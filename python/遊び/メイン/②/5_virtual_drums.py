# バーチャル・エアドラム AI
# インストール: pip install opencv-python Pillow pygame
# 実行方法: python 5_virtual_drums.py
# Select Interpreter: Python 3.11.9

import cv2
import numpy as np
import pygame
import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
from PIL import Image, ImageDraw, ImageFont, ImageTk
import threading
import time
import os

# Windowsでのビープ音用フォールバック
try:
    import winsound
except ImportError:
    winsound = None

class VirtualDrumsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("バーチャル・エアドラム ✨")
        self.root.geometry("1500x900") # より広い画面サイズに調整
        self.root.configure(bg="#FFFBEB")

        # カラー設定
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"

        # ドラム設定 [x1, y1, x2, y2, 名前, 表示色]
        # 解像度 640x480 を前提とした配置（描画時にスケーリングされます）
        self.DRUMS = [
            {"rect": [50, 250, 220, 420], "color": (255, 100, 100), "name": "Snare", "id": "snare"},
            {"rect": [250, 300, 420, 470], "color": (100, 255, 100), "name": "Bass", "id": "kick"},
            {"rect": [450, 200, 600, 370], "color": (100, 200, 255), "name": "Hi-Hat", "id": "hihat"}
        ]

        # 追跡する色（青色のHSV範囲）
        self.LOWER_BLUE = np.array([100, 150, 100])
        self.UPPER_BLUE = np.array([140, 255, 255])

        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.prev_y = 0
        self.is_hitting = False
        self.hit_log = [] # 叩いた履歴
        self.flash_timer = {d["name"]: 0 for d in self.DRUMS}

        # サウンド初期化
        try:
            pygame.mixer.init()
            self.load_sounds()
        except:
            print("オーディオデバイスの初期化に失敗しました。")

        self.setup_ui()
        
        # UI更新ループ
        self.update_loop()

    def load_sounds(self):
        """ドラム音の読み込み（ファイルがない場合はスキップ）"""
        self.sounds = {}
        for d in self.DRUMS:
            path = f"{d['id']}.wav"
            if os.path.exists(path):
                self.sounds[d['name']] = pygame.mixer.Sound(path)

    def play_drum(self, name):
        """音を鳴らし、履歴を更新する"""
        if name in self.sounds:
            self.sounds[name].play()
        elif winsound:
            # 音源ファイルがない場合のフォールバック
            if name == "Snare": winsound.Beep(800, 50)
            elif name == "Bass": winsound.Beep(200, 80)
            elif name == "Hi-Hat": winsound.Beep(1500, 30)
        
        # ログに追加
        log_entry = f"[{time.strftime('%H:%M:%S')}] {name} をヒット！\n"
        self.update_log_display(log_entry)
        
        # フラッシュエフェクト開始
        self.flash_timer[name] = 5 

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🥁 バーチャル・エアドラム", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：左(操作)1, 右(表示)6 にしてカメラを大きく
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=6)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル (幅をスリムに) ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=300)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # ガイド
        info_frame = tk.LabelFrame(self.left_panel, text=" 💡 遊びかた ", 
                                   font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        guide_text = (
            "1. 青色のペンや物体を持つ\n"
            "2. 枠を勢いよく叩く！\n"
            "3. 速度に反応して鳴るよ"
        )
        tk.Label(info_frame, text=guide_text, bg=self.BG_WHITE, justify=tk.LEFT, 
                 font=("Meiryo", 9), padx=15, pady=10).pack(anchor="w")

        # 叩いた履歴（スクロール可能に変更）
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 ヒット履歴 ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- 右側：プレビューパネル (ここを最大化) ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ エアドラム・ステージ ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def update_log_display(self, entry):
        """履歴エリアに新しい行を追加し、最新行までスクロールする"""
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, entry)
        self.log_area.see(tk.END) # 最新の履歴まで自動スクロール
        self.log_area.config(state=tk.DISABLED)

    def process_frame(self, frame):
        """ドラムヒット判定と描画処理"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.LOWER_BLUE, self.UPPER_BLUE)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) > 0:
            c = max(contours, key=cv2.contourArea)
            ((x, y), radius) = cv2.minEnclosingCircle(c)
            
            if radius > 15:
                curr_x, curr_y = int(x), int(y)
                cv2.circle(frame, (curr_x, curr_y), int(radius), (255, 255, 0), 2)
                cv2.circle(frame, (curr_x, curr_y), 5, (0, 0, 255), -1)
                
                speed = curr_y - self.prev_y
                if speed > 20 and not self.is_hitting:
                    for drum in self.DRUMS:
                        x1, y1, x2, y2 = drum["rect"]
                        if x1 < curr_x < x2 and y1 < curr_y < y2:
                            self.play_drum(drum["name"])
                            self.is_hitting = True
                elif speed < 5:
                    self.is_hitting = False
                
                self.prev_y = curr_y

        for drum in self.DRUMS:
            x1, y1, x2, y2 = drum["rect"]
            color = drum["color"]
            
            if self.flash_timer[drum["name"]] > 0:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), -1)
                self.flash_timer[drum["name"]] -= 1
            else:
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                cv2.rectangle(frame, (x1, y1-35), (x1+100, y1), color, -1)
                cv2.putText(frame, drum["name"], (x1 + 5, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return frame

    def update_loop(self):
        """カメラ映像の取得と表示更新のループ"""
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            frame = self.process_frame(frame)
            
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 50 and ch > 50:
                rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_img)
                
                fw, fh = pil_img.size
                ratio = min(cw/fw, ch/fh)
                new_size = (int(fw*ratio), int(fh*ratio))
                pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
                
                self.tk_img = ImageTk.PhotoImage(pil_img)
                self.canvas.itemconfig(self.image_item, image=self.tk_img)
                self.canvas.coords(self.image_item, (cw-new_size[0])//2, (ch-new_size[1])//2)

        if self.is_running:
            self.root.after(20, self.update_loop)

    def on_closing(self):
        self.is_running = False
        self.cap.release()
        try:
            pygame.mixer.quit()
        except:
            pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = VirtualDrumsApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()