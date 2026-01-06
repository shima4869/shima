# AI自動追尾カーシステム ✨
# インストール: pip install opencv-python numpy tkinter pillow
# 実行方法: python 19_auto_tracking_car.py
# Select Interpreter: Python 3.11.9

import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import threading
import time
import os
import sys

class TrackingEngine:
    """物体の色と位置を解析して移動命令を生成するエンジン"""
    def __init__(self):
        # 追尾対象の色設定（赤色）
        self.lower_red1 = np.array([0, 120, 70])
        self.upper_red1 = np.array([10, 255, 255])
        self.lower_red2 = np.array([170, 120, 70])
        self.upper_red2 = np.array([180, 255, 255])
        
        # 制御用の定数
        self.deadzone_x = 0.15 # 左右の遊び（15%以内なら正面とみなす）
        self.target_area_ratio = 0.1 # 目標とする物体の面積比（10%）
        self.area_tolerance = 0.03   # 面積の許容誤差

    def process_frame(self, frame):
        """画像を解析し、中心座標、面積比、命令を返す"""
        h, w, _ = frame.shape
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 赤色のマスク作成
        mask1 = cv2.inRange(hsv, self.lower_red1, self.upper_red1)
        mask2 = cv2.inRange(hsv, self.lower_red2, self.upper_red2)
        mask = cv2.bitwise_or(mask1, mask2)
        
        # ノイズ除去
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        
        # 輪郭抽出
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        center = None
        area_ratio = 0
        command = "STOP"
        
        if contours:
            # 最大の物体を選択
            c = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(c)
            total_area = h * w
            area_ratio = area / total_area
            
            if area > 500: # 小さすぎるノイズは無視
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    center = (cx, cy)
                    
                    # --- 追尾ロジックの生成 ---
                    norm_x = (cx / w) - 0.5 # -0.5(左) ～ 0.5(右)
                    
                    if norm_x < -self.deadzone_x:
                        turn = "LEFT"
                    elif norm_x > self.deadzone_x:
                        turn = "RIGHT"
                    else:
                        turn = "STRAIGHT"
                        
                    if area_ratio < (self.target_area_ratio - self.area_tolerance):
                        move = "FORWARD"
                    elif area_ratio > (self.target_area_ratio + self.area_tolerance):
                        move = "BACKWARD"
                    else:
                        move = "STAY"
                        
                    if move == "STAY" and turn == "STRAIGHT":
                        command = "IDLE (TARGET LOCKED)"
                    else:
                        command = f"{move}_{turn}"

        return center, area_ratio, command, mask

class AutoTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI自動追尾システム ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"        # 緑
        self.ALERT_COLOR = "#E74C3C"       # 赤

        # エンジン初期化
        self.engine = TrackingEngine()
        
        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.is_auto_pilot = False
        self.last_command = ""
        
        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🏎️ AI自動追尾・撮影システム", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：左1, 右3
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作・命令パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 自動運転スイッチ
        self.pilot_btn = tk.Button(self.left_panel, text="自動追尾モード開始 ▶", 
                                  command=self.toggle_pilot,
                                  bg=self.SAFE_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                  relief=tk.FLAT, cursor="hand2", pady=15)
        self.pilot_btn.pack(fill=tk.X, pady=(0, 10))

        # 現在の命令表示
        cmd_frame = tk.LabelFrame(self.left_panel, text=" 🕹️ モーター制御信号 ", 
                                 font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        cmd_frame.pack(fill=tk.X, pady=5)

        self.lbl_command = tk.Label(cmd_frame, text="WAITING", bg=self.BG_WHITE, 
                                   font=("Impact", 24), fg=self.TEXT_COLOR, pady=20)
        self.lbl_command.pack()

        # ターゲット情報
        info_frame = tk.LabelFrame(self.left_panel, text=" 👁️ ターゲット解析データ ", 
                                  font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                  fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        info_frame.pack(fill=tk.X, pady=5)
        
        self.lbl_area = tk.Label(info_frame, text="距離(面積比): 0.0%", bg=self.BG_WHITE, font=("Meiryo", 10))
        self.lbl_area.pack(anchor="w", padx=15, pady=5)
        
        self.lbl_pos = tk.Label(info_frame, text="中心座標: ---", bg=self.BG_WHITE, font=("Meiryo", 10))
        self.lbl_pos.pack(anchor="w", padx=15, pady=5)

        # 操作ガイドパネル (修正箇所: LabelからLabelFrameへ変更し配置を固定)
        guide_frame = tk.LabelFrame(self.left_panel, text=" 💡 操作ガイド ", 
                                   font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        guide_frame.pack(fill=tk.X, pady=5)
        
        guide_text = "・赤い色の物体を認識して追いかけます。\n・実機に繋ぐ際は send_command 関数に\n  GPIO操作を記述してください。"
        guide_label = tk.Label(guide_frame, text=guide_text, bg=self.BG_WHITE, justify=tk.LEFT, 
                               font=("Meiryo", 9), fg=self.TEXT_COLOR, padx=10, pady=10)
        guide_label.pack(fill=tk.X)

        # 送信ログ (expand=Trueで残りのスペースを埋める)
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 ハードウェア通信ログ ", 
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

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ 追尾ビジュアルモニター ", 
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

    def toggle_pilot(self):
        self.is_auto_pilot = not self.is_auto_pilot
        if self.is_auto_pilot:
            self.pilot_btn.config(text="自動追尾モード停止 ⏹", bg=self.ALERT_COLOR)
            self.write_log("AUTOPILOT: 稼働中")
        else:
            self.pilot_btn.config(text="自動追尾モード開始 ▶", bg=self.SAFE_COLOR)
            self.write_log("AUTOPILOT: 停止")
            self.lbl_command.config(text="STOP", fg=self.TEXT_COLOR)

    def send_command(self, cmd):
        """【拡張用】実際にハードウェアへ命令を飛ばす場所"""
        if cmd != self.last_command:
            self.write_log(f"CMD SEND: {cmd}")
            self.last_command = cmd

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1) # 鏡表示
            h, w, _ = frame.shape
            
            # AI解析
            center, area_ratio, command, mask = self.engine.process_frame(frame)
            display_frame = frame.copy()
            
            if center:
                color = (0, 159, 255) # オレンジ
                cv2.drawMarker(display_frame, center, color, cv2.MARKER_CROSS, 40, 2)
                cv2.circle(display_frame, center, 50, color, 2)
                
                self.lbl_area.config(text=f"距離(面積比): {area_ratio*100:.1f}%")
                self.lbl_pos.config(text=f"中心座標: X:{center[0]}, Y:{center[1]}")
                
                if self.is_auto_pilot:
                    self.lbl_command.config(text=command, fg=self.PRIMARY_COLOR)
                    self.send_command(command)
            else:
                self.lbl_area.config(text="ターゲット未検出")
                if self.is_auto_pilot:
                    self.lbl_command.config(text="SEARCHING...", fg=self.ALERT_COLOR)

            dw = int(w * self.engine.deadzone_x)
            cv2.line(display_frame, (w//2 - dw, 0), (w//2 - dw, h), (255, 255, 255), 1)
            cv2.line(display_frame, (w//2 + dw, 0), (w//2 + dw, h), (255, 255, 255), 1)

            # Canvas表示
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
    
    app = AutoTrackerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()