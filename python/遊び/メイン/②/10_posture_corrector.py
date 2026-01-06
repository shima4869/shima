# 姿勢矯正・猫背アラート AI
# インストール: pip install opencv-python mediapipe Pillow requests
# 実行方法: python 10_posture_corrector.py
# Select Interpreter: Python 3.11.9

import cv2
import mediapipe as mp
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext
from PIL import Image, ImageDraw, ImageFont, ImageTk
import requests
import threading
import time
import os

class PostureCorrectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("姿勢矯正・猫背アラート ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB") # クリーム色の背景

        # Discord Webhook設定
        self.DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1444232363637997659/c9oDNYEjj1dqTTGHaVzs4zCQMiH0ulc7hDAONZVHgH-rv_mB9ImpAKZLAF-NhJWe9i5x"
        
        # カラー設定
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.ALERT_COLOR = "#E74C3C"       # 赤
        self.SAFE_COLOR = "#2ECC71"        # 緑
        self.TEXT_COLOR = "#4B4B4B"
        self.BG_WHITE = "#FFFFFF"

        # MediaPipe Pose初期化
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)
        self.mp_draw = mp.solutions.drawing_utils

        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_monitoring = False
        self.base_ear_shoulder_dist = None  # 正しい姿勢の耳と肩の水平距離
        self.bad_posture_start_time = None  # 悪い姿勢が始まった時刻
        self.alert_threshold_sec = 3        # 3秒続いたらアラート
        self.last_discord_time = 0
        self.is_bad_now = False

        self.setup_ui()
        
        # カメラのスレッド開始
        self.thread = threading.Thread(target=self.video_loop, daemon=True)
        self.thread.start()

    def setup_ui(self):
        # タイトル
        title_label = tk.Label(self.root, text="🧘 姿勢矯正・猫背アラート AI", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率：左1, 右3
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))

        # モニター開始ボタン
        self.start_btn = tk.Button(self.left_panel, text="監視を開始する ▶", command=self.toggle_monitoring,
                                  bg=self.SAFE_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                  relief=tk.FLAT, cursor="hand2", pady=15)
        self.start_btn.pack(fill=tk.X, pady=(0, 10))

        # 基準設定ボタン
        self.calibrate_btn = tk.Button(self.left_panel, text="今の姿勢を「正解」にする ✨", command=self.calibrate,
                                      bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 10, "bold"),
                                      relief=tk.FLAT, cursor="hand2", pady=10)
        self.calibrate_btn.pack(fill=tk.X, pady=5)

        # 状態表示
        status_frame = tk.LabelFrame(self.left_panel, text=" 📊 解析データ ", 
                                    font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, pady=15)
        
        self.posture_label = tk.Label(status_frame, text="姿勢: 待機中", bg=self.BG_WHITE, 
                                     font=("Meiryo", 14, "bold"), fg=self.TEXT_COLOR)
        self.posture_label.pack(pady=10)

        self.dist_label = tk.Label(status_frame, text="耳-肩 距離: --", bg=self.BG_WHITE, font=("Meiryo", 9))
        self.dist_label.pack(pady=5)

        # ログ
        self.log_area = scrolledtext.ScrolledText(self.left_panel, height=12, font=("Meiryo", 8), 
                                                 bg="#F7F7F7", relief=tk.FLAT)
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=10)
        self.log("システム準備完了。カメラの横に座ってください。")

        # --- 右側：カメラ表示エリア ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        self.canvas = tk.Canvas(self.right_panel, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_area.see(tk.END)

    def toggle_monitoring(self):
        self.is_monitoring = not self.is_monitoring
        if self.is_monitoring:
            if self.base_ear_shoulder_dist is None:
                messagebox.showwarning("設定が必要です", "先に「正しい姿勢」を記憶させてください。")
                self.is_monitoring = False
                return
            self.start_btn.config(text="監視を停止する ⏹", bg=self.ALERT_COLOR)
            self.log("監視を開始しました。")
        else:
            self.start_btn.config(text="監視を開始する ▶", bg=self.SAFE_COLOR)
            self.log("監視を停止しました。")
            self.is_bad_now = False

    def calibrate(self):
        """現在の姿勢を理想的な姿勢として保存"""
        if hasattr(self, 'last_dist'):
            self.base_ear_shoulder_dist = self.last_dist
            self.log(f"正しい姿勢を記録しました。基準距離: {self.base_ear_shoulder_dist:.2f}")
            messagebox.showinfo("成功", "今の姿勢を正解として保存しました！")

    def send_discord_alert(self):
        """Discordへ通知を送信（連続送信防止：1分間隔）"""
        now = time.time()
        if now - self.last_discord_time < 60:
            return

        payload = {"content": "🚨 **猫背アラート！**\nPC作業中の姿勢が悪くなっています。肩を回して背筋を伸ばしましょう！🧘"}
        try:
            requests.post(self.DISCORD_WEBHOOK_URL, json=payload, timeout=5)
            self.last_discord_time = now
            self.log("Discordへ警告を送信しました。")
        except:
            pass

    def calculate_distance(self, p1, p2):
        """2点間の水平距離を計算（耳と肩の前後関係用）"""
        return abs(p1.x - p2.x)

    def video_loop(self):
        while True:
            ret, frame = self.cap.read()
            if not ret: break
            
            # 横向きを想定して左右反転（必要に応じて調整）
            # frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            
            # AI解析
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(rgb_frame)
            
            is_bad_posture = False
            
            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                
                # 耳 (右耳: 8) と 肩 (右肩: 12) を取得 (横顔想定)
                # 反対側なら 左耳: 7, 左肩: 11
                ear = landmarks[self.mp_pose.PoseLandmark.RIGHT_EAR]
                shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
                
                # 信頼度が低い場合は反対側もチェック
                if ear.visibility < 0.5:
                    ear = landmarks[self.mp_pose.PoseLandmark.LEFT_EAR]
                    shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]

                # 水平距離を計算
                dist = self.calculate_distance(ear, shoulder)
                self.last_dist = dist
                self.root.after(0, lambda d=dist: self.dist_label.config(text=f"耳-肩 水平距離: {d:.4f}"))

                # ランドマーク描画
                self.mp_draw.draw_landmarks(frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)

                # 姿勢判定ロジック
                if self.is_monitoring and self.base_ear_shoulder_dist is not None:
                    # 耳が肩より一定以上前に出たら「猫背/首出し」
                    # 基準より 0.05 (正規化座標) 以上前に出たらアウト
                    if dist > self.base_ear_shoulder_dist + 0.04:
                        is_bad_posture = True

            # アラート管理
            if self.is_monitoring:
                if is_bad_posture:
                    if self.bad_posture_start_time is None:
                        self.bad_posture_start_time = time.time()
                    
                    elapsed = time.time() - self.bad_posture_start_time
                    if elapsed > self.alert_threshold_sec:
                        self.is_bad_now = True
                        self.root.after(0, lambda: self.posture_label.config(text="姿勢: 悪い ⚠️", fg=self.ALERT_COLOR))
                        self.send_discord_alert()
                    else:
                        self.root.after(0, lambda: self.posture_label.config(text=f"姿勢: 注意... ({int(elapsed)}s)", fg="#F39C12"))
                else:
                    self.bad_posture_start_time = None
                    self.is_bad_now = False
                    self.root.after(0, lambda: self.posture_label.config(text="姿勢: 良い ✅", fg=self.SAFE_COLOR))

            # 映像加工（悪い姿勢のときは画面を暗く/赤くする）
            if self.is_bad_now:
                overlay = frame.copy()
                cv2.rectangle(overlay, (0,0), (w,h), (0,0,150), -1) # 赤暗く
                cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
                cv2.putText(frame, "POSTURE ALERT!", (w//2-150, h//2), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 4)

            # GUI表示更新
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 50 and ch > 50:
                img_h, img_w = frame.shape[:2]
                ratio = min(cw/img_w, ch/img_h)
                new_size = (int(img_w*ratio), int(img_h*ratio))
                
                rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_img).resize(new_size, Image.Resampling.LANCZOS)
                self.tk_img = ImageTk.PhotoImage(pil_img)
                
                self.canvas.itemconfig(self.image_item, image=self.tk_img)
                self.canvas.coords(self.image_item, (cw-new_size[0])//2, (ch-new_size[1])//2)

            time.sleep(0.05)

if __name__ == "__main__":
    root = tk.Tk()
    # Windows高DPI対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = PostureCorrectorApp(root)
    # 終了時にカメラ解放
    def on_closing():
        app.cap.release()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()