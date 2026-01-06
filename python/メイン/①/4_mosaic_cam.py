# 自動モザイク・プライバシーカメラ AI
# インストール: pip install opencv-python mediapipe pillow numpy
# 実行方法: python 4_mosaic_cam.py
# Select Interpreter: Python 3.11.9

import cv2
import mediapipe as mp
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk, filedialog
from PIL import Image, ImageDraw, ImageFont, ImageTk
import datetime
import threading
import time
import os

class MosaicCamApp:
    def __init__(self, root):
        self.root = root
        self.root.title("自動モザイク・プライバシーカメラ ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー設定
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.SAFE_COLOR = "#2ECC71"        # 緑
        self.ALERT_COLOR = "#E74C3C"       # 赤
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"

        # MediaPipe Face Detection 初期化
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=0, 
            min_detection_confidence=0.5
        )

        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.mode = "mosaic" # mosaic, blur, none
        self.last_display_frame = None

        self.setup_ui()
        
        # UI更新ループ開始
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🛡️ 自動モザイク・プライバシーカメラ", 
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

        # モード選択
        mode_frame = tk.LabelFrame(self.left_panel, text=" 🎭 加工モード選択 ", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        mode_frame.pack(fill=tk.X, pady=(0, 10))

        self.mode_buttons = {}
        modes = [("mosaic", "モザイク (M)"), ("blur", "ぼかし (B)"), ("none", "なし (N)")]
        for m_id, label in modes:
            btn = tk.Button(mode_frame, text=label, command=lambda m=m_id: self.change_mode(m),
                           bg="#F7F7F7", font=("Meiryo", 10, "bold"), pady=10, 
                           relief=tk.FLAT, cursor="hand2")
            btn.pack(fill=tk.X, padx=10, pady=5)
            self.mode_buttons[m_id] = btn

        self.update_button_highlight()

        # 撮影ボタン
        self.shot_btn = tk.Button(self.left_panel, text="今の画面を保存 📸 (S)", 
                                 command=self.save_screenshot,
                                 bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                 relief=tk.FLAT, cursor="hand2", pady=15)
        self.shot_btn.pack(fill=tk.X, pady=15)

        # ログエリア
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 動作ログ ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.write_log("システム準備完了。カメラを起動しました。")

        # --- 右側：映像プレビュー ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ カメラ映像 (リアルタイム加工) ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

        # キーボードショートカット設定
        self.root.bind('<m>', lambda e: self.change_mode("mosaic"))
        self.root.bind('<b>', lambda e: self.change_mode("blur"))
        self.root.bind('<n>', lambda e: self.change_mode("none"))
        self.root.bind('<s>', lambda e: self.save_screenshot())

    def write_log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def change_mode(self, new_mode):
        self.mode = new_mode
        self.update_button_highlight()
        self.write_log(f"モードを {new_mode.upper()} に変更しました。")

    def update_button_highlight(self):
        for m_id, btn in self.mode_buttons.items():
            if m_id == self.mode:
                btn.config(bg=self.SECONDARY_COLOR, fg=self.TEXT_COLOR)
            else:
                btn.config(bg="#F7F7F7", fg=self.TEXT_COLOR)

    def apply_mosaic(self, image, x, y, w, h, ratio=0.08):
        """既存のモザイクロジック"""
        h_img, w_img = image.shape[:2]
        x, y = max(0, x), max(0, y)
        w, h = min(w, w_img - x), min(h, h_img - y)
        if w <= 0 or h <= 0: return image
        face_roi = image[y:y+h, x:x+w]
        small = cv2.resize(face_roi, None, fx=ratio, fy=ratio, interpolation=cv2.INTER_NEAREST)
        mosaic_face = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
        image[y:y+h, x:x+w] = mosaic_face
        return image

    def apply_blur(self, image, x, y, w, h):
        """既存のぼかしロジック"""
        h_img, w_img = image.shape[:2]
        x, y = max(0, x), max(0, y)
        w, h = min(w, w_img - x), min(h, h_img - y)
        if w <= 0 or h <= 0: return image
        face_roi = image[y:y+h, x:x+w]
        blur_face = cv2.GaussianBlur(face_roi, (99, 99), 30)
        image[y:y+h, x:x+w] = blur_face
        return image

    def save_screenshot(self):
        if self.last_display_frame is not None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"shot_{timestamp}.jpg"
            cv2.imwrite(filename, self.last_display_frame)
            self.write_log(f"保存完了: {filename}")
            messagebox.showinfo("保存完了", f"画像を保存しました:\n{filename}")

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1) # 鏡表示
            h_img, w_img, _ = frame.shape
            
            # AI顔検出
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_detection.process(rgb_frame)
            
            processed_frame = frame.copy()
            if results.detections:
                for detection in results.detections:
                    bboxC = detection.location_data.relative_bounding_box
                    margin = 20
                    x = int(bboxC.xmin * w_img) - margin
                    y = int(bboxC.ymin * h_img) - margin * 2
                    w = int(bboxC.width * w_img) + margin * 2
                    h = int(bboxC.height * h_img) + margin * 2

                    if self.mode == "mosaic":
                        processed_frame = self.apply_mosaic(processed_frame, x, y, w, h)
                    elif self.mode == "blur":
                        processed_frame = self.apply_blur(processed_frame, x, y, w, h)

            self.last_display_frame = processed_frame.copy()

            # Canvas表示
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 50 and ch > 50:
                # BGR -> RGB 変換
                frame_rgb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
                
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
    
    app = MosaicCamApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()