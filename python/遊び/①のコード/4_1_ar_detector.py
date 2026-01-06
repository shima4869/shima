# ARマーカー検知システム ✨
# インストール: pip install tkinter opencv-python numpy pillow
# 実行方法: python ar_detector.py
# Select Interpreter: Python 3.11.9

import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import time
import os
import sys

class ArUcoEngine:
    """OpenCVのArUcoモジュールを使用してマーカーを検知するエンジン"""
    def __init__(self):
        # マーカー辞書の準備
        self.dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.parameters = cv2.aruco.DetectorParameters()
        
        # 新旧APIの互換性チェック
        try:
            self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.parameters)
            self.use_new_api = True
        except AttributeError:
            self.use_new_api = False

    def detect(self, frame):
        """フレームからマーカーを検出し、IDと座標を返す"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self.use_new_api:
            corners, ids, rejected = self.detector.detectMarkers(gray)
        else:
            corners, ids, rejected = cv2.aruco.detectMarkers(gray, self.dictionary, parameters=self.parameters)
        return corners, ids

class ARDetectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI ARマーカー検知システム ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数 (シリーズ統一デザイン)
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"
        self.ALERT_COLOR = "#E74C3C"

        # エンジンの初期化
        self.engine = ArUcoEngine()
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        
        # 統計データ
        self.detected_ids = set()
        self.last_log_time = {}

        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="📐 AI ARマーカー検知システム", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：左(情報)1, 右(映像)3
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：ステータス・ログパネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 1. 検知ステータス
        status_frame = tk.LabelFrame(self.left_panel, text=" 👁️ 現在の検知状態 ", 
                                    font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        self.lbl_status = tk.Label(status_frame, text="スキャン中...", bg=self.BG_WHITE, 
                                  font=("Meiryo", 14, "bold"), fg=self.TEXT_COLOR, pady=20)
        self.lbl_status.pack()

        # 2. 累計検知数
        stats_frame = tk.LabelFrame(self.left_panel, text=" 📊 統計データ ", 
                                   font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        stats_frame.pack(fill=tk.X, pady=10)
        
        self.lbl_count = tk.Label(stats_frame, text="発見したID数: 0", bg=self.BG_WHITE, 
                                 font=("Meiryo", 11), fg=self.TEXT_COLOR, pady=10)
        self.lbl_count.pack()

        # 3. 解析ログ
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 マーカー検知ログ ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Consolas", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.write_log("システムを起動しました。")

        # ヒント
        guide_text = "【Tips】\n・DICT_4X4_50のマーカーに対応。\n・ID:0 は特別なターゲットとして\n  強調表示されます。"
        tk.Label(self.left_panel, text=guide_text, bg="#FFFBEB", justify=tk.LEFT, 
                 font=("Meiryo", 9), fg="#95A5A6").pack(side=tk.BOTTOM, pady=20)

        # --- 右側：カメラプレビュー ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ AR リアルタイム・モニター ", 
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

    def process_frame(self, frame):
        """既存の描画ロジックを統合した解析処理"""
        corners, ids = self.engine.detect(frame)
        
        if ids is not None:
            # 基本の枠線描画
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)
            
            self.lbl_status.config(text=f"{len(ids)} 個のマーカーを検知中", fg=self.SAFE_COLOR)
            
            for i, marker_id in enumerate(ids):
                m_id = int(marker_id[0])
                c = corners[i][0]
                x, y = int(c[0][0]), int(c[0][1])

                # 統計とログの更新
                if m_id not in self.detected_ids:
                    self.detected_ids.add(m_id)
                    self.lbl_count.config(text=f"発見したID数: {len(self.detected_ids)}")
                
                now = time.time()
                if m_id not in self.last_log_time or (now - self.last_log_time[m_id]) > 5:
                    self.write_log(f"ID:{m_id} をスキャンしました")
                    self.last_log_time[m_id] = now

                # 既存のメッセージロジック
                message = f"ID: {m_id}"
                color = (0, 255, 0) # 緑 (BGR)

                if m_id == 0:
                    message = "Target Found!"
                    color = (0, 0, 255) # 赤
                    # ターゲット用の強調円
                    cv2.circle(frame, (int(np.mean(c[:, 0])), int(np.mean(c[:, 1]))), 40, color, 2)
                
                cv2.putText(frame, message, (x, y - 15), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)
        else:
            self.lbl_status.config(text="スキャン中...", fg=self.TEXT_COLOR)

        return frame

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            # 鏡像ではなく実際の配置を確認するため反転なし
            # 解析とHUD描画
            processed_frame = self.process_frame(frame)

            # Tkinter表示
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 50 and ch > 50:
                frame_rgb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
                
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
    # Windows高DPIディスプレイ対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = ARDetectorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()