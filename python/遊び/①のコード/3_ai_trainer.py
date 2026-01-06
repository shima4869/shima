# AIパーソナルトレーナー ✨
# インストール: pip install tkinter mediapipe numpy pillow
# 実行方法: python ai_trainer.py
# Select Interpreter: Python 3.11.9

import cv2
import mediapipe as mp
import numpy as np
import math
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import time
import os
import sys

# --- 既存の計算ロジックをそのまま継承 ---
def calculate_angle(a, b, c):
    """3点間の角度を計算する関数"""
    a = np.array(a) # 腰
    b = np.array(b) # 膝
    c = np.array(c) # 足首
    
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians*180.0/np.pi)
    
    if angle > 180.0:
        angle = 360-angle
    return angle

class AITrainerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIパーソナルトレーナー ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数 (シリーズ統一デザイン)
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"

        # MediaPipe Pose初期化 (既存システムを継承)
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.mp_draw = mp.solutions.drawing_utils

        # 状態管理変数 (既存システムを継承)
        self.counter = 0
        self.stage = "UP"
        self.current_angle = 0
        
        # 内部管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.is_training = False
        
        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="💪 AIパーソナルトレーナー", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：左(情報)1, 右(映像)3
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作・ステータスパネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 1. カウント表示
        count_frame = tk.LabelFrame(self.left_panel, text=" 📊 スクワット回数 ", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        count_frame.pack(fill=tk.X, pady=(0, 10))

        self.lbl_count = tk.Label(count_frame, text="0", bg=self.BG_WHITE, 
                                 font=("Impact", 64), fg=self.TEXT_COLOR)
        self.lbl_count.pack(pady=(10, 0))
        tk.Label(count_frame, text="REPS", bg=self.BG_WHITE, font=("Impact", 12), fg="#95A5A6").pack(pady=(0, 10))

        # 2. 状態・角度
        status_frame = tk.LabelFrame(self.left_panel, text=" 👁️ 現在の状態 ", 
                                    font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.lbl_stage = tk.Label(status_frame, text="STAGE: UP", bg=self.BG_WHITE, 
                                 font=("Meiryo", 14, "bold"), fg=self.SAFE_COLOR, pady=10)
        self.lbl_stage.pack()
        
        self.lbl_angle = tk.Label(status_frame, text="膝の角度: 180°", bg=self.BG_WHITE, 
                                 font=("Meiryo", 10), fg=self.TEXT_COLOR, pady=5)
        self.lbl_angle.pack()

        # 3. ログエリア
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 トレーニングログ ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.write_log("システムを起動しました。")

        # 操作ボタン
        self.reset_btn = tk.Button(self.left_panel, text="回数をリセット 🔄", 
                                  command=self.reset_counter,
                                  bg="#BDC3C7", fg="white", font=("Meiryo", 10, "bold"),
                                  relief=tk.FLAT, cursor="hand2", pady=10)
        self.reset_btn.pack(fill=tk.X, pady=5)

        # ガイド
        guide_text = "【使い方】\n・横向きに立ってください。\n・カメラに全身を映してください。\n・深くしゃがむとカウントされます。"
        tk.Label(self.left_panel, text=guide_text, bg="#FFFBEB", justify=tk.LEFT, 
                 font=("Meiryo", 9), fg="#95A5A6").pack(side=tk.BOTTOM, pady=20)

        # --- 右側：カメラプレビュー ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ AIポーズトラッキング画面 ", 
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

    def reset_counter(self):
        self.counter = 0
        self.lbl_count.config(text="0")
        self.write_log("カウンターをリセットしました。")

    def process_pose(self, frame):
        """MediaPipeで姿勢を解析し、カウントを行う (既存ロジックの統合)"""
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb_frame)
        
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            
            # --- 関節座標の取得 (既存の左側判定ロジック) ---
            hip = [landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value].x, 
                   landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value].y]
            knee = [landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE.value].x, 
                    landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE.value].y]
            ankle = [landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value].x, 
                     landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
            
            # 角度計算
            angle = calculate_angle(hip, knee, ankle)
            self.current_angle = int(angle)
            
            # --- カウントロジック (既存システムを厳守) ---
            if angle > 160:
                if self.stage != "UP":
                    self.stage = "UP"
                    self.lbl_stage.config(text="STAGE: UP", fg=self.SAFE_COLOR)
            
            if angle < 90 and self.stage == "UP":
                self.stage = "DOWN"
                self.counter += 1
                self.lbl_count.config(text=str(self.counter))
                self.lbl_stage.config(text="STAGE: DOWN", fg="#E67E22")
                self.write_log(f"Nice Rep! カウント: {self.counter}")

            # 映像への描画 (HUD風)
            # 膝の位置に角度を表示
            cv2.putText(frame, str(int(angle)), 
                       (int(knee[0]*w)+20, int(knee[1]*h)), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
            
            # スケルトンの描画
            self.mp_draw.draw_landmarks(
                frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                self.mp_draw.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2), 
                self.mp_draw.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)
            )

        return frame

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            # 鏡表示にする
            frame = cv2.flip(frame, 1)
            
            # ポーズ解析
            processed_frame = self.process_pose(frame)
            
            # GUI上の情報更新
            self.lbl_angle.config(text=f"膝の角度: {self.current_angle}°")

            # Tkinter Canvasへ転送
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 50 and ch > 50:
                rgb_img = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_img)
                
                fw, fh = pil_img.size
                ratio = min(cw/fw, ch/fh)
                new_size = (int(fw*ratio), int(fh*ratio))
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
    
    app = AITrainerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()