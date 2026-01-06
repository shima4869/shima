# AIじゃんけんバトル ✨
# インストール: pip install tkinter mediapipe opencv-python numpy pillow
# 実行方法: python 20_ai_janken_machine.py
# Select Interpreter: Python 3.11.9

import cv2
import mediapipe as mp
import random
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import os
import sys

# --- 既存の判定ロジックをそのまま継承 ---

def detect_hand_gesture(landmarks):
    """手の形を判定するロジック (既存システム)"""
    finger_tips = [8, 12, 16, 20]
    fingers_open = []

    for tip_id in finger_tips:
        if landmarks.landmark[tip_id].y < landmarks.landmark[tip_id - 2].y:
            fingers_open.append(1)
        else:
            fingers_open.append(0)

    total_open = sum(fingers_open)

    if total_open == 0:
        return "Rock"
    elif total_open == 4:
        return "Paper"
    elif total_open == 1 or total_open == 2:
        return "Scissors"
    else:
        return "Paper"

def judge_winner(player, cpu):
    """勝敗判定ロジック (既存システム)"""
    if player == cpu:
        return "DRAW"
    
    if (player == "Rock" and cpu == "Scissors") or \
       (player == "Scissors" and cpu == "Paper") or \
       (player == "Paper" and cpu == "Rock"):
        return "WIN!"
    
    return "LOSE..."

class JankenApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIじゃんけんバトル ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数 (シリーズ統一)
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.WIN_COLOR = "#2ECC71"
        self.LOSE_COLOR = "#E74C3C"

        # MediaPipe初期化
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            min_detection_confidence=0.7, 
            min_tracking_confidence=0.5, 
            max_num_hands=1
        )
        
        # カメラ初期化
        self.cap = cv2.VideoCapture(0)
        
        # ゲーム状態管理 (既存のステートマシンをクラス変数へ)
        self.is_running = True
        self.game_state = "IDLE" 
        self.countdown_start_time = 0
        self.result_display_time = 0
        self.computer_move = ""
        self.player_move = ""
        self.result_text = ""
        
        # 統計データ
        self.wins = 0
        self.losses = 0
        self.draws = 0

        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        header = tk.Frame(self.root, bg="#FFFBEB")
        header.pack(pady=20)
        tk.Label(header, text="✊✌️🖐️ AIじゃんけんバトル", 
                 font=("Meiryo", 28, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR).pack()
        tk.Label(header, text="〜 AIの手の形認識 vs 人間の反射神経 〜", 
                 font=("Meiryo", 10), bg="#FFFBEB", fg="#95A5A6").pack()

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=40, pady=10)
        
        # 比率調整：左(操作・戦績)1, 右(カメラモニター)2
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=2)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作・情報パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=400)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 1. 試合開始ボタン
        self.start_btn = tk.Button(self.left_panel, text="勝負を開始 (SPACE)", 
                                  command=self.trigger_countdown,
                                  bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 14, "bold"),
                                  relief=tk.FLAT, cursor="hand2", pady=20)
        self.start_btn.pack(fill=tk.X, pady=(0, 15))

        # 2. 現在の状態・結果
        status_frame = tk.LabelFrame(self.left_panel, text=" 👁️ 今の状態 ", 
                                    font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, pady=10)
        
        self.lbl_status = tk.Label(status_frame, text="待機中", bg=self.BG_WHITE, 
                                  font=("Meiryo", 18, "bold"), fg=self.TEXT_COLOR, pady=15)
        self.lbl_status.pack()

        self.lbl_result_big = tk.Label(status_frame, text="-", bg=self.BG_WHITE, 
                                      font=("Impact", 42), fg=self.PRIMARY_COLOR)
        self.lbl_result_big.pack(pady=(0, 10))

        # 3. 通算成績
        stats_frame = tk.LabelFrame(self.left_panel, text=" 📊 通算成績 ", 
                                   font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        stats_frame.pack(fill=tk.X, pady=10)
        
        self.lbl_stats = tk.Label(stats_frame, text="0勝 - 0敗 - 0分", bg=self.BG_WHITE, 
                                 font=("Meiryo", 12, "bold"), fg=self.TEXT_COLOR, pady=10)
        self.lbl_stats.pack()

        # ヒント
        guide = "【操作】\n・スペースキーでカウント開始\n・3, 2, 1 で手をカメラに向けて！\n・Qキーで終了"
        tk.Label(self.left_panel, text=guide, bg="#FFFBEB", justify=tk.LEFT, 
                 font=("Meiryo", 9), fg="#95A5A6").pack(side=tk.BOTTOM, pady=20)

        # --- 右側：カメラ表示エリア ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ AI認識モニター ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

        # スペースキーのバインド
        self.root.bind('<space>', lambda e: self.trigger_countdown())
        self.root.bind('<q>', lambda e: self.on_closing())

    def trigger_countdown(self):
        if self.game_state == "IDLE":
            self.game_state = "COUNTDOWN"
            self.countdown_start_time = time.time()
            self.start_btn.config(state=tk.DISABLED, bg="#BDC3C7")

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)

            current_hand_shape = "Unknown"
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp.solutions.drawing_utils.draw_landmarks(
                        frame, hand_landmarks, mp.solutions.hands.HAND_CONNECTIONS)
                    current_hand_shape = detect_hand_gesture(hand_landmarks)

            # ステートマシンの処理
            if self.game_state == "IDLE":
                self.lbl_status.config(text="対戦待ち", fg=self.TEXT_COLOR)
                cv2.putText(frame, "READY?", (w//2-100, h//2), cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 3)

            elif self.game_state == "COUNTDOWN":
                elapsed = time.time() - self.countdown_start_time
                if elapsed < 1: val = "3"
                elif elapsed < 2: val = "2"
                elif elapsed < 3: val = "1"
                else:
                    # 判定フェーズ
                    self.game_state = "RESULT"
                    self.result_display_time = time.time()
                    self.player_move = current_hand_shape
                    self.computer_move = random.choice(["Rock", "Paper", "Scissors"])
                    self.result_text = judge_winner(self.player_move, self.computer_move)
                    
                    # 成績更新
                    if self.result_text == "WIN!": self.wins += 1
                    elif self.result_text == "LOSE...": self.losses += 1
                    else: self.draws += 1
                    self.lbl_stats.config(text=f"{self.wins}勝 - {self.losses}敗 - {self.draws}分")
                    val = "GO!"

                self.lbl_status.config(text="カウントダウン中！", fg=self.SECONDARY_COLOR)
                cv2.putText(frame, val, (w//2-50, h//2), cv2.FONT_HERSHEY_SIMPLEX, 4, (0, 255, 255), 6)

            elif self.game_state == "RESULT":
                if self.player_move == "Unknown":
                    msg = "Hand not detected!"
                    color = (0, 0, 255)
                    self.lbl_result_big.config(text="ERROR", fg=self.LOSE_COLOR)
                else:
                    msg = f"CPU:{self.computer_move} vs YOU:{self.player_move}"
                    color = (255, 255, 255)
                    self.lbl_result_big.config(text=self.result_text, 
                                             fg=self.WIN_COLOR if "WIN" in self.result_text else self.LOSE_COLOR)
                
                self.lbl_status.config(text="結果発表")
                cv2.putText(frame, msg, (50, h-50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                
                # 3秒後にリセット
                if time.time() - self.result_display_time > 3:
                    self.game_state = "IDLE"
                    self.lbl_result_big.config(text="-", fg=self.PRIMARY_COLOR)
                    self.start_btn.config(state=tk.NORMAL, bg=self.PRIMARY_COLOR)

            # GUI表示
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
    # 高DPI対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = JankenApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()