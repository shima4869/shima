# AI顔識別・補助メガネ (Light Edition) ✨
# インストール: pip install opencv-python mediapipe pillow numpy
# 実行方法: python 13_smart_glasses.py
# Select Interpreter: Python 3.11.9

import cv2
import mediapipe as mp
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk
import json
import os
import time
import datetime
import threading

class FaceMemoryAI:
    """MediaPipeを使用して顔の形状特徴(ジオメトリ)で識別を行うエンジン"""
    def __init__(self, data_file="face_memory_v2.json"):
        self.data_file = data_file
        self.known_signatures = [] # 顔の比率データのリスト
        self.known_metadata = []   # {name, memo, last_seen}
        
        # MediaPipe Face Mesh の初期化
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=5,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.load_data()

    def load_data(self):
        """保存されたデータを読み込む"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        self.known_signatures.append(np.array(item["signature"]))
                        self.known_metadata.append(item["metadata"])
            except Exception as e:
                print(f"Read Error: {e}")

    def save_data(self):
        """データをJSONに保存"""
        save_list = []
        for sig, meta in zip(self.known_signatures, self.known_metadata):
            save_list.append({
                "signature": sig.tolist(),
                "metadata": meta
            })
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(save_list, f, ensure_ascii=False, indent=4)

    def get_face_signature(self, landmarks):
        """
        顔のランドマークから、サイズに依存しない相対的な比率（署名）を計算
        [目と目の距離 / 顔の高さ, 鼻の幅 / 顔の幅, ...] などの特徴量を作成
        """
        # 正規化のための基準（顔の全体サイズ）
        top = landmarks[10] # 額
        bottom = landmarks[152] # 顎
        left = landmarks[234] # 左端
        right = landmarks[454] # 右端
        
        f_height = np.sqrt((top.x - bottom.x)**2 + (top.y - bottom.y)**2)
        f_width = np.sqrt((left.x - right.x)**2 + (left.y - right.y)**2)
        
        # 特徴的な距離を計算（一部抜粋）
        # 1. 目の間の距離
        eye_l = landmarks[33]
        eye_r = landmarks[263]
        dist_eyes = np.sqrt((eye_l.x - eye_r.x)**2 + (eye_l.y - eye_r.y)**2)
        
        # 2. 口の幅
        mouth_l = landmarks[61]
        mouth_r = landmarks[291]
        dist_mouth = np.sqrt((mouth_l.x - mouth_r.x)**2 + (mouth_l.y - mouth_r.y)**2)
        
        # 3. 鼻の高さ
        nose_top = landmarks[168]
        nose_tip = landmarks[1]
        dist_nose = np.sqrt((nose_top.x - nose_tip.x)**2 + (nose_top.y - nose_tip.y)**2)

        # 4. 顎の形状（数カ所サンプリング）
        # 比率として保持することで遠近に対応
        signature = [
            dist_eyes / f_height,
            dist_mouth / f_width,
            dist_nose / f_height,
            f_width / f_height
        ]
        
        # さらに詳細なポイント（10箇所程度）を追加して精度向上
        key_indices = [1, 33, 263, 61, 291, 199, 10, 152, 234, 454]
        for i in range(len(key_indices)):
            for j in range(i + 1, len(key_indices)):
                p1 = landmarks[key_indices[i]]
                p2 = landmarks[key_indices[j]]
                d = np.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)
                signature.append(d / f_height)

        return np.array(signature)

    def register(self, signature, name, memo):
        """新しい顔を登録"""
        self.known_signatures.append(signature)
        self.known_metadata.append({
            "name": name,
            "memo": memo,
            "last_seen": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        self.save_data()
        return True

    def identify(self, signature):
        """署名を既存データと比較して同一人物か判定"""
        if not self.known_signatures:
            return None
        
        # ユークリッド距離で一番近いデータを探す
        distances = [np.linalg.norm(signature - known) for known in self.known_signatures]
        best_match_idx = np.argmin(distances)
        
        # しきい値設定（小さいほど厳格）
        if distances[best_match_idx] < 0.15:
            return self.known_metadata[best_match_idx]
        return None

class SmartGlassesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI顔識別・補助メガネ (Light Edition) ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        self.PRIMARY_COLOR = "#FF9F43"
        self.SECONDARY_COLOR = "#FFCC33"
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.HUD_COLOR = (255, 159, 67)

        self.ai = FaceMemoryAI()
        
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.current_face_info = [] # [(rect, metadata, signature)]
        self.last_detected_signature = None
        
        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        title_label = tk.Label(self.root, text="👓 AI顔識別・補助メガネ", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=4)
        self.main_container.rowconfigure(0, weight=1)

        # 左側：登録パネル
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        reg_frame = tk.LabelFrame(self.left_panel, text=" 👤 知人を記憶する ", 
                                 font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        reg_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(reg_frame, text="お名前:", bg=self.BG_WHITE, font=("Meiryo", 9)).pack(anchor="w", padx=15, pady=(10, 0))
        self.name_entry = tk.Entry(reg_frame, font=("Meiryo", 11), relief=tk.SOLID, bd=1)
        self.name_entry.pack(fill=tk.X, padx=15, pady=5)

        tk.Label(reg_frame, text="メモ（前回の話題など）:", bg=self.BG_WHITE, font=("Meiryo", 9)).pack(anchor="w", padx=15, pady=(5, 0))
        self.memo_entry = tk.Entry(reg_frame, font=("Meiryo", 11), relief=tk.SOLID, bd=1)
        self.memo_entry.pack(fill=tk.X, padx=15, pady=5)

        self.reg_btn = tk.Button(reg_frame, text="この人を登録 💾", command=self.register_person,
                                bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 11, "bold"),
                                relief=tk.FLAT, cursor="hand2", pady=10)
        self.reg_btn.pack(fill=tk.X, padx=15, pady=15)

        self.log_area = scrolledtext.ScrolledText(self.left_panel, font=("Meiryo", 9), height=15,
                                                 bg=self.BG_WHITE, relief=tk.FLAT, fg=self.TEXT_COLOR)
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=10)
        self.write_log("システム起動。MediaPipeエンジンの準備完了。")

        # 右側：プレビュー
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ HUD プレビュー ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def write_log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def register_person(self):
        name = self.name_entry.get().strip()
        memo = self.memo_entry.get().strip()
        
        if not name or self.last_detected_signature is None:
            messagebox.showwarning("エラー", "名前を入力するか、顔をカメラに向けてください。")
            return

        if self.ai.register(self.last_detected_signature, name, memo):
            self.write_log(f"「{name}」さんを登録しました。")
            self.name_entry.delete(0, tk.END)
            self.memo_entry.delete(0, tk.END)

    def draw_hud(self, frame, faces_info):
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil, "RGBA")
        try:
            font_path = "C:/Windows/Fonts/meiryo.ttc"
            f_main = ImageFont.truetype(font_path, 24)
            f_sub = ImageFont.truetype(font_path, 16)
        except:
            f_main = ImageFont.load_default()
            f_sub = ImageFont.load_default()

        for (x, y, w, h), metadata, _ in faces_info:
            color = self.HUD_COLOR + (255,)
            d = 25
            # ターゲットマーカー
            draw.line([(x, y), (x+d, y)], fill=color, width=4)
            draw.line([(x, y), (x, y+d)], fill=color, width=4)
            draw.line([(x+w, y), (x+w-d, y)], fill=color, width=4)
            draw.line([(x+w, y), (x+w, y+d)], fill=color, width=4)
            draw.line([(x, y+h), (x+d, y+h)], fill=color, width=4)
            draw.line([(x, y+h), (x, y+h-d)], fill=color, width=4)
            draw.line([(x+w, y+h), (x+w-d, y+h)], fill=color, width=4)
            draw.line([(x+w, y+h), (x+w, y+h-d)], fill=color, width=4)

            # 情報パネル
            px, py = x + w + 15, y
            if metadata:
                draw.rectangle([px, py, px+250, py+100], fill=(0,0,0,160), outline=color, width=2)
                draw.text((px+10, py+10), f"ID: {metadata['name']}", font=f_main, fill=(255,255,255))
                draw.text((px+10, py+45), f"MEMO: {metadata['memo']}", font=f_sub, fill=(200,200,200))
                draw.text((px+10, py+70), f"LAST: {metadata['last_seen']}", font=f_sub, fill=(150,150,150))
            else:
                draw.text((px, py), "UNKNOWN TARGET", font=f_sub, fill=(255,255,255,180))

        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.ai.face_mesh.process(rgb_frame)
            
            self.current_face_info = []
            self.last_detected_signature = None

            if results.multi_face_landmarks:
                for landmarks in results.multi_face_landmarks:
                    # バウンディングボックス計算
                    pts = np.array([[l.x * w, l.y * h] for l in landmarks.landmark])
                    xmin, ymin = np.min(pts, axis=0)
                    xmax, ymax = np.max(pts, axis=0)
                    rect = (int(xmin), int(ymin), int(xmax-xmin), int(ymax-ymin))
                    
                    # 特徴量抽出と識別
                    sig = self.ai.get_face_signature(landmarks.landmark)
                    meta = self.ai.identify(sig)
                    
                    self.current_face_info.append((rect, meta, sig))
                    # 登録ボタン用に一つ保持
                    self.last_detected_signature = sig

            # 描画
            display_frame = self.draw_hud(frame, self.current_face_info)

            # Tkinter更新
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 50 and ch > 50:
                rgb_img = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_img)
                ratio = min(cw/w, ch/h)
                new_size = (int(w*ratio), int(h*ratio))
                pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
                self.tk_img = ImageTk.PhotoImage(pil_img)
                self.canvas.itemconfig(self.image_item, image=self.tk_img)
                self.canvas.coords(self.image_item, (cw-new_size[0])//2, (ch-new_size[1])//2)

        if self.is_running:
            self.root.after(30, self.update_loop)

    def on_closing(self):
        self.is_running = False
        self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    app = SmartGlassesApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()