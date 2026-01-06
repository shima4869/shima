# 食事カロリー計算カメラ AI
# インストール: pip install ultralytics opencv-python pillow numpy
# 実行方法: python 7_calorie_camera.py
# Select Interpreter: Python 3.11.9

import cv2
from ultralytics import YOLO
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk
import platform
import os
import sys
import time
import threading

class CalorieCameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("食事カロリー計算カメラ AI ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"        # 緑

        # --- 既存システムの継承設定 ---
        self.food_database = {
            47: {"name": "リンゴ", "cal": 52},    # apple
            46: {"name": "バナナ", "cal": 89},    # banana
            49: {"name": "オレンジ", "cal": 47},  # orange
            50: {"name": "ブロッコリー", "cal": 34}, # broccoli
            51: {"name": "ニンジン", "cal": 41},  # carrot
            52: {"name": "ホットドッグ", "cal": 290}, # hot dog
            53: {"name": "ピザ(1切)", "cal": 266},   # pizza
            54: {"name": "ドーナツ", "cal": 250},   # donut
            55: {"name": "ケーキ", "cal": 350},     # cake
            48: {"name": "サンドイッチ", "cal": 250}, # sandwich
        }

        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.frame_count = 0
        self.skip_frames = 5
        self.detected_foods = []
        self.total_calories = 0

        # AIモデル読み込み
        try:
            self.model = YOLO('yolov8n.pt')
        except Exception as e:
            messagebox.showerror("エラー", f"AIモデルの読み込みに失敗しました: {e}")
            sys.exit(1)

        self.font_path = self._get_system_font()
        self.setup_ui()
        
        # メインループ開始
        self.update_loop()

    def _get_system_font(self):
        """OSごとの日本語フォントパスを取得"""
        system = platform.system()
        if system == "Windows":
            return "C:/Windows/Fonts/meiryo.ttc"
        elif system == "Darwin": # macOS
            return "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
        return None

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🥗 食事カロリー計算カメラ", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：左1, 右4
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=4)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：情報パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 合計表示
        total_frame = tk.LabelFrame(self.left_panel, text=" 👁️ 今日の食事合計 ", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        total_frame.pack(fill=tk.X, pady=(0, 10))

        self.total_label = tk.Label(total_frame, text="0 kcal", bg=self.BG_WHITE, 
                                   font=("Meiryo", 22, "bold"), fg=self.SAFE_COLOR, pady=20)
        self.total_label.pack()

        # 検出食品リスト
        list_frame = tk.LabelFrame(self.left_panel, text=" 📝 検出された食品 ", 
                                  font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                  fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.food_list_area = scrolledtext.ScrolledText(list_frame, font=("Meiryo", 10), 
                                                       bg=self.BG_WHITE, relief=tk.FLAT,
                                                       fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.food_list_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ガイド
        hint_label = tk.Label(self.left_panel, text="対応食品:\nリンゴ、バナナ、ピザ、\nドーナツ、サンドイッチなど", 
                             bg="#FFFBEB", fg="#95A5A6", font=("Meiryo", 9), justify=tk.LEFT)
        hint_label.pack(side=tk.BOTTOM, pady=10)

        # --- 右側：映像プレビュー ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ リアルタイム解析画面 ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def update_food_list(self):
        """左側のリストと合計値を更新"""
        self.food_list_area.config(state=tk.NORMAL)
        self.food_list_area.delete("1.0", tk.END)
        
        current_total = 0
        if not self.detected_foods:
            self.food_list_area.insert(tk.END, "食品を映してください...")
        else:
            for food in self.detected_foods:
                name, cal = food[4], food[5]
                self.food_list_area.insert(tk.END, f"・{name}: {cal} kcal\n")
                current_total += cal
        
        self.total_label.config(text=f"{current_total} kcal")
        self.food_list_area.config(state=tk.DISABLED)

    def update_loop(self):
        """メインの更新処理ループ"""
        ret, frame = self.cap.read()
        if ret:
            display_frame = frame.copy()
            self.frame_count += 1
            
            # 解析処理 (5フレームに1回)
            if self.frame_count % self.skip_frames == 0:
                try:
                    results = self.model(frame, stream=True, verbose=False, conf=0.5)
                    new_detected_foods = []
                    for result in results:
                        for box in result.boxes:
                            cls_id = int(box.cls[0])
                            if cls_id in self.food_database:
                                food_info = self.food_database[cls_id]
                                x1, y1, x2, y2 = map(int, box.xyxy[0])
                                conf = float(box.conf[0])
                                new_detected_foods.append((x1, y1, x2, y2, food_info["name"], food_info["cal"], conf))
                    
                    self.detected_foods = new_detected_foods
                    self.update_food_list()
                except Exception as e:
                    print(f"Inference Error: {e}")

            # 描画処理 (検出枠)
            for (x1, y1, x2, y2, name, cal, conf) in self.detected_foods:
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (46, 204, 113), 3) # 緑の枠
                label = f"{name} ({cal}kcal)"
                cv2.putText(display_frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (46, 204, 113), 2)

            # Canvasへ表示
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 50 and ch > 50:
                # BGR -> RGB 変換
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
    
    app = CalorieCameraApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()