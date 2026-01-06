# AIプレゼンター・コントローラー ✨
# インストール: pip install tkinter mediapipe opencv-python numpy pillow
# 実行方法: python ai_presenter.py
# Select Interpreter: Python 3.11.9

import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import time
import os
import sys

class PresenterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIプレゼンター・コントローラー ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数 (シリーズ統一デザイン)
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"        # チャージ完了（緑）

        # --- 既存システムの変数を継承 ---
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            min_detection_confidence=0.8, 
            max_num_hands=1
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # ボタン設定 (640x480 基準の座標)
        self.width_ref, self.height_ref = 640, 480
        self.btn_next = [self.width_ref - 150, 50, self.width_ref - 30, 150]
        self.btn_prev = [30, 50, 150, 150]
        
        # チャージ・クールダウン管理
        self.charge_needed = 15 
        self.charge_counter_next = 0
        self.charge_counter_prev = 0
        self.cooldown = 0
        
        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        
        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="👨‍🏫 AIプレゼンター・コントローラー", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率：左(情報)1, 右(操作画面)3
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：ステータス・ログパネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 1. 状態パネル
        status_frame = tk.LabelFrame(self.left_panel, text=" 👁️ システム状態 ", 
                                    font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        self.lbl_status = tk.Label(status_frame, text="カメラ稼働中", bg=self.BG_WHITE, 
                                  font=("Meiryo", 12, "bold"), fg=self.PRIMARY_COLOR, pady=15)
        self.lbl_status.pack()

        # 2. コマンドログ
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 操作ログ ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.write_log("システムを起動しました。")

        # 遊び方ガイド
        guide_text = "【操作方法】\n・画面上の青い枠に手をかざしてね。\n・緑色に塗りつぶされるまで\n　そのまま待つとスライドが動きます。\n・「NEXT」で次へ、「PREV」で前へ。"
        tk.Label(self.left_panel, text=guide_text, bg="#FFFBEB", justify=tk.LEFT, 
                 font=("Meiryo", 9), fg="#95A5A6").pack(side=tk.BOTTOM, pady=20)

        # --- 右側：カメラプレビュー ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ プレゼンター・モニター (HUDオーバーレイ) ", 
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

    def process_logic(self, frame, results):
        """既存のチャージ・クールダウン・操作ロジックを統合"""
        h, w, _ = frame.shape
        # 内部処理用に 640x480 基準の座標で計算
        
        if self.cooldown > 0:
            self.cooldown -= 1

        # ボタン描画 (通常時)
        # Next (青)
        cv2.rectangle(frame, (self.btn_next[0], self.btn_next[1]), (self.btn_next[2], self.btn_next[3]), (255, 100, 0), 2)
        cv2.putText(frame, "NEXT >", (self.btn_next[0]+20, self.btn_next[1]+60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 100, 0), 2)
        
        # Prev (青)
        cv2.rectangle(frame, (self.btn_prev[0], self.btn_prev[1]), (self.btn_prev[2], self.btn_prev[3]), (255, 100, 0), 2)
        cv2.putText(frame, "< PREV", (self.btn_prev[0]+20, self.btn_prev[1]+60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 100, 0), 2)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                
                # 指先(8)の座標取得
                lm = hand_landmarks.landmark[8]
                cx, cy = int(lm.x * self.width_ref), int(lm.y * self.height_ref)
                
                # 指先の可視化 (オレンジ)
                cv2.circle(frame, (cx, cy), 12, (0, 159, 255), -1)

                if self.cooldown == 0:
                    # NEXT判定
                    if self.btn_next[0] < cx < self.btn_next[2] and self.btn_next[1] < cy < self.btn_next[3]:
                        self.charge_counter_next += 1
                        fill_h = int((self.charge_counter_next / self.charge_needed) * (self.btn_next[3] - self.btn_next[1]))
                        cv2.rectangle(frame, (self.btn_next[0], self.btn_next[3] - fill_h), (self.btn_next[2], self.btn_next[3]), (46, 204, 113), -1)
                        
                        if self.charge_counter_next >= self.charge_needed:
                            pyautogui.press('right')
                            self.write_log("COMMAND: 次のスライドへ (RIGHT)")
                            self.cooldown = 40
                            self.charge_counter_next = 0
                    else:
                        self.charge_counter_next = 0

                    # PREV判定
                    if self.btn_prev[0] < cx < self.btn_prev[2] and self.btn_prev[1] < cy < self.btn_prev[3]:
                        self.charge_counter_prev += 1
                        fill_h = int((self.charge_counter_prev / self.charge_needed) * (self.btn_prev[3] - self.btn_prev[1]))
                        cv2.rectangle(frame, (self.btn_prev[0], self.btn_prev[3] - fill_h), (self.btn_prev[2], self.btn_prev[3]), (46, 204, 113), -1)
                        
                        if self.charge_counter_prev >= self.charge_needed:
                            pyautogui.press('left')
                            self.write_log("COMMAND: 前のスライドへ (LEFT)")
                            self.cooldown = 40
                            self.charge_counter_prev = 0
                    else:
                        self.charge_counter_prev = 0
        
        return frame

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1) # 鏡表示
            # 処理用に 640x480 にリサイズ（座標基準を合わせるため）
            frame = cv2.resize(frame, (self.width_ref, self.height_ref))
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)
            
            # コントロールロジック適用
            processed_frame = self.process_logic(frame, results)

            # Tkinter Canvas表示
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 50 and ch > 50:
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
        sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    # Windows高DPI対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = PresenterApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()