# AIジェスチャー・スマートホーム ✨
# インストール: pip install opencv-python mediapipe numpy tkinter pillow
# 実行方法: python 18_smart_home_gesture.py
# Select Interpreter: Python 3.11.9

import cv2
import mediapipe as mp
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk
import threading
import time
import os
import math

class GestureHomeEngine:
    """MediaPipeを使用して手の動きを解析し、家電操作へ変換するエンジン"""
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        
        # 家電の状態管理
        self.light_on = False
        self.ac_temp = 24
        self.last_snap_time = 0
        self.is_snapping = False
        self.base_angle = None
        self.current_angle = 0
        
    def get_distance(self, p1, p2):
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

    def analyze(self, frame):
        """フレームから手を検出し、操作を判定する"""
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        
        gesture_msg = ""
        action_triggered = None # (type, value)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                landmarks = hand_landmarks.landmark
                
                # --- 1. 指パッチン判定 (親指と中指の距離) ---
                thumb_tip = landmarks[4]
                middle_tip = landmarks[12]
                dist_snap = self.get_distance(thumb_tip, middle_tip)
                
                # 距離が非常に近い(くっついている)状態から離れた瞬間を検知
                if dist_snap < 0.05:
                    self.is_snapping = True
                elif self.is_snapping and dist_snap > 0.12:
                    now = time.time()
                    if now - self.last_snap_time > 0.5: # 連続誤爆防止
                        self.light_on = not self.light_on
                        action_triggered = ("LIGHT", self.light_on)
                        self.last_snap_time = now
                    self.is_snapping = False

                # --- 2. 手の回転判定 (手首から中指の付け根の角度) ---
                wrist = landmarks[0]
                middle_mcp = landmarks[9]
                
                # ラジアンから度数に変換
                angle = math.degrees(math.atan2(wrist.y - middle_mcp.y, wrist.x - middle_mcp.x))
                
                if self.base_angle is None:
                    self.base_angle = angle
                
                # 回転量の計算
                diff_angle = angle - self.base_angle
                if abs(diff_angle) > 15: # 15度以上の回転で反応
                    if diff_angle > 0: self.ac_temp = min(30, self.ac_temp + 1)
                    else: self.ac_temp = max(16, self.ac_temp - 1)
                    action_triggered = ("AC", self.ac_temp)
                    self.base_angle = angle # 基準を更新
                
                self.current_angle = diff_angle
                gesture_msg = "HAND DETECTED"

        return results, gesture_msg, action_triggered

class SmartHomeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIジェスチャー・スマートホーム ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数 (シリーズ統一)
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"

        self.engine = GestureHomeEngine()
        
        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        
        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🏠 AIジェスチャー・スマートホーム", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：左1, 右3
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：家電ステータスパネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 照明ステータス
        light_frame = tk.LabelFrame(self.left_panel, text=" 💡 照明の状態 ", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        light_frame.pack(fill=tk.X, pady=5)

        self.lbl_light = tk.Label(light_frame, text="OFF", bg=self.BG_WHITE, 
                                 font=("Impact", 32), fg="#BDC3C7")
        self.lbl_light.pack(pady=10)

        # エアコンステータス
        ac_frame = tk.LabelFrame(self.left_panel, text=" ❄️ エアコン設定 ", 
                                font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        ac_frame.pack(fill=tk.X, pady=5)

        self.lbl_ac = tk.Label(ac_frame, text="24°C", bg=self.BG_WHITE, 
                              font=("Impact", 32), fg=self.TEXT_COLOR)
        self.lbl_ac.pack(pady=10)

        # 操作説明 (修正箇所: LabelからLabelFrameへ変更し配置を固定)
        guide_frame = tk.LabelFrame(self.left_panel, text=" 💡 操作ガイド ", 
                                   font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        guide_frame.pack(fill=tk.X, pady=5)
        
        guide_text = "・指パッチン ➡ 照明ON/OFF\n・手を左右に傾ける ➡ 温度調節\n※カメラに手をハッキリ映してね！"
        guide_label = tk.Label(guide_frame, text=guide_text, bg=self.BG_WHITE, justify=tk.LEFT, 
                               font=("Meiryo", 9), fg=self.TEXT_COLOR, padx=10, pady=10)
        guide_label.pack(fill=tk.X)

        # 動作ログ (expand=Trueで残りのスペースを埋める)
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 コマンド送信ログ ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.write_log("システムを起動しました。")

        # --- 右側：カメラプレビュー ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ ジェスチャー認識モニター ", 
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

    def send_ir_signal(self, device, value):
        """【拡張用】Nature Remo等のAPIを叩くコードをここに記述"""
        msg = f"SEND IR: {device} -> {value}"
        self.write_log(msg)

    def update_ui_status(self, action):
        """家電の状態変化をUIに反映"""
        type, val = action
        if type == "LIGHT":
            status = "ON" if val else "OFF"
            color = self.SECONDARY_COLOR if val else "#BDC3C7"
            self.lbl_light.config(text=status, fg=color)
            self.send_ir_signal("LIGHT", status)
        elif type == "AC":
            self.lbl_ac.config(text=f"{val}°C")
            self.send_ir_signal("AIR_CON", f"{val}deg")

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1) # 鏡表示
            h, w, _ = frame.shape
            
            # AI解析
            results, msg, action = self.engine.analyze(frame)
            
            if action:
                self.update_ui_status(action)

            # 描画処理 (HUDオーバーレイ)
            display_frame = frame.copy()
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp.solutions.drawing_utils.draw_landmarks(
                        display_frame, hand_landmarks, mp.solutions.hands.HAND_CONNECTIONS)
            
            # 画面上部に操作ガイドをオーバーレイ
            cv2.rectangle(display_frame, (0, 0), (w, 60), (0,0,0), -1)
            cv2.putText(display_frame, f"STATUS: {msg if msg else 'WAITING...'}", 
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, self.HUD_COLOR_BGR(), 2)

            # Tkinter表示
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

    def HUD_COLOR_BGR(self):
        # オレンジをBGR形式で返す
        return (67, 159, 255)

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
    
    app = SmartHomeApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()