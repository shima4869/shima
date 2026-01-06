# AI居眠り防止・覚醒アラート + Discord通知 ✨
# インストール: pip install tkinter mediapipe opencv-python numpy pillow requests
# 実行方法: python drowsiness_monitor.py
# Select Interpreter: Python 3.11.9

import cv2
import mediapipe as mp
import numpy as np
import time
import math
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import os
import sys
import threading
import requests
import datetime

# --- 設定項目 ---
# ユーザー指定のWebhook URL
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1444232363637997659/c9oDNYEjj1dqTTGHaVzs4zCQMiH0ulc7hDAONZVHgH-rv_mB9ImpAKZLAF-NhJWe9i5x"

# --- 既存の計算ロジックを継承 ---

def distance(p1, p2):
    """2点間の距離を計算する関数"""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def calculate_ear(landmarks, indices, w, h):
    """EAR（目の開き具合）を計算する関数"""
    points = []
    for i in indices:
        lm = landmarks[i]
        points.append((lm.x * w, lm.y * h))

    vertical1 = distance(points[1], points[5])
    vertical2 = distance(points[2], points[4])
    horizontal = distance(points[0], points[3])

    ear = (vertical1 + vertical2) / (2.0 * horizontal)
    return ear

class DrowsinessApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI居眠り防止・覚醒アラート + Discord通知 ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"
        self.SECONDARY_COLOR = "#FFCC33"
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"
        self.ALERT_COLOR = "#E74C3C"

        # 判定パラメータ
        self.EAR_THRESHOLD = 0.23
        self.CLOSED_TIME_THRESHOLD = 1.2 # 1.2秒以上閉じたら警告
        
        # 状態管理
        self.eyes_closed_start_time = None
        self.warning_status = False
        self.current_ear = 0.0
        self.closed_duration = 0.0
        self.last_discord_time = 0 # 最後に通知を送った時刻
        self.discord_cooldown = 60 # 通知間隔（秒）

        # MediaPipe初期化
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        
        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="👁️ AI 居眠り監視・Discord緊急通知", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：解析パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # EAR表示
        ear_frame = tk.LabelFrame(self.left_panel, text=" 📊 解析データ ", 
                                 font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        ear_frame.pack(fill=tk.X, pady=(0, 10))

        self.lbl_ear_value = tk.Label(ear_frame, text="0.00", bg=self.BG_WHITE, 
                                     font=("Impact", 48), fg=self.TEXT_COLOR)
        self.lbl_ear_value.pack(pady=10)
        self.ear_bar = ttk.Progressbar(ear_frame, orient="horizontal", mode="determinate", length=300)
        self.ear_bar.pack(padx=20, pady=(0, 20))

        # 覚醒状態
        status_frame = tk.LabelFrame(self.left_panel, text=" 👁️ 覚醒状態 ", 
                                    font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, pady=5)
        self.lbl_status = tk.Label(status_frame, text="監視中", bg=self.BG_WHITE, 
                                  font=("Meiryo", 18, "bold"), fg=self.SAFE_COLOR, pady=15)
        self.lbl_status.pack()

        # ログ
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 イベント履歴 ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.write_log("システム起動。監視を開始します。")

        # 通知先情報
        info_text = "【緊急連絡先】\nDiscord Webhook連携済み\n居眠り検知時に自動で画像を送信します。"
        tk.Label(self.left_panel, text=info_text, bg="#FFFBEB", justify=tk.LEFT, 
                 font=("Meiryo", 9), fg="#95A5A6").pack(side=tk.BOTTOM, pady=20)

        # --- 右側：映像パネル ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ リアルタイム・ドライバーモニター ", 
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

    def send_discord_notification(self, frame):
        """画像をDiscordへ送信する処理 (非同期実行)"""
        now = time.time()
        # クールダウンチェック
        if now - self.last_discord_time < self.discord_cooldown:
            return
        
        self.last_discord_time = now
        
        def _task():
            try:
                # フレームを一時的にファイル保存
                filename = "drowsiness_alert.jpg"
                cv2.imwrite(filename, frame)
                
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                payload = {"content": f"🚨 **【居眠り検知アラート】**\n日時: {timestamp}\nドライバーが居眠りをしている可能性があります。至急確認してください！"}
                
                with open(filename, 'rb') as f:
                    files = {'file': (filename, f, 'image/jpeg')}
                    response = requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files, timeout=15)
                
                if response.status_code == 200 or response.status_code == 204:
                    self.root.after(0, lambda: self.write_log("✅ Discordへ緊急画像を送信しました"))
                else:
                    self.root.after(0, lambda: self.write_log(f"❌ 通信失敗: {response.status_code}"))
                
                # 後片付け
                if os.path.exists(filename):
                    os.remove(filename)
            except Exception as e:
                self.root.after(0, lambda: self.write_log(f"❌ 送信エラー: {e}"))

        threading.Thread(target=_task, daemon=True).start()

    def draw_eye_contours(self, frame, landmarks, indices, w, h, color):
        points = []
        for i in indices:
            lm = landmarks[i]
            points.append((int(lm.x * w), int(lm.y * h)))
        cv2.polylines(frame, [np.array(points)], True, color, 1, cv2.LINE_AA)

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1) # 鏡像
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb_frame)
            
            self.warning_status = False
            self.current_ear = 0.0

            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    # EAR計算
                    left_ear = calculate_ear(face_landmarks.landmark, [33, 160, 158, 133, 153, 144], w, h)
                    right_ear = calculate_ear(face_landmarks.landmark, [362, 385, 387, 263, 373, 380], w, h)
                    self.current_ear = (left_ear + right_ear) / 2.0

                    # 居眠り判定
                    if self.current_ear < self.EAR_THRESHOLD:
                        if self.eyes_closed_start_time is None:
                            self.eyes_closed_start_time = time.time()
                        
                        self.closed_duration = time.time() - self.eyes_closed_start_time
                        if self.closed_duration > self.CLOSED_TIME_THRESHOLD:
                            self.warning_status = True
                            # Discordへ通知
                            self.send_discord_notification(frame)
                    else:
                        self.eyes_closed_start_time = None
                        self.closed_duration = 0.0

                    # 描画処理
                    status_color_bgr = (46, 204, 113) if not self.warning_status else (60, 76, 231)
                    self.draw_eye_contours(frame, face_landmarks.landmark, [33, 160, 158, 133, 153, 144], w, h, status_color_bgr)
                    self.draw_eye_contours(frame, face_landmarks.landmark, [362, 385, 387, 263, 373, 380], w, h, status_color_bgr)

                    if self.warning_status:
                        cv2.putText(frame, "WAKE UP!!!", (w//2-180, h//2), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 2.5, (60, 76, 231), 6, cv2.LINE_AA)
                        cv2.rectangle(frame, (0,0), (w,h), (60, 76, 231), 20)
                        
                        if int(self.closed_duration * 10) % 10 == 0:
                            self.write_log(f"⚠️ 警告: 居眠りを検知 ({self.closed_duration:.1f}秒)")

            # GUI更新
            self.lbl_ear_value.config(text=f"{self.current_ear:.2f}")
            self.ear_bar["value"] = min(100, self.current_ear * 200)
            
            if self.warning_status:
                self.lbl_status.config(text="⚠️ 警告：居眠り検知", fg=self.ALERT_COLOR)
                self.lbl_ear_value.config(fg=self.ALERT_COLOR)
            elif self.current_ear > 0:
                self.lbl_status.config(text="✅ 覚醒状態：良好", fg=self.SAFE_COLOR)
                self.lbl_ear_value.config(fg=self.TEXT_COLOR)
            else:
                self.lbl_status.config(text="顔が見つかりません", fg="#95A5A6")

            # Canvas表示
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 50 and ch > 50:
                rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
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
        sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    app = DrowsinessApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()