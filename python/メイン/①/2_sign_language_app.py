# 手話（ジェスチャー）翻訳 AI
# インストール: pip install opencv-python mediapipe pillow numpy
# 実行方法: python 2_sign_language_app.py
# Select Interpreter: Python 3.11.9

import cv2
import mediapipe as mp
import numpy as np
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk
import threading
import time
import os
import platform

class SignLanguageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("手話（ジェスチャー）翻訳 AI ✨")
        self.root.geometry("1500x950")
        self.root.configure(bg="#FFFBEB")

        # カラー設定
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"

        # MediaPipe Hands 初期化
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7 
        )

        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.current_gesture = "待機中"
        
        # フォント設定
        self.font_path = self._get_system_font()

        self.setup_ui()
        
        # UI更新ループ開始
        self.update_loop()

    def _get_system_font(self):
        """OSに合わせて日本語フォントのパスを取得"""
        system = platform.system()
        if system == "Windows":
            candidates = ["C:/Windows/Fonts/meiryo.ttc", "C:/Windows/Fonts/msgothic.ttc"]
        elif system == "Darwin": # macOS
            candidates = ["/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"]
        else: # Linux
            candidates = ["/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"]
        
        for path in candidates:
            if os.path.exists(path): return path
        return None

    def setup_ui(self):
        # タイトル
        title_label = tk.Label(self.root, text="🖐️ 手話・ジェスチャー翻訳機", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：カメラ(右)をより大きく (左1:右6)
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=6) 
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：ステータスパネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=400) # 幅を少し広げました
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 判定結果
        res_frame = tk.LabelFrame(self.left_panel, text=" 🗨️ 翻訳結果 ", 
                                 font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        res_frame.pack(fill=tk.X, pady=(0, 10))

        self.gesture_label = tk.Label(res_frame, text="待機中", bg=self.BG_WHITE, 
                                     font=("Meiryo", 22, "bold"), fg=self.TEXT_COLOR, pady=25)
        self.gesture_label.pack()

        # 認識リスト (文字サイズを大きくし、意味を正確に記載)
        list_frame = tk.LabelFrame(self.left_panel, text=" 💡 認識できる手の形と意味 ", 
                                  font=("Meiryo", 12, "bold"), bg=self.BG_WHITE, 
                                  fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        guide_text = (
            "🖐️ 全指を広げる\n"
            "　 ➡ こんにちは\n\n"
            "👍 親指だけ立てる\n"
            "　 ➡ ありがとう\n\n"
            "✌️ 人差指・中指を立てる\n"
            "　 ➡ 平和 (ピース)\n\n"
            "👌 親指・人差指で輪を作る\n"
            "　 ➡ 了解 (OK)\n\n"
            "🤙 親指・人差指・小指を出す\n"
            "　 ➡ 愛してる\n\n"
            "🤘 人差指・小指を出す\n"
            "　 ➡ キツネ (Fox)\n\n"
            "🤙 小指だけを立てる\n"
            "　 ➡ 約束"
        )
        # フォントサイズを 10 から 13 に変更
        tk.Label(list_frame, text=guide_text, bg=self.BG_WHITE, justify=tk.LEFT, 
                 font=("Meiryo", 13), padx=20, pady=20).pack(anchor="nw")

        # --- 右側：カメラプレビュー ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ カメラ映像 ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def _is_finger_up(self, landmarks, finger_name):
        """指の付け根(MCP)を基準にした判定"""
        tips = {'thumb': 4, 'index': 8, 'middle': 12, 'ring': 16, 'pinky': 20}
        mcps = {'thumb': 2, 'index': 5, 'middle': 9, 'ring': 13, 'pinky': 17}
        
        tip = landmarks.landmark[tips[finger_name]]
        mcp = landmarks.landmark[mcps[finger_name]]
        
        if finger_name == 'thumb':
            return (abs(tip.x - mcp.x) > 0.06) or (tip.y < mcp.y - 0.03)
        else:
            return tip.y < mcp.y - 0.02

    def classify_gesture(self, landmarks):
        """ジェスチャー分類ロジック"""
        t = self._is_finger_up(landmarks, 'thumb')
        i = self._is_finger_up(landmarks, 'index')
        m = self._is_finger_up(landmarks, 'middle')
        r = self._is_finger_up(landmarks, 'ring')
        p = self._is_finger_up(landmarks, 'pinky')
        
        count = sum([t, i, m, r, p])

        # OKサイン (特別判定)
        d_ok = ((landmarks.landmark[4].x - landmarks.landmark[8].x)**2 + 
                (landmarks.landmark[4].y - landmarks.landmark[8].y)**2)**0.5
        if d_ok < 0.05 and m and r and p:
            return "了解 (OK)", (46, 204, 113)

        # ピース
        if i and m and not any([t, r, p]):
            return "平和 (Peace)", (241, 196, 15)

        # 約束
        if p and not any([t, i, m, r]):
            return "約束 (Promise)", (255, 105, 180)

        # こんにちは
        if count == 5:
            return "こんにちは", (52, 152, 219)

        # ありがとう
        if t and not any([i, m, r, p]):
            return "ありがとう", (230, 126, 34)

        # キツネ
        if i and p and not any([t, m, r]):
            return "キツネ (Fox)", (231, 76, 60)

        # 愛してる
        if t and i and p and not any([m, r]):
            return "愛してる", (255, 20, 147)

        if count == 0:
            return "待機中...", (149, 165, 166)
            
        return "認識中...", self.TEXT_COLOR

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)

            detected_text = "手を映してください"
            text_rgb = self.TEXT_COLOR

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                    detected_text, text_rgb = self.classify_gesture(hand_landmarks)

            self.gesture_label.config(text=detected_text, fg=self._rgb_to_hex(text_rgb))

            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 50 and ch > 50:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
                
                fw, fh = pil_img.size
                ratio = min(cw/fw, ch/fh)
                new_size = (int(fw*ratio), int(fh*ratio))
                pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
                
                self.tk_img = ImageTk.PhotoImage(pil_img)
                self.canvas.itemconfig(self.image_item, image=self.tk_img)
                self.canvas.coords(self.image_item, (cw-new_size[0])//2, (ch-new_size[1])//2)

        if self.is_running:
            self.root.after(30, self.update_loop)

    def _rgb_to_hex(self, rgb):
        if isinstance(rgb, str): return rgb
        return '#%02x%02x%02x' % rgb

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
    
    app = SignLanguageApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()