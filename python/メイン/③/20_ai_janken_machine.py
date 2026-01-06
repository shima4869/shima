# AIじゃんけん・絶対後出しマシーン ✨
# インストール: pip install tkinter mediapipe opencv-python numpy pillow
# 実行方法: python 20_ai_janken_machine.py
# Select Interpreter: Python 3.11.9

import cv2
import mediapipe as mp
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import threading
import time
import sys

class JankenEngine:
    """手の形状をミリ秒単位で解析し、勝てる手を導き出すAIエンジン"""
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        # 手の形に対応する「勝てる手」
        # キー: 人間の手 -> 値: AIが出すべき手
        self.WINNING_HAND = {
            "ROCK": "PAPER",
            "PAPER": "SCISSORS",
            "SCISSORS": "ROCK",
            "WAITING": "READY"
        }

    def _is_finger_up(self, landmarks, finger_idx):
        """指が立っているかを判定 (4:親指, 8:人差, 12:中, 16:薬, 20:小)"""
        tips = [4, 8, 12, 16, 20]
        mcps = [2, 5, 9, 13, 17]
        
        tip = landmarks[tips[finger_idx]]
        mcp = landmarks[mcps[finger_idx]]
        
        if finger_idx == 0: # 親指はx座標で判定
            return abs(tip.x - mcp.x) > 0.05
        return tip.y < mcp.y

    def classify_hand(self, hand_landmarks):
        """手の形状からグー・チョキ・パーを判定"""
        landmarks = hand_landmarks.landmark
        # 各指の起立状態 [親, 人, 中, 薬, 小]
        fingers = [self._is_finger_up(landmarks, i) for i in range(5)]
        
        # 判定ロジック
        up_count = sum(fingers)
        
        if up_count <= 1: 
            return "ROCK"
        if up_count >= 4:
            return "PAPER"
        if fingers[1] and fingers[2]:
            return "SCISSORS"
        
        return "WAITING"

class JankenApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIじゃんけん・絶対後出しマシーン ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数 (シリーズ統一)
        self.PRIMARY_COLOR = "#FF9F43"
        self.SECONDARY_COLOR = "#FFCC33"
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.ALERT_COLOR = "#E74C3C"

        self.engine = JankenEngine()
        self.cap = cv2.VideoCapture(0)
        
        # 状態管理
        self.is_running = True
        self.current_user_hand = "WAITING"
        self.ai_hand = "READY"
        self.match_count = 0
        self.ai_win_count = 0
        
        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        header = tk.Frame(self.root, bg="#FFFBEB")
        header.pack(pady=20)
        tk.Label(header, text="🎰 AI絶対後出しマシーン", 
                 font=("Meiryo", 28, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR).pack()
        tk.Label(header, text="〜 AIがあなたの動きを先読みし、100%勝利します 〜", 
                 font=("Meiryo", 10), bg="#FFFBEB", fg="#95A5A6").pack()

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=40, pady=10)
        
        # 比率調整：左(AI)3, 右(あなた)1
        self.main_container.columnconfigure(0, weight=3)
        self.main_container.columnconfigure(1, weight=1)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：AIの手 表示エリア ---
        self.ai_panel = tk.Frame(self.main_container, bg=self.BG_WHITE, relief=tk.RIDGE, bd=4)
        self.ai_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        
        tk.Label(self.ai_panel, text="🤖 AI'S HAND", font=("Impact", 24), bg=self.BG_WHITE, fg=self.PRIMARY_COLOR).pack(pady=10)
        
        # AIの手を描画するCanvas
        self.ai_canvas = tk.Canvas(self.ai_panel, bg=self.BG_WHITE, highlightthickness=0)
        self.ai_canvas.pack(fill=tk.BOTH, expand=True)
        self.ai_image_item = self.ai_canvas.create_image(0, 0, anchor=tk.CENTER)

        # --- 右側：あなたの手 プレビューエリア ---
        self.user_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.user_panel.grid(row=0, column=1, sticky="nsew")

        # カメラプレビュー
        cam_frame = tk.LabelFrame(self.user_panel, text=" 👤 あなたの手 ", font=("Meiryo", 10, "bold"),
                                 bg=self.BG_WHITE, fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        cam_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.cam_canvas = tk.Canvas(cam_frame, height=250, bg="black", highlightthickness=0)
        self.cam_canvas.pack(fill=tk.X, padx=5, pady=5)
        self.cam_image_item = self.cam_canvas.create_image(0, 0, anchor=tk.NW)

        # 判定結果
        status_frame = tk.LabelFrame(self.user_panel, text=" 📊 対戦成績 ", font=("Meiryo", 10, "bold"),
                                    bg=self.BG_WHITE, fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, pady=10)
        
        self.lbl_result = tk.Label(status_frame, text="AIの全勝中", font=("Meiryo", 14, "bold"), 
                                  bg=self.BG_WHITE, fg=self.ALERT_COLOR, pady=10)
        self.lbl_result.pack()

        self.lbl_stats = tk.Label(status_frame, text="AI 0勝 - あなた 0勝", bg=self.BG_WHITE, font=("Meiryo", 10))
        self.lbl_stats.pack(pady=(0, 10))

        # ヒント
        guide = "【攻略法】\nAIは手の形が完成する数ミリ秒前に\n反応します。あなたが手を出し切る\n瞬間には、AIはすでにあなたを\n負かす準備ができています。"
        tk.Label(self.user_panel, text=guide, bg="#FFFBEB", justify=tk.LEFT, 
                 font=("Meiryo", 9), fg="#95A5A6").pack(side=tk.BOTTOM, pady=20)

    def draw_ai_hand(self, hand_type):
        """AIの手を絵文字や図形で描画"""
        self.ai_canvas.delete("all")
        cw, ch = self.ai_canvas.winfo_width(), self.ai_canvas.winfo_height()
        if cw < 50: return

        emoji_map = {"ROCK": "✊", "SCISSORS": "✌️", "PAPER": "🖐️", "READY": "❓"}
        text = emoji_map.get(hand_type, "❓")
        
        # 背景の円
        self.ai_canvas.create_oval(cw//2-200, ch//2-200, cw//2+200, ch//2+200, 
                                   fill="#FDF2E9", outline=self.PRIMARY_COLOR, width=5)
        
        # 巨大な手
        self.ai_canvas.create_text(cw//2, ch//2, text=text, font=("Segoe UI Emoji", 180))
        
        # テキストラベル
        self.ai_canvas.create_text(cw//2, ch//2 + 250, text=hand_type, 
                                   font=("Impact", 48), fill=self.PRIMARY_COLOR)

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1) # 鏡表示
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.engine.hands.process(rgb_frame)
            
            user_hand = "WAITING"
            if results.multi_hand_landmarks:
                # 最も確実な1つ目の手を解析
                hand_landmarks = results.multi_hand_landmarks[0]
                user_hand = self.engine.classify_hand(hand_landmarks)
                
                # スケルトン描画
                mp.solutions.drawing_utils.draw_landmarks(
                    frame, hand_landmarks, mp.solutions.hands.HAND_CONNECTIONS)
            
            # --- ここが「後出し」の核心部 ---
            # 人間の手が確定した瞬間、あるいはその直前に、AIが勝つ手を選択する
            if user_hand != "WAITING":
                new_ai_hand = self.engine.WINNING_HAND[user_hand]
                if self.ai_hand != new_ai_hand:
                    self.ai_hand = new_ai_hand
                    self.ai_win_count += 1
                    self.match_count += 1
                    self.lbl_stats.config(text=f"AI {self.ai_win_count}勝 - あなた 0勝")
            else:
                self.ai_hand = "READY"

            # AIの手を描画
            self.draw_ai_hand(self.ai_hand)

            # カメラプレビューをTkinter Canvasへ表示
            self.root.update_idletasks()
            ccw, cch = self.cam_canvas.winfo_width(), self.cam_canvas.winfo_height()
            if ccw > 10 and cch > 10:
                pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                ratio = min(ccw/w, cch/h)
                new_size = (int(w*ratio), int(h*ratio))
                pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
                self.tk_cam_img = ImageTk.PhotoImage(pil_img)
                self.cam_canvas.itemconfig(self.cam_image_item, image=self.tk_cam_img)
                self.cam_canvas.coords(self.cam_image_item, (ccw-new_size[0])//2, (cch-new_size[1])//2)

        if self.is_running:
            # 高速レスポンスのためインターバルを短く設定
            self.root.after(20, self.update_loop)

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
    
    app = JankenApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()