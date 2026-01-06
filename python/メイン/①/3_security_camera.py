# 不審者検知・防犯システム AI
# インストール: pip install opencv-python ultralytics pillow requests
# 実行方法: python 3_security_camera.py
# Select Interpreter: Python 3.11.9

import cv2
from ultralytics import YOLO
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk
import requests
import threading
import time
import os
import datetime
import sys

class IntruderSecurityApp:
    def __init__(self, root):
        self.root = root
        self.root.title("不審者検知・防犯システム AI ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー設定
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.ALERT_COLOR = "#E74C3C"       # 赤
        self.SAFE_COLOR = "#2ECC71"        # 緑
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"

        # --- 既存システムの継承設定 ---
        self.discord_webhook_url = "https://discord.com/api/webhooks/1444232363637997659/c9oDNYEjj1dqTTGHaVzs4zCQMiH0ulc7hDAONZVHgH-rv_mB9ImpAKZLAF-NhJWe9i5x"
        self.line_notify_token = "YOUR_LINE_TOKEN"
        self.cooldown_seconds = 10
        self.save_dir = "captures"
        self.skip_frames = 5
        os.makedirs(self.save_dir, exist_ok=True)

        # 状態管理
        self.is_monitoring = False
        self.last_alert_time = 0
        self.frame_count = 0
        self.detected_boxes = []
        self.is_running = True

        # AIモデル読み込み
        try:
            self.model = YOLO('yolov8n.pt')
        except Exception as e:
            messagebox.showerror("エラー", f"AIモデルの読み込みに失敗しました: {e}")
            sys.exit(1)

        # カメラ初期化
        self.cap = cv2.VideoCapture(0)
        
        self.setup_ui()
        
        # メインループ開始
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🚨 不審者検知・防犯システム", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：左1, 右4
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=4)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=350)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 監視スイッチ
        self.toggle_btn = tk.Button(self.left_panel, text="監視を開始する ▶", 
                                   command=self.toggle_monitoring,
                                   bg=self.SAFE_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                   relief=tk.FLAT, cursor="hand2", pady=15)
        self.toggle_btn.pack(fill=tk.X, pady=(0, 10))

        # ステータス表示
        status_frame = tk.LabelFrame(self.left_panel, text=" 📊 監視ステータス ", 
                                    font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, pady=10)
        
        self.status_label = tk.Label(status_frame, text="待機中", bg=self.BG_WHITE, 
                                    font=("Meiryo", 14, "bold"), fg=self.TEXT_COLOR, pady=10)
        self.status_label.pack()

        # ログエリア
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 リアルタイム・ログ ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.write_log("システム準備完了。")

        # 設定情報
        config_label = tk.Label(self.left_panel, text=f"通知先: Discord Webhook\nクールダウン: {self.cooldown_seconds}秒", 
                               bg="#FFFBEB", fg="#95A5A6", font=("Meiryo", 8), justify=tk.LEFT)
        config_label.pack(side=tk.BOTTOM, pady=10)

        # --- 右側：映像プレビュー ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ カメラ映像 (AI人物検知) ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def write_log(self, message):
        """ログエリアにメッセージを追記"""
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def toggle_monitoring(self):
        """監視のON/OFF切り替え"""
        self.is_monitoring = not self.is_monitoring
        if self.is_monitoring:
            self.toggle_btn.config(text="監視を停止する ⏹", bg=self.ALERT_COLOR)
            self.status_label.config(text="👮 監視中...", fg=self.ALERT_COLOR)
            self.write_log("監視を開始しました。")
        else:
            self.toggle_btn.config(text="監視を開始する ▶", bg=self.SAFE_COLOR)
            self.status_label.config(text="待機中", fg=self.TEXT_COLOR)
            self.write_log("監視を停止しました。")
            self.detected_boxes = []

    def send_discord_notification(self, image_path):
        """既存のDiscord通知ロジック"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(image_path, 'rb') as f:
                payload = {"content": f"🚨 **不審者検知アラート**\n日時: {timestamp}\nカメラが人物を検出しました。"}
                files = {"file": f}
                requests.post(self.discord_webhook_url, data=payload, files=files, timeout=10)
            self.write_log("Discordへ通知を送信しました。")
        except Exception as e:
            self.write_log(f"通知失敗: {e}")

    def trigger_alert(self, frame):
        """既存のアラート実行ロジック"""
        current_time = time.time()
        if current_time - self.last_alert_time < self.cooldown_seconds:
            return

        self.last_alert_time = current_time
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.save_dir}/intruder_{timestamp_str}.jpg"
        
        try:
            cv2.imwrite(filename, frame)
            self.write_log(f"人物を検知！画像を保存しました。")
            
            # 非同期で通知
            threading.Thread(target=self.send_discord_notification, args=(filename,), daemon=True).start()
        except Exception as e:
            self.write_log(f"保存エラー: {e}")

    def update_loop(self):
        """メインの更新処理ループ"""
        ret, frame = self.cap.read()
        if ret:
            # 鏡像ではなく防犯カメラとして正像で表示（必要ならflip）
            # frame = cv2.flip(frame, 1) 
            h, w, _ = frame.shape
            self.frame_count += 1
            person_detected = False

            # AI推論（監視中のみ、かつ指定フレームごと）
            if self.is_monitoring and (self.frame_count % self.skip_frames == 0):
                results = self.model(frame, stream=True, verbose=False, conf=0.5, imgsz=320)
                self.detected_boxes = []
                for result in results:
                    for box in result.boxes:
                        if int(box.cls[0]) == 0: # Person
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            conf = float(box.conf[0])
                            self.detected_boxes.append((x1, y1, x2, y2, conf))
                            person_detected = True
                
                if person_detected:
                    self.trigger_alert(frame)

            # 描画処理
            display_frame = frame.copy()
            for (x1, y1, x2, y2, conf) in self.detected_boxes:
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                label = f"PERSON {conf:.2f}"
                cv2.putText(display_frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            # Canvasへ表示
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 50 and ch > 50:
                rgb_img = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_img)
                
                # アスペクト比維持
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

if __name__ == "__main__":
    root = tk.Tk()
    # Windows高DPI対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = IntruderSecurityApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()