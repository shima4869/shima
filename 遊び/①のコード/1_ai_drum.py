# AIエアドラム・シミュレーター ✨
# インストール: pip install tkinter mediapipe pyaudio numpy opencv-python pillow pygame
# 実行方法: python ai_drum.py
# Select Interpreter: Python 3.11.9

import cv2
import mediapipe as mp
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import pygame
import os
import time
import sys

# --- 音を鳴らすためのクラス (既存システムを継承) ---
class SoundPlayer:
    def __init__(self):
        try:
            pygame.mixer.init()
        except:
            print("Audio device not found.")
            
        self.sounds = {}
        # 音声ファイルの設定
        self.load_sound("snare", "snare.wav")
        self.load_sound("kick", "kick.wav")
        self.load_sound("hihat", "hihat.wav")

    def load_sound(self, name, filepath):
        if os.path.exists(filepath):
            try:
                self.sounds[name] = pygame.mixer.Sound(filepath)
            except:
                self.sounds[name] = None
        else:
            self.sounds[name] = None

    def play(self, name):
        if self.sounds.get(name):
            self.sounds[name].play()
        else:
            # ファイルがない場合のフォールバック
            try:
                import winsound
                if name == "snare": winsound.Beep(1000, 50)
                elif name == "kick": winsound.Beep(200, 80)
                elif name == "hihat": winsound.Beep(4000, 30)
            except:
                pass

class AirDrumApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIエアドラム・シミュレーター ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数 (シリーズ統一デザイン)
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.HIT_COLOR = (255, 255, 255)   # ヒット時のフラッシュ（白）

        # エンジンとプレーヤーの初期化
        self.player = SoundPlayer()
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        
        # --- 楽器エリアの設定 (既存の座標・設定を継承) ---
        # 解像度 640x480 を基準にした座標系
        self.drums = [
            {"rect": [50, 200, 180, 330], "color": (255, 100, 100), "name": "snare", "active": False, "label": "SNARE"},
            {"rect": [250, 320, 390, 450], "color": (100, 255, 100), "name": "kick", "active": False, "label": "BASS DRUM"},
            {"rect": [460, 150, 590, 280], "color": (100, 200, 255), "name": "hihat", "active": False, "label": "HI-HAT"}
        ]

        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        
        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🥁 AIエアドラム・シミュレーター", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：左(情報)1, 右(演奏画面)4
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=4)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：ステータス・ログパネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=350)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 1. 遊びかた
        guide_frame = tk.LabelFrame(self.left_panel, text=" 💡 遊びかた ", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        guide_frame.pack(fill=tk.X, pady=(0, 10))
        
        guide_text = "・カメラに手を映してください。\n・空中にあるドラムの枠を\n　人差し指で叩いてください。\n・叩いた瞬間、枠が白く光ります！"
        tk.Label(guide_frame, text=guide_text, bg=self.BG_WHITE, justify=tk.LEFT, 
                 font=("Meiryo", 10), padx=15, pady=15).pack(anchor="nw")

        # 2. ヒットログ
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 演奏ログ ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.write_log("システムを起動しました。演奏を開始してください！")

        # 終了ボタン
        self.exit_btn = tk.Button(self.left_panel, text="プログラムを終了 (Q)", 
                                 command=self.on_closing,
                                 bg="#BDC3C7", fg="white", font=("Meiryo", 10, "bold"),
                                 relief=tk.FLAT, cursor="hand2", pady=10)
        self.exit_btn.pack(fill=tk.X, side=tk.BOTTOM, pady=10)

        # --- 右側：演奏プレビュー ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ エアドラム・メインステージ ", 
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

    def process_drum_logic(self, frame, results):
        """ドラムの衝突判定と描画 (既存の核となるロジック)"""
        h, w, _ = frame.shape
        # 判定用座標（640x480ベースのドラム設定に合わせるための倍率）
        # ただし今回は640x480を前提とするか、正規化座標で計算
        
        # 毎フレームのフラグ初期化
        for drum in self.drums:
            drum["touched_now"] = False

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # 指先（人差し指:8 と 中指:12）の取得
                for finger_id in [8, 12]:
                    lm = hand_landmarks.landmark[finger_id]
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    
                    # 指先の可視化
                    cv2.circle(frame, (cx, cy), 8, (255, 255, 255), -1)
                    cv2.circle(frame, (cx, cy), 10, self.HUD_COLOR_BGR(), 2)

                    # エリア判定
                    for drum in self.drums:
                        x1, y1, x2, y2 = drum["rect"]
                        # 描画座標を実際のフレーム解像度(w, h)に合わせてスケーリング
                        # (ここでは簡易的に 640x480 ベースの座標をそのまま適用)
                        if x1 < cx < x2 and y1 < cy < y2:
                            drum["touched_now"] = True

        # 音を鳴らすロジックと描画
        for drum in self.drums:
            x1, y1, x2, y2 = drum["rect"]
            color_bgr = drum["color"][::-1] # RGB -> BGR
            
            if drum["touched_now"] and not drum["active"]:
                self.player.play(drum["name"])
                drum["active"] = True
                self.write_log(f"HIT: {drum['label']} !")
                # 視覚効果：叩いた瞬間、四角形を白く光らせる
                cv2.rectangle(frame, (x1, y1), (x2, y2), self.HIT_COLOR, -1)
            elif not drum["touched_now"]:
                drum["active"] = False

            # 通常時の枠線描画
            if not (drum["touched_now"] and drum["active"]):
                cv2.rectangle(frame, (x1, y1), (x2, y2), color_bgr, 3)
                # ラベル背景
                cv2.rectangle(frame, (x1, y1-30), (x1+120, y1), color_bgr, -1)
                cv2.putText(frame, drum["label"], (x1+5, y1-8), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return frame

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1) # 鏡表示
            # 640x480にリサイズ（ドラム座標の基準に合わせる）
            frame = cv2.resize(frame, (640, 480))
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)
            
            # ドラムロジック適用
            processed_frame = self.process_drum_logic(frame, results)

            # Tkinter Canvas表示
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 50 and ch > 50:
                rgb_img = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_img)
                
                # アスペクト比維持で最大化
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
        return (67, 159, 255) # オレンジ

    def on_closing(self):
        self.is_running = False
        self.cap.release()
        try:
            pygame.mixer.quit()
        except:
            pass
        self.root.destroy()
        sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    # Windows高DPI対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = AirDrumApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    # キーボードのQでも終了できるように
    root.bind('<q>', lambda e: app.on_closing())
    root.mainloop()