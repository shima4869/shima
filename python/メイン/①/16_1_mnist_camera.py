# AI手書き数字認識カメラ ✨
# インストール: pip install opencv-python joblib numpy pillow
# 実行方法: python 16_1_mnist_camera.py
# Select Interpreter: Python 3.11.9

import cv2
import joblib
import numpy as np
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk
import threading
import time
import os
import sys

class MnistCameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI手書き数字認識カメラ ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"        # 緑

        # --- 既存システムのモデル読み込み ---
        try:
            self.model = joblib.load("mnist_model.pkl")
        except:
            messagebox.showerror("エラー", "モデルファイル(mnist_model.pkl)が見つかりません。\n先に学習を実行してください。")
            sys.exit(1)

        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        
        # --- 【修正】認識エリアのサイズを拡大 (220 -> 350) ---
        self.rect_size = 350 
        
        # 認識結果の保持
        self.current_prediction = "-"
        self.current_probability = 0.0
        self.debug_view_img = np.zeros((100, 100, 3), dtype=np.uint8)

        self.setup_ui()
        
        # メインループ開始
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🔢 AI手書き数字認識カメラ", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：左1, 右3
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：解析パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 判定結果表示
        res_frame = tk.LabelFrame(self.left_panel, text=" 👁️ AIの判定結果 ", 
                                 font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        res_frame.pack(fill=tk.X, pady=(0, 10))

        self.result_label = tk.Label(res_frame, text="-", bg=self.BG_WHITE, 
                                    font=("Helvetica", 64, "bold"), fg=self.TEXT_COLOR)
        self.result_label.pack(pady=10)

        # 確信度（プログレスバー）
        prob_frame = tk.Frame(res_frame, bg=self.BG_WHITE)
        prob_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        self.prob_text_label = tk.Label(prob_frame, text="確信度: 0%", bg=self.BG_WHITE, font=("Meiryo", 10))
        self.prob_text_label.pack()
        
        self.prob_bar = ttk.Progressbar(prob_frame, orient="horizontal", mode="determinate")
        self.prob_bar.pack(fill=tk.X, pady=5)

        # AIが見ている画像（デバッグ用）
        debug_frame = tk.LabelFrame(self.left_panel, text=" 🔬 AIが見ている世界 (28x28) ", 
                                   font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        debug_frame.pack(fill=tk.X, pady=10)
        
        self.debug_canvas = tk.Canvas(debug_frame, width=200, height=200, bg="#222", highlightthickness=0)
        self.debug_canvas.pack(pady=15)
        self.debug_image_item = self.debug_canvas.create_image(0, 0, anchor=tk.NW)

        # 操作ガイド
        guide_label = tk.Label(self.left_panel, text="使い方:\nオレンジの大きな枠の中に、白い紙に\n太く書いた数字を入れてください。\n枠が大きくなり、使いやすくなりました！", 
                              bg="#FFFBEB", fg="#95A5A6", font=("Meiryo", 9), justify=tk.LEFT)
        guide_label.pack(side=tk.BOTTOM, pady=10)

        # --- 右側：カメラプレビュー ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ リアルタイム・スキャン画面 ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def process_digit(self, frame):
        """既存のMNIST画像処理ロジックを継承（サイズ拡大対応）"""
        h, w, _ = frame.shape
        # 1. 認識エリア（ROI）の座標計算
        # 枠がはみ出さないようにガードを入れる
        r_size = min(self.rect_size, h - 20, w - 20)
        x1 = (w - r_size) // 2
        y1 = (h - r_size) // 2
        x2 = x1 + r_size
        y2 = y1 + r_size

        roi = frame[y1:y2, x1:x2]
        
        # 2. 画像処理（AIが読めるように加工）
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # 枠が大きくなった分、膨張処理も少し強めにするか検討可能だが、一旦維持
        kernel = np.ones((3,3), np.uint8)
        thresh = cv2.dilate(thresh, kernel, iterations=1)

        # 3. AIの入力サイズ(28x28)にリサイズ
        small_img = cv2.resize(thresh, (28, 28), interpolation=cv2.INTER_AREA)
        
        # デバッグ表示用画像の作成
        self.debug_view_img = cv2.cvtColor(small_img, cv2.COLOR_GRAY2RGB)
        
        # 4. 0.0〜1.0に正規化
        input_data = small_img.reshape(1, -1) / 255.0

        # 5. AIによる予測
        if np.sum(input_data) > 5: # 何か書かれている場合
            probs = self.model.predict_proba(input_data)[0]
            self.current_prediction = str(np.argmax(probs))
            self.current_probability = np.max(probs) * 100
        else:
            self.current_prediction = "-"
            self.current_probability = 0.0

        return (x1, y1, x2, y2)

    def update_loop(self):
        """メインの更新処理ループ"""
        ret, frame = self.cap.read()
        if ret:
            # 鏡像反転（ユーザー体験向上）
            frame = cv2.flip(frame, 1)
            display_frame = frame.copy()
            
            # AI解析
            x1, y1, x2, y2 = self.process_digit(frame)
            
            # スキャンエリアの枠を描画（オレンジ）
            color = (0, 159, 255) # BGR: Orange
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
            # 角にアクセントの太い線
            d = 30
            cv2.line(display_frame, (x1, y1), (x1+d, y1), color, 6)
            cv2.line(display_frame, (x1, y1), (x1, y1+d), color, 6)
            cv2.line(display_frame, (x1+self.rect_size, y1), (x1+self.rect_size-d, y1), color, 6)
            cv2.line(display_frame, (x1+self.rect_size, y1), (x1+self.rect_size, y1+d), color, 6)
            cv2.line(display_frame, (x1, y1+self.rect_size), (x1+d, y1+self.rect_size), color, 6)
            cv2.line(display_frame, (x1, y1+self.rect_size), (x1, y1+self.rect_size-d), color, 6)
            cv2.line(display_frame, (x1+self.rect_size, y1+self.rect_size), (x1+self.rect_size-d, y1+self.rect_size), color, 6)
            cv2.line(display_frame, (x1+self.rect_size, y1+self.rect_size), (x1+self.rect_size, y1+self.rect_size-d), color, 6)

            # 左側UI更新
            self.result_label.config(text=self.current_prediction, 
                                    fg=self.SAFE_COLOR if self.current_probability > 80 else self.TEXT_COLOR)
            self.prob_text_label.config(text=f"確信度: {self.current_probability:.1f}%")
            self.prob_bar["value"] = self.current_probability

            # デバッグビュー（28x28）の更新
            debug_pil = Image.fromarray(self.debug_view_img).resize((200, 200), Image.NEAREST)
            self.tk_debug_img = ImageTk.PhotoImage(debug_pil)
            self.debug_canvas.itemconfig(self.debug_image_item, image=self.tk_debug_img)

            # メインCanvas表示
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 50 and ch > 50:
                rgb_img = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
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

if __name__ == "__main__":
    root = tk.Tk()
    # Windows高DPI対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = MnistCameraApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()