# 植物の水やり監視ボット AI+
# インストール: pip install opencv-python Pillow requests ultralytics
# 実行方法: python 9_plant_monitor.py
# Select Interpreter: Python 3.11.9

import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
from PIL import Image, ImageDraw, ImageFont, ImageTk
import requests
import threading
import time
import os
from ultralytics import YOLO

class PlantMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("植物の水やり監視ボット 🌿")
        self.root.geometry("1300x900")
        self.root.configure(bg="#FFFBEB")

        # Discord Webhook URL (提供されたもの)
        self.DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1444232363637997659/c9oDNYEjj1dqTTGHaVzs4zCQMiH0ulc7hDAONZVHgH-rv_mB9ImpAKZLAF-NhJWe9i5x"
        
        # カラー設定
        self.PRIMARY_COLOR = "#FF9F43"
        self.SECONDARY_COLOR = "#2ECC71"
        self.ALERT_COLOR = "#E74C3C"
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"

        # AIモデル読み込み (人間検知用)
        self.log("AIモデル(YOLOv8)を読み込み中...")
        self.model = YOLO('yolov8n.pt')
        
        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_monitoring = False
        self.last_notify_time = 0
        self.notify_cooldown = 300 # 5分間は再通知しない
        
        # 検知用の基準値
        self.baseline_height = None
        self.brown_threshold = 5.0 # 茶色い面積が5%を超えたら異常
        self.droop_threshold = 30  # 重心が30ピクセル下がったら異常
        self.human_detected = False

        self.setup_ui()
        
        # カメラのスレッド開始
        self.thread = threading.Thread(target=self.video_loop, daemon=True)
        self.thread.start()

    def setup_ui(self):
        # タイトル
        title_label = tk.Label(self.root, text="🌿 植物の水やり監視ボット AI+", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # --- 左側：操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=350)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 監視スイッチ
        self.monitor_btn = tk.Button(self.left_panel, text="監視を開始する ▶", command=self.toggle_monitoring,
                                    bg=self.SECONDARY_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                    relief=tk.FLAT, cursor="hand2", pady=15)
        self.monitor_btn.pack(fill=tk.X, pady=(0, 10))

        # 基準設定ボタン
        self.base_btn = tk.Button(self.left_panel, text="今の状態を「健康」として記憶", command=self.set_baseline,
                                 bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 10, "bold"),
                                 relief=tk.FLAT, cursor="hand2", pady=10)
        self.base_btn.pack(fill=tk.X, pady=5)

        # ステータス表示
        status_frame = tk.LabelFrame(self.left_panel, text=" 📊 リアルタイム分析 ", font=("Meiryo", 10, "bold"),
                                    bg=self.BG_WHITE, fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, pady=10)
        
        self.human_label = tk.Label(status_frame, text="人間検知: なし", bg=self.BG_WHITE, font=("Meiryo", 10, "bold"), fg="blue")
        self.human_label.pack(anchor="w", padx=10, pady=5)
        
        self.green_label = tk.Label(status_frame, text="緑色(健康)面積: 0%", bg=self.BG_WHITE, font=("Meiryo", 10))
        self.green_label.pack(anchor="w", padx=10, pady=5)
        
        self.brown_label = tk.Label(status_frame, text="茶色(異常)面積: 0%", bg=self.BG_WHITE, font=("Meiryo", 10))
        self.brown_label.pack(anchor="w", padx=10, pady=5)

        self.height_label = tk.Label(status_frame, text="葉の重心(高さ): -", bg=self.BG_WHITE, font=("Meiryo", 10))
        self.height_label.pack(anchor="w", padx=10, pady=5)

        # ログ表示
        self.log_area = scrolledtext.ScrolledText(self.left_panel, height=12, font=("Meiryo", 8), bg="#F7F7F7", relief=tk.FLAT)
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=10)
        self.log("AI監視システム 準備完了。")

        # --- 右側：カメラ表示エリア ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.right_panel, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        if hasattr(self, 'log_area'):
            self.log_area.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_area.see(tk.END)
        else:
            print(f"[{timestamp}] {message}")

    def toggle_monitoring(self):
        self.is_monitoring = not self.is_monitoring
        if self.is_monitoring:
            self.monitor_btn.config(text="監視を停止する ⏹", bg=self.ALERT_COLOR)
            self.log("監視を開始しました。")
        else:
            self.monitor_btn.config(text="監視を開始する ▶", bg=self.SECONDARY_COLOR)
            self.log("監視を停止しました。")

    def set_baseline(self):
        if hasattr(self, 'current_green_height'):
            self.baseline_height = self.current_green_height
            self.log(f"健康な高さを設定しました: {int(self.baseline_height)}")
            messagebox.showinfo("設定完了", "今の植物の状態を基準に設定しました。")

    def send_discord_notification(self, reason):
        """Discordへ通知を送信 (人間がいないときのみ)"""
        if self.human_detected:
            return # 人間が映っているときは誤検知防止のため送らない

        now = time.time()
        if now - self.last_notify_time < self.notify_cooldown:
            return

        payload = {
            "content": f"📢 **植物からのSOS！**\n理由: {reason}\n「水がほしいよ！」🌿💧"
        }
        try:
            response = requests.post(self.DISCORD_WEBHOOK_URL, json=payload, timeout=5)
            if response.status_code == 204:
                self.log("通知成功: 植物が水を求めています。")
                self.last_notify_time = now
        except Exception as e:
            self.log(f"通知エラー: {e}")

    def analyze_plant_and_human(self, frame):
        """人間検知と植物の解析を同時に行う"""
        # 1. 人間検知 (YOLOv8)
        # verbose=False でログを抑制, classes=[0] は人間(person)
        results = self.model(frame, classes=[0], conf=0.4, verbose=False)
        self.human_detected = len(results[0].boxes) > 0
        
        # 2. 植物の色解析
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 緑色の範囲 (健康な葉)
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 255])
        mask_green = cv2.inRange(hsv, lower_green, upper_green)
        
        # 茶色・黄色の範囲 (枯れ・異常)
        lower_brown = np.array([10, 50, 20])
        upper_brown = np.array([30, 255, 200])
        mask_brown = cv2.inRange(hsv, lower_brown, upper_brown)
        
        # 面積比率
        total_pixels = frame.shape[0] * frame.shape[1]
        green_ratio = (cv2.countNonZero(mask_green) / total_pixels) * 100
        brown_ratio = (cv2.countNonZero(mask_brown) / total_pixels) * 100
        
        # 重心の計算 (萎れの検知)
        M = cv2.moments(mask_green)
        height = 0
        if M["m00"] > 0:
            height = int(M["m01"] / M["m00"])

        self.current_green_height = height
        return green_ratio, brown_ratio, height, mask_green, mask_brown, results[0].boxes

    def video_loop(self):
        while True:
            ret, frame = self.cap.read()
            if not ret: break
            
            # AI解析
            green_pct, brown_pct, height, m_green, m_brown, human_boxes = self.analyze_plant_and_human(frame)
            
            # UI更新
            h_text = "⚠️ 人間を検知中 (通知OFF)" if self.human_detected else "✅ 植物のみ検知"
            h_color = "orange" if self.human_detected else "green"
            self.root.after(0, lambda: self.human_label.config(text=h_text, fg=h_color))
            self.root.after(0, lambda: self.green_label.config(text=f"緑色面積: {green_pct:.1f}%"))
            self.root.after(0, lambda: self.brown_label.config(text=f"茶色面積: {brown_pct:.1f}%"))
            self.root.after(0, lambda: self.height_label.config(text=f"重心の高さ: {height}"))

            # 異常検知通知
            if self.is_monitoring and not self.human_detected:
                if brown_pct > self.brown_threshold:
                    self.send_discord_notification(f"葉に茶色の変色を確認 ({brown_pct:.1f}%)")
                
                if self.baseline_height is not None:
                    if height > self.baseline_height + self.droop_threshold:
                        self.send_discord_notification("植物が萎れています (重心の低下を検知)")

            # 表示用ビジュアル
            # 人間の枠を描画
            for box in human_boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(frame, "HUMAN", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

            # 茶色部分を強調表示
            frame[m_brown > 0] = [0, 0, 255]
            
            # 植物の重心を表示
            if height > 0:
                cv2.circle(frame, (frame.shape[1]//2, height), 8, (255, 159, 67), -1)

            # Tkinter Canvasへの表示
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 10 and ch > 10:
                frame_resized = cv2.resize(frame, (cw, ch))
                rgb_img = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                img_tk = ImageTk.PhotoImage(Image.fromarray(rgb_img))
                self.canvas.itemconfig(self.image_item, image=img_tk)
                self.tk_img = img_tk

            time.sleep(0.05)

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = PlantMonitorApp(root)
    root.mainloop()