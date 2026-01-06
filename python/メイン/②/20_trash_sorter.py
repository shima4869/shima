# AIゴミ自動分別システム ✨
# インストール: pip install ultralytics opencv-python numpy tkinter pillow
# 実行方法: python 20_trash_sorter.py
# Select Interpreter: Python 3.11.9

import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
from ultralytics import YOLO
import threading
import time
import os
import sys

class SortingEngine:
    """AIを用いてゴミの分別・仕分け命令を生成するエンジン"""
    def __init__(self):
        # AIモデルの読み込み (軽量なnモデル)
        try:
            self.model = YOLO('yolov8n.pt')
        except Exception as e:
            print(f"Model Load Error: {e}")
            sys.exit(1)
            
        # サーボモータの角度設定
        self.ANGLES = {
            "PET_BOTTLE": 45,  # ペットボトル用レーン
            "CAN": 90,         # カン用レーン
            "GLASS_BOTTLE": 135, # ビン用レーン
            "UNKNOWN": 0       # 待機状態
        }

    def analyze_frame(self, frame):
        """フレームを解析し、ゴミの種類とサーボ角度を決定する"""
        # YOLOで物体検出
        results = self.model(frame, verbose=False, conf=0.4)[0]
        
        category = "WAITING"
        command = "UNKNOWN"
        box_data = None
        
        for box in results.boxes:
            cls = int(box.cls[0])
            name = self.model.names[cls]
            
            # クラスID: 39=bottle, 41=cup (カンとして代用)
            if name == "bottle":
                # アスペクト比でペットボトルとビンを簡易推測
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                w, h = x2 - x1, y2 - y1
                aspect_ratio = h / w if w > 0 else 0
                
                if aspect_ratio > 2.5:
                    category = "PET BOTTLE"
                    command = "PET_BOTTLE"
                else:
                    category = "GLASS BOTTLE"
                    command = "GLASS_BOTTLE"
                
                box_data = (x1, y1, x2, y2)
                break 
                
            elif name == "cup" or name == "can":
                category = "CAN / TIN"
                command = "CAN"
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                box_data = (x1, y1, x2, y2)
                break

        angle = self.ANGLES.get(command, 0)
        return category, command, angle, box_data

class GarbageSorterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIゴミ自動分別システム ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数 (シリーズ統一)
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"
        self.ALERT_COLOR = "#E74C3C"

        self.engine = SortingEngine()
        
        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.is_sorting_active = False
        self.last_command = ""
        
        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="♻️ AIゴミ自動分別システム", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率：左1, 右3
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：コントロールパネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 自動分別スイッチ
        self.toggle_btn = tk.Button(self.left_panel, text="分別システム稼働 ▶", 
                                   command=self.toggle_sorting,
                                   bg=self.SAFE_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                   relief=tk.FLAT, cursor="hand2", pady=15)
        self.toggle_btn.pack(fill=tk.X, pady=(0, 15))

        # 現在の識別ステータス
        status_frame = tk.LabelFrame(self.left_panel, text=" 👁️ 現在の識別結果 ", 
                                    font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.lbl_category = tk.Label(status_frame, text="待機中", bg=self.BG_WHITE, 
                                    font=("Meiryo", 18, "bold"), fg=self.TEXT_COLOR, pady=15)
        self.lbl_category.pack()

        # サーボ制御情報
        servo_frame = tk.LabelFrame(self.left_panel, text=" ⚙️ サーボ出力 (制御信号) ", 
                                   font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        servo_frame.pack(fill=tk.X, pady=5)
        
        self.lbl_angle = tk.Label(servo_frame, text="角度: 0°", bg=self.BG_WHITE, 
                                 font=("Consolas", 14, "bold"), fg=self.ALERT_COLOR, pady=10)
        self.lbl_angle.pack()

        # 操作説明（ヒント）- デザイン統一のためLabelFrameに変更
        guide_frame = tk.LabelFrame(self.left_panel, text=" 💡 操作ガイド ", 
                                   font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        guide_frame.pack(fill=tk.X, pady=5)
        
        guide_text = "・ペットボトル: 45度\n・カン: 90度\n・ビン: 135度\nターンテーブル中央に対象を置いてください。"
        guide_label = tk.Label(guide_frame, text=guide_text, bg=self.BG_WHITE, justify=tk.LEFT, 
                               font=("Meiryo", 9), fg=self.TEXT_COLOR, padx=10, pady=10)
        guide_label.pack(fill=tk.X)

        # 通信ログ (expand=Trueで残りのスペースを埋める)
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 ハードウェア動作ログ ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Consolas", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)


        # --- 右側：カメラプレビュー ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ リアルタイム分別モニター (AIスキャン) ", 
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

    def toggle_sorting(self):
        self.is_sorting_active = not self.is_sorting_active
        if self.is_sorting_active:
            self.toggle_btn.config(text="システム停止 ⏹", bg=self.ALERT_COLOR)
            self.write_log("SYSTEM: 分別モード開始")
        else:
            self.toggle_btn.config(text="分別システム稼働 ▶", bg=self.SAFE_COLOR)
            self.write_log("SYSTEM: 停止中")
            self.lbl_category.config(text="待機中", fg=self.TEXT_COLOR)
            self.lbl_angle.config(text="角度: 0°")

    def send_hardware_signal(self, command, angle):
        """【拡張用】実際にArduinoやRaspberry Piへ信号を送る場所"""
        if command != self.last_command:
            msg = f"SEND -> CMD:{command} / SERVO:{angle}deg"
            self.write_log(msg)
            self.last_command = command

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            # AI解析
            category, command, angle, box = self.engine.analyze_frame(frame)
            display_frame = frame.copy()
            
            if self.is_sorting_active:
                # UI更新
                self.lbl_category.config(text=category, fg=self.PRIMARY_COLOR if category != "WAITING" else self.TEXT_COLOR)
                self.lbl_angle.config(text=f"角度: {angle}°")
                
                # 検出枠の描画
                if box:
                    x1, y1, x2, y2 = box
                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 159, 255), 3)
                    cv2.putText(display_frame, category, (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 159, 255), 2)
                
                # 命令送信
                if command != "UNKNOWN":
                    self.send_hardware_signal(command, angle)

            # Canvas表示
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
    
    app = GarbageSorterApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()