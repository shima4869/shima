# ナンバープレート自動読み取りシステム
# インストール: pip install opencv-python pytesseract pillow numpy
# 実行方法: python 6_alpr_system.py
# Select Interpreter: Python 3.11.9

import cv2
import pytesseract
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk
import platform
import os
import sys
import re
import datetime
import threading
import time

class AlprSystemApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ナンバープレート自動読み取りシステム ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.SAFE_COLOR = "#2ECC71"        # 緑
        self.TEXT_COLOR = "#4B4B4B"
        self.BG_WHITE = "#FFFFFF"

        # --- 既存システムの継承設定 ---
        self._setup_tesseract_path()
        self.min_area = 1000
        self.max_area = 15000
        self.save_dir = "plate_logs"
        os.makedirs(self.save_dir, exist_ok=True)

        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.frame_count = 0
        self.skip_frames = 5
        self.detection_cooldown = 0
        self.last_detected_text = ""
        self.current_plate_cnt = None

        self.setup_ui()
        
        # メインループ開始
        self.update_loop()

    def _setup_tesseract_path(self):
        """既存のTesseractパス設定ロジック"""
        system = platform.system()
        if system == "Windows":
            paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                os.getenv("TESSERACT_PATH", "")
            ]
            for p in paths:
                if os.path.exists(p):
                    pytesseract.pytesseract.tesseract_cmd = p
                    break

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🚗 ナンバープレート自動読み取りシステム", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：左1, 右4
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=4)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作・情報パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 現在の認識結果
        res_frame = tk.LabelFrame(self.left_panel, text=" 👁️ 最新の認識 ", 
                                 font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        res_frame.pack(fill=tk.X, pady=(0, 10))

        self.plate_label = tk.Label(res_frame, text="スキャン中...", bg=self.BG_WHITE, 
                                   font=("Consolas", 22, "bold"), fg=self.TEXT_COLOR, pady=20)
        self.plate_label.pack()

        # 認識履歴ログ
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 認識履歴 ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Consolas", 10), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.write_log("システム準備完了。")

        # ヒント
        hint_label = tk.Label(self.left_panel, text="認識のコツ:\nプレートを正面から映し、\n手ブレに注意してください。", 
                             bg="#FFFBEB", fg="#95A5A6", font=("Meiryo", 9), justify=tk.LEFT)
        hint_label.pack(side=tk.BOTTOM, pady=10)

        # --- 右側：映像プレビュー ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ カメラ映像 (OCR解析) ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def write_log(self, message):
        """履歴エリアに追記"""
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def preprocess_image(self, img):
        """既存の画像前処理ロジック"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.bilateralFilter(gray, 11, 17, 17)
        edged = cv2.Canny(blur, 30, 200)
        return edged

    def find_plate_contour(self, edged_img):
        """既存の輪郭検出ロジック"""
        contours, _ = cv2.findContours(edged_img.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.018 * peri, True)
            if len(approx) == 4:
                area = cv2.contourArea(c)
                if self.min_area < area < self.max_area:
                    return approx
        return None

    def ocr_plate(self, plate_img):
        """既存のOCR実行ロジック"""
        gray_plate = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        _, binary_plate = cv2.threshold(gray_plate, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        custom_config = r'--oem 3 --psm 7'
        try:
            text = pytesseract.image_to_string(binary_plate, config=custom_config, lang='eng')
            clean_text = re.sub(r'[^A-Z0-9-]', '', text.strip())
            return clean_text
        except:
            return ""

    def save_log(self, frame, text):
        """既存の画像保存ロジック"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.save_dir}/plate_{timestamp}_{text}.jpg"
        cv2.imwrite(filename, frame)
        self.write_log(f"記録: {text}")

    def update_loop(self):
        """メインの更新処理ループ"""
        ret, frame = self.cap.read()
        if ret:
            # 防犯・監視用なので鏡像反転は行わない（必要に応じて cv2.flip してください）
            display_frame = frame.copy()
            self.frame_count += 1
            
            # 解析処理 (5フレームに1回)
            if self.frame_count % self.skip_frames == 0:
                try:
                    processed = self.preprocess_image(frame)
                    plate_cnt = self.find_plate_contour(processed)
                    self.current_plate_cnt = plate_cnt
                    
                    if plate_cnt is not None:
                        (x, y, w, h) = cv2.boundingRect(plate_cnt)
                        if w > 10 and h > 10:
                            plate_roi = frame[y:y+h, x:x+w]
                            text = self.ocr_plate(plate_roi)
                            
                            if len(text) >= 3:
                                self.last_detected_text = text
                                self.plate_label.config(text=text, fg=self.SAFE_COLOR)
                                
                                if self.detection_cooldown == 0:
                                    self.save_log(frame, text)
                                    self.detection_cooldown = 30
                except:
                    pass

            if self.detection_cooldown > 0:
                self.detection_cooldown -= 1

            # 描画処理 (検出枠)
            if self.current_plate_cnt is not None:
                cv2.drawContours(display_frame, [self.current_plate_cnt], -1, (0, 255, 0), 3)

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
    
    app = AlprSystemApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()