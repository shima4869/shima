# AIバーチャル・ペイント ✨
# インストール: pip install tkinter mediapipe opencv-python numpy pillow
# 実行方法: python virtual_paint.py
# Select Interpreter: Python 3.11.9

import cv2
import mediapipe as mp
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import time
import os
import sys

class VirtualPaintApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIバーチャル・ペイント ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数 (シリーズ統一デザイン)
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"

        # --- 既存システムの変数を継承 ---
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.8,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        self.canvas = None # 描画用ビットマップ
        self.draw_color = (0, 255, 0) # 最初は緑 (BGR)
        self.brush_thickness = 10
        self.prev_x, self.prev_y = 0, 0
        
        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.is_drawing_now = False

        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🎨 AIバーチャル・ペイント", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：左(操作)1, 右(表示)3
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 1. 描画色・ツール設定
        tool_frame = tk.LabelFrame(self.left_panel, text=" 🖌️ ツール設定 ", 
                                  font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                  fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        tool_frame.pack(fill=tk.X, pady=(0, 10))

        # 色選択ボタン
        colors = [
            ("Green", (0, 255, 0), "#2ECC71"),
            ("Red", (0, 0, 255), "#E74C3C"),
            ("Blue", (255, 0, 0), "#3498DB")
        ]
        for name, bgr, hex_code in colors:
            btn = tk.Button(tool_frame, text=name, command=lambda c=bgr: self.set_color(c),
                           bg=hex_code, fg="white", font=("Meiryo", 10, "bold"),
                           relief=tk.FLAT, cursor="hand2", pady=8)
            btn.pack(fill=tk.X, padx=15, pady=5)

        self.clear_btn = tk.Button(tool_frame, text="キャンバスクリア (C)", command=self.clear_canvas,
                                  bg="#BDC3C7", fg="white", font=("Meiryo", 10, "bold"),
                                  relief=tk.FLAT, cursor="hand2", pady=10)
        self.clear_btn.pack(fill=tk.X, padx=15, pady=15)

        # 2. ステータス
        status_frame = tk.LabelFrame(self.left_panel, text=" 👁️ 現在の状態 ", 
                                    font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, pady=10)
        
        self.lbl_status = tk.Label(status_frame, text="待機中", bg=self.BG_WHITE, 
                                  font=("Meiryo", 14, "bold"), fg=self.TEXT_COLOR, pady=15)
        self.lbl_status.pack()

        # 3. ログエリア
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 動作ログ ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.write_log("システムを起動しました。")

        # 使い方ガイド
        guide_text = "【操作ガイド】\n☝️ 人差し指を立てる ➡ 描画\n✌️ 中指も立てる ➡ 移動のみ\n✊ 手を握る ➡ 待機"
        tk.Label(self.left_panel, text=guide_text, bg="#FFFBEB", justify=tk.LEFT, 
                 font=("Meiryo", 9), fg="#95A5A6").pack(side=tk.BOTTOM, pady=20)

        # --- 右側：プレビューパネル ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ バーチャル・キャンバス ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas_widget = tk.Canvas(preview_frame, bg="black", highlightthickness=0)
        self.canvas_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.canvas_widget.create_image(0, 0, anchor=tk.NW)

        # ショートカットキー
        self.root.bind('<c>', lambda e: self.clear_canvas())
        self.root.bind('<r>', lambda e: self.set_color((0, 0, 255)))
        self.root.bind('<g>', lambda e: self.set_color((0, 255, 0)))
        self.root.bind('<b>', lambda e: self.set_color((255, 0, 0)))

    def write_log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def set_color(self, bgr):
        self.draw_color = bgr
        color_name = "Green" if bgr == (0, 255, 0) else "Red" if bgr == (0, 0, 255) else "Blue"
        self.write_log(f"色を {color_name} に変更しました。")

    def clear_canvas(self):
        if self.canvas is not None:
            self.canvas = np.zeros_like(self.canvas)
            self.write_log("キャンバスをクリアしました。")

    def process_logic(self, frame, results):
        """既存の描画ロジックと合成処理を統合"""
        h, w, _ = frame.shape
        if self.canvas is None:
            self.canvas = np.zeros((h, w, 3), np.uint8)

        self.is_drawing_now = False

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # 骨格描画
                self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                
                # 人差し指先端(8)の取得
                lm = hand_landmarks.landmark[8]
                cx, cy = int(lm.x * w), int(lm.y * h)

                # --- 判定ロジック (既存システムを継承) ---
                index_tip_y = hand_landmarks.landmark[8].y
                index_pip_y = hand_landmarks.landmark[6].y
                middle_tip_y = hand_landmarks.landmark[12].y
                middle_pip_y = hand_landmarks.landmark[10].y

                # 人差し指のみ立っているポーズ
                is_drawing_pose = (index_tip_y < index_pip_y) and (middle_tip_y > middle_pip_y)

                if is_drawing_pose:
                    self.is_drawing_now = True
                    cv2.circle(frame, (cx, cy), 15, self.draw_color, -1)
                    
                    if self.prev_x == 0 and self.prev_y == 0:
                        self.prev_x, self.prev_y = cx, cy
                    
                    # キャンバスへ線を引く
                    cv2.line(self.canvas, (self.prev_x, self.prev_y), (cx, cy), self.draw_color, self.brush_thickness)
                    self.prev_x, self.prev_y = cx, cy
                else:
                    self.prev_x, self.prev_y = 0, 0

        # --- 合成処理 (既存システムを継承) ---
        img_gray = cv2.cvtColor(self.canvas, cv2.COLOR_BGR2GRAY)
        _, img_inv = cv2.threshold(img_gray, 50, 255, cv2.THRESH_BINARY_INV)
        img_inv = cv2.cvtColor(img_inv, cv2.COLOR_GRAY2BGR)
        
        frame = cv2.bitwise_and(frame, img_inv)
        frame = cv2.bitwise_or(frame, self.canvas)
        
        return frame

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1) # 鏡表示
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)
            
            # 解析と合成
            processed_frame = self.process_logic(frame, results)

            # UIステータス更新
            if self.is_drawing_now:
                self.lbl_status.config(text="描画中... ✍️", fg=self.SAFE_COLOR)
            else:
                self.lbl_status.config(text="待機中", fg=self.TEXT_COLOR)

            # Tkinter表示
            self.root.update_idletasks()
            cw, ch = self.canvas_widget.winfo_width(), self.canvas_widget.winfo_height()
            if cw > 50 and ch > 50:
                frame_rgb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
                ratio = min(cw/w, ch/h)
                new_size = (int(w*ratio), int(h*ratio))
                pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
                
                self.tk_img = ImageTk.PhotoImage(pil_img)
                self.canvas_widget.itemconfig(self.image_item, image=self.tk_img)
                self.canvas_widget.coords(self.image_item, (cw-new_size[0])//2, (ch-new_size[1])//2)

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
    
    app = VirtualPaintApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()