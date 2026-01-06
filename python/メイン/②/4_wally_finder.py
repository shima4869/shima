# AIウォーリー探せ！アプリケーション
# インストール: pip install ultralytics opencv-python Pillow numpy
# 実行方法: python 4_wally_finder.py
# Select Interpreter: Python 3.11.9

import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageTk
from ultralytics import YOLO
import threading
import os
import time

class WallyFinderLogic:
    """元のスクリプトから継承した検出ロジッククラス"""
    def __init__(self):
        # 人物検出用のYOLOモデル読み込み
        self.model = YOLO('yolov8n.pt')
        self.conf_threshold = 0.3
        self.min_red_ratio = 0.10
        self.min_white_ratio = 0.10

    def detect_color_ratio(self, img_roi):
        if img_roi is None or img_roi.size == 0: return 0, 0
        hsv = cv2.cvtColor(img_roi, cv2.COLOR_BGR2HSV)
        height, width = hsv.shape[:2]
        total_pixels = height * width
        if total_pixels == 0: return 0, 0

        # 赤色の範囲
        lower_red1, upper_red1 = np.array([0, 70, 50]), np.array([10, 255, 255])
        lower_red2, upper_red2 = np.array([170, 70, 50]), np.array([180, 255, 255])
        mask_red = cv2.bitwise_or(cv2.inRange(hsv, lower_red1, upper_red1), cv2.inRange(hsv, lower_red2, upper_red2))
        
        # 白色の範囲
        lower_white, upper_white = np.array([0, 0, 200]), np.array([180, 50, 255])
        mask_white = cv2.inRange(hsv, lower_white, upper_white)

        return cv2.countNonZero(mask_red) / total_pixels, cv2.countNonZero(mask_white) / total_pixels

    def find_wally(self, image):
        results = self.model(image, classes=[0], conf=self.conf_threshold, verbose=False)
        output_image = image.copy()
        found_count = 0

        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                w, h = x2 - x1, y2 - y1
                if x1 < 0 or y1 < 0 or w <= 0 or h <= 0: continue

                # 上半身の色判定
                body_y1, body_y2 = y1 + int(h * 0.15), y1 + int(h * 0.5)
                roi = image[body_y1:body_y2, x1:x2]
                
                red_rate, white_rate = self.detect_color_ratio(roi)
                if (red_rate > self.min_red_ratio) and (white_rate > self.min_white_ratio):
                    found_count += 1
                    cv2.circle(output_image, (x1 + w // 2, y1 + h // 3), max(w, h) // 2, (0, 0, 255), 3)
                    cv2.putText(output_image, "WALLY FOUND!", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        return output_image, found_count

class WallyFinderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIウォーリー探せ！ ✨")
        self.root.geometry("1400x850")
        self.root.configure(bg="#FFFBEB")

        # カラー設定
        self.PRIMARY_COLOR = "#FF9F43"
        self.SECONDARY_COLOR = "#FFCC33"
        self.SUCCESS_COLOR = "#2ECC71"
        self.TEXT_COLOR = "#4B4B4B"
        self.BG_WHITE = "#FFFFFF"

        # AIロジック
        self.finder = WallyFinderLogic()
        
        # 状態管理
        self.cap = None
        self.is_camera_on = False
        self.current_display_img = None # OpenCV形式
        
        self.setup_ui()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🔍 AIウォーリー探せ！", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        # メインコンテナ
        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：左(操作)1, 右(表示)12
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=12)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))

        # モード選択フレーム
        mode_frame = tk.LabelFrame(self.left_panel, text=" 🕹️ モード選択 ", 
                                   font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        mode_frame.pack(fill=tk.X, pady=(0, 10))

        # 画像から探す
        self.file_btn = tk.Button(mode_frame, text="画像ファイルを開く 📁", command=self.open_file,
                                 bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 11, "bold"),
                                 relief=tk.FLAT, cursor="hand2", pady=10)
        self.file_btn.pack(fill=tk.X, padx=10, pady=10)

        # カメラ起動
        self.cam_btn = tk.Button(mode_frame, text="カメラを起動する 📷", command=self.toggle_camera,
                                bg=self.SECONDARY_COLOR, fg="white", font=("Meiryo", 11, "bold"),
                                relief=tk.FLAT, cursor="hand2", pady=10)
        self.cam_btn.pack(fill=tk.X, padx=10, pady=(0, 10))

        # 保存ボタン
        self.save_btn = tk.Button(self.left_panel, text="結果を保存 💾", command=self.save_result,
                                 bg="#BDC3C7", fg="white", font=("Meiryo", 11, "bold"),
                                 relief=tk.FLAT, cursor="hand2", pady=10, state=tk.DISABLED)
        self.save_btn.pack(fill=tk.X, pady=10)

        # ステータス表示
        self.status_label = tk.Label(self.left_panel, text="準備完了！", 
                                    bg="#FFFBEB", fg=self.TEXT_COLOR, font=("Meiryo", 10))
        self.status_label.pack(pady=20)

        # プログラム情報
        info_label = tk.Label(self.left_panel, text="AIが赤と白の縞々を\n自動で判別します。", 
                             bg="#FFFBEB", fg="#95A5A6", font=("Meiryo", 9), justify=tk.LEFT)
        info_label.pack(side=tk.BOTTOM, pady=10)

        # --- 右側：プレビューパネル ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ 探索結果プレビュー ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="#F7F7F7", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def update_display(self, cv_img):
        """OpenCVの画像をTkinterのCanvasに表示"""
        self.current_display_img = cv_img
        
        # 表示サイズ計算
        self.root.update_idletasks()
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw < 10 or ch < 10: return

        # リサイズ
        img_h, img_w = cv_img.shape[:2]
        ratio = min(cw / img_w, ch / img_h)
        new_size = (int(img_w * ratio), int(img_h * ratio))
        
        # BGR -> RGB 変換
        rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img).resize(new_size, Image.Resampling.LANCZOS)
        
        self.tk_img = ImageTk.PhotoImage(pil_img)
        self.canvas.itemconfig(self.image_item, image=self.tk_img)
        self.canvas.coords(self.image_item, (cw - new_size[0]) // 2, (ch - new_size[1]) // 2)
        
        # 保存ボタン有効化
        self.save_btn.config(state=tk.NORMAL, bg=self.SUCCESS_COLOR)

    def open_file(self):
        if self.is_camera_on: self.toggle_camera()
        
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp")])
        if not path: return

        self.status_label.config(text="✨ AIが探索中...", fg=self.PRIMARY_COLOR)
        self.root.update()

        img = cv2.imread(path)
        if img is None:
            messagebox.showerror("エラー", "画像を読み込めませんでした。")
            return

        result_img, count = self.finder.find_wally(img)
        self.update_display(result_img)
        self.status_label.config(text=f"✅ {count}人の候補を発見！", fg="green")

    def toggle_camera(self):
        if not self.is_camera_on:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                messagebox.showerror("カメラエラー", "カメラを起動できませんでした。")
                return
            
            self.is_camera_on = True
            self.cam_btn.config(text="カメラを停止 ⏹️", bg="#E74C3C")
            self.status_label.config(text="📸 リアルタイム探索中...", fg=self.PRIMARY_COLOR)
            
            # カメラループを別スレッドで開始
            self.thread = threading.Thread(target=self.camera_loop, daemon=True)
            self.thread.start()
        else:
            self.is_camera_on = False
            self.cam_btn.config(text="カメラを起動する 📷", bg=self.SECONDARY_COLOR)
            self.status_label.config(text="カメラを停止しました", fg=self.TEXT_COLOR)
            if self.cap:
                self.cap.release()

    def camera_loop(self):
        while self.is_camera_on:
            ret, frame = self.cap.read()
            if not ret: break
            
            result_img, count = self.finder.find_wally(frame)
            
            # メインスレッドでUI更新
            self.root.after(0, self.update_display, result_img)
            time.sleep(0.01)

    def save_result(self):
        if self.current_display_img is None: return
        
        path = filedialog.asksaveasfilename(defaultextension=".jpg",
                                            filetypes=[("JPEG Image", "*.jpg"), ("PNG Image", "*.png")])
        if path:
            cv2.imwrite(path, self.current_display_img)
            messagebox.showinfo("保存完了", f"結果を保存しました：\n{path}")

if __name__ == "__main__":
    root = tk.Tk()
    # 高DPI対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = WallyFinderApp(root)
    root.mainloop()