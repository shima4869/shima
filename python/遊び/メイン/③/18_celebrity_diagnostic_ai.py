# AI芸能人診断AI ✨
# インストール: pip install tkinter mediapipe opencv-python numpy pillow
# 実行方法: python 18_celebrity_diagnostic_ai.py    
# Select Interpreter: Python 3.11.9

import cv2
import mediapipe as mp
import numpy as np
import tkinter as tk
from tkinter import messagebox, filedialog, scrolledtext, ttk
from PIL import Image, ImageTk
import threading
import time
import os
import sys

class LookalikeEngine:
    """顔の幾何学的特徴を抽出し、データベースと比較するAIエンジン"""
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # 簡易的な芸能人顔タイプデータベース (比率データ)
        # 本来は大量の顔画像から学習させますが、ここでは特徴的な比率を定義
        # [目の間隔比, 鼻の長さ比, 口の幅比, 顔の横縦比]
        self.celebrity_db = [
            {"name": "目黒 蓮風", "type": "クール・端正", "sig": [0.38, 0.42, 0.45, 0.75]},
            {"name": "橋本 環奈風", "type": "キュート・華やか", "sig": [0.42, 0.38, 0.48, 0.82]},
            {"name": "大谷 翔平風", "type": "爽やか・スポーティ", "sig": [0.35, 0.45, 0.42, 0.78]},
            {"name": "新垣 結衣風", "type": "清純・ナチュラル", "sig": [0.40, 0.40, 0.50, 0.80]},
            {"name": "菅田 将暉風", "type": "個性的・アーティスティック", "sig": [0.36, 0.48, 0.40, 0.72]},
            {"name": "石原 さとみ風", "type": "フェミニン・魅力的", "sig": [0.41, 0.39, 0.52, 0.79]}
        ]

    def get_face_signature(self, landmarks):
        """顔のパーツ間距離の比率を計算（サイズ・角度に依存しない特徴量）"""
        # 基準点
        top = landmarks[10]    # 額上部
        bottom = landmarks[152] # 顎
        left = landmarks[234]   # 顔左端
        right = landmarks[454]  # 顔右端
        
        f_h = np.sqrt((top.x - bottom.x)**2 + (top.y - bottom.y)**2)
        f_w = np.sqrt((left.x - right.x)**2 + (left.y - right.y)**2)
        
        # 特徴抽出
        dist_eyes = np.sqrt((landmarks[33].x - landmarks[263].x)**2 + (landmarks[33].y - landmarks[263].y)**2)
        dist_nose = np.sqrt((landmarks[168].x - landmarks[1].y)**2 + (landmarks[168].y - landmarks[1].y)**2)
        dist_mouth = np.sqrt((landmarks[61].x - landmarks[291].x)**2 + (landmarks[61].y - landmarks[291].y)**2)
        
        # 比率（シグネチャ）の作成
        return [
            dist_eyes / f_h, 
            dist_nose / f_h,
            dist_mouth / f_w,
            f_w / f_h
        ]

    def diagnose(self, signature):
        """データベースと照合して最も近い人物を算出"""
        results = []
        for celeb in self.celebrity_db:
            # ユークリッド距離で「近さ」を計算
            dist = np.linalg.norm(np.array(signature) - np.array(celeb["sig"]))
            # 距離を％に変換（0.2を最大乖離として計算）
            similarity = max(0, min(99, 100 - (dist * 400)))
            results.append({**celeb, "score": similarity})
        
        # スコア順にソート
        return sorted(results, key=lambda x: x["score"], reverse=True)[0]

class CelebrityDiagnosticApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI芸能人診断 ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"

        self.engine = LookalikeEngine()
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.is_analyzing = False
        
        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # タイトル
        header = tk.Frame(self.root, bg="#FFFBEB")
        header.pack(pady=20)
        tk.Label(header, text="👤 AI芸能人・似顔絵診断", 
                 font=("Meiryo", 28, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR).pack()
        tk.Label(header, text="〜 あなたの顔立ちを黄金比データと照合します 〜", 
                 font=("Meiryo", 10), bg="#FFFBEB", fg="#95A5A6").pack()

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=40, pady=10)
        
        # 比率調整：左1, 右3
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：診断パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=400)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 診断ボタン
        self.diag_btn = tk.Button(self.left_panel, text="診断を実行する 🚀", 
                                 command=self.start_diagnosis,
                                 bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 14, "bold"),
                                 relief=tk.FLAT, cursor="hand2", pady=20)
        self.diag_btn.pack(fill=tk.X, pady=(0, 20))

        # 結果表示エリア
        self.res_frame = tk.LabelFrame(self.left_panel, text=" 📊 診断結果レポート ", 
                                      font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                      fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        self.res_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.lbl_celeb_name = tk.Label(self.res_frame, text="準備完了", bg=self.BG_WHITE, 
                                      font=("Meiryo", 18, "bold"), fg=self.TEXT_COLOR, pady=15)
        self.lbl_celeb_name.pack()

        self.lbl_score = tk.Label(self.res_frame, text="-- %", bg=self.BG_WHITE, 
                                 font=("Impact", 56), fg=self.PRIMARY_COLOR)
        self.lbl_score.pack()

        self.lbl_type = tk.Label(self.res_frame, text="カメラに顔を映してください", bg=self.BG_WHITE, 
                                font=("Meiryo", 10), fg="#95A5A6", pady=10)
        self.lbl_type.pack()

        # 履歴ログ
        self.log_area = scrolledtext.ScrolledText(self.left_panel, font=("Meiryo", 9), height=10,
                                                 bg="#F9F9F9", relief=tk.FLAT)
        self.log_area.pack(fill=tk.X, pady=10)
        self.write_log("システムスタンバイ。")

        # --- 右側：カメラプレビュー ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ AIフェイシャル・スキャンモニター ", 
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

    def start_diagnosis(self):
        """診断のトリガー"""
        if self.is_analyzing: return
        self.is_analyzing = True
        self.diag_btn.config(state=tk.DISABLED, text="スキャン中...")
        self.write_log("顔の構造を精密スキャンしています...")
        # 2秒後に結果を表示する演出
        self.root.after(2000, self.finish_diagnosis)

    def finish_diagnosis(self):
        self.is_analyzing = False
        self.diag_btn.config(state=tk.NORMAL, text="診断を実行する 🚀")
        if hasattr(self, 'last_result'):
            res = self.last_result
            self.lbl_celeb_name.config(text=f"あなたは {res['name']} さん")
            self.lbl_score.config(text=f"{int(res['score'])} %")
            self.lbl_type.config(text=f"タイプ: {res['type']}", fg=self.SAFE_COLOR)
            self.write_log(f"診断完了: {res['name']} ({int(res['score'])}%)")
        else:
            messagebox.showwarning("エラー", "顔が検出されていません。")

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1) # 鏡表示
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.engine.face_mesh.process(rgb_frame)
            
            hud_color = (0, 159, 255) # オレンジ
            
            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0]
                # 比率データの計算
                sig = self.engine.get_face_signature(landmarks.landmark)
                # 診断結果のシミュレーション
                self.last_result = self.engine.diagnose(sig)
                
                # スキャン中のみエフェクトを派手にする
                if self.is_analyzing:
                    hud_color = (46, 204, 113) # 緑に変化
                    # スキャンライン演出
                    scan_y = int((time.time() * 500) % h)
                    cv2.line(frame, (0, scan_y), (w, scan_y), hud_color, 2)

                # メッシュの一部を描画（HUD演出）
                for idx in [1, 33, 263, 61, 291, 199]: # 主要ポイント
                    pt = landmarks.landmark[idx]
                    cv2.circle(frame, (int(pt.x * w), int(pt.y * h)), 4, hud_color, -1)
                
                # 輪郭線の描画
                mp.solutions.drawing_utils.draw_landmarks(
                    frame, landmarks, mp.solutions.face_mesh.FACEMESH_CONTOURS,
                    connection_drawing_spec=mp.solutions.drawing_styles.get_default_face_mesh_contours_style()
                )

            # Tkinter更新
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 50 and ch > 50:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
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
        sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    # Windows高DPI対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = CelebrityDiagnosticApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()