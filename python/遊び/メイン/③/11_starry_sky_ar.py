# AI星空解説ARガイド ✨
# インストール: pip install tkinter requests pillow opencv-python numpy
# 実行方法: python 11_starry_sky_ar.py
# Select Interpreter: Python 3.11.9

import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk, filedialog
from PIL import Image, ImageTk
import threading
import time
import datetime
import os
import sys

class StarSkyEngine:
    """星の検出と星座・惑星のARオーバーレイを管理するエンジン"""
    def __init__(self):
        # 簡易的な星の名前データベース
        self.celestial_objects = [
            {"name": "木星 (Jupiter)", "type": "Planet", "color": (150, 255, 255)},
            {"name": "シリウス (Sirius)", "type": "Star", "color": (255, 200, 150)},
            {"name": "ベテルギウス (Betelgeuse)", "type": "Star", "color": (100, 100, 255)},
            {"name": "土星 (Saturn)", "type": "Planet", "color": (200, 255, 200)},
            {"name": "火星 (Mars)", "type": "Planet", "color": (100, 100, 255)},
            {"name": "プロキオン (Procyon)", "type": "Star", "color": (200, 255, 255)},
            {"name": "デネブ (Deneb)", "type": "Star", "color": (255, 255, 200)},
            {"name": "ベガ (Vega)", "type": "Star", "color": (220, 220, 255)}
        ]
        
    def detect_stars(self, frame):
        """画像から明るい点（星）を検出する"""
        if frame is None: return []
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # ノイズを飛ばしつつ輝点を強調
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            _, thresh = cv2.threshold(blurred, 180, 255, cv2.THRESH_BINARY)
            
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            stars = []
            for cnt in contours:
                M = cv2.moments(cnt)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    # 小さすぎる輝点や、輪郭面積が一定以下のものを星として抽出
                    if cv2.contourArea(cnt) < 300:
                        stars.append((cx, cy))
            return stars
        except:
            return []

    def draw_ar_overlay(self, frame, stars):
        """検出された星に対して星座線やラベルを描画する"""
        if frame is None: return None
        h, w = frame.shape[:2]
        overlay = frame.copy()
        
        if len(stars) >= 2:
            # 星座線のシミュレーション (近接点同士を結ぶ)
            for i in range(len(stars)):
                for j in range(i + 1, len(stars)):
                    dist = np.sqrt((stars[i][0] - stars[j][0])**2 + (stars[i][1] - stars[j][1])**2)
                    if 40 < dist < 180:
                        cv2.line(overlay, stars[i], stars[j], (255, 159, 67), 1, cv2.LINE_AA)

        # 惑星・主要星のタグ付け (明るい順に割り当てをシミュレート)
        for i, star in enumerate(stars[:len(self.celestial_objects)]):
            obj = self.celestial_objects[i]
            cv2.circle(overlay, star, 18, obj["color"], 2)
            cv2.circle(overlay, star, 3, (255, 255, 255), -1)
            
            # 視認性の高いテキスト描画
            cv2.putText(overlay, obj['name'], (star[0] + 25, star[1]), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(overlay, f"[{obj['type']}]", (star[0] + 25, star[1] + 25), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, obj["color"], 1, cv2.LINE_AA)

        return overlay

class StarrySkyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI星空解説AR ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"
        self.SECONDARY_COLOR = "#FFCC33"
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"

        self.engine = StarSkyEngine()
        
        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.mode = "camera" # "camera" or "image"
        self.loaded_image = None
        
        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🌌 AI星空解説ARガイド", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=4)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=350)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 1. 読み込みボタン
        ctrl_frame = tk.LabelFrame(self.left_panel, text=" 📂 画像を読み込む ", 
                                  font=("Meiryo", 11, "bold"), bg="#FFFFFF", 
                                  fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        ctrl_frame.pack(fill=tk.X, pady=(0, 10))

        self.btn_load = tk.Button(ctrl_frame, text="星空ファイルを選択 📁", 
                                 command=self.load_star_image,
                                 bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 10, "bold"),
                                 relief=tk.FLAT, cursor="hand2", pady=12)
        self.btn_load.pack(fill=tk.X, padx=15, pady=10)

        self.btn_camera = tk.Button(ctrl_frame, text="カメラ映像に戻る 📷", 
                                   command=self.back_to_camera,
                                   bg="#BDC3C7", fg="white", font=("Meiryo", 10, "bold"),
                                   relief=tk.FLAT, cursor="hand2", pady=12)
        self.btn_camera.pack(fill=tk.X, padx=15, pady=(0, 10))

        # 2. 解析ステータス
        data_frame = tk.LabelFrame(self.left_panel, text=" 📊 解析ステータス ", 
                                  font=("Meiryo", 10, "bold"), bg="#FFFFFF", 
                                  fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        data_frame.pack(fill=tk.X, pady=10)
        
        self.lbl_mode = tk.Label(data_frame, text="モード: カメラ映像", bg="#FFFFFF", font=("Meiryo", 10, "bold"), fg=self.SAFE_COLOR)
        self.lbl_mode.pack(anchor="w", padx=15, pady=(10, 5))

        self.lbl_star_count = tk.Label(data_frame, text="検出された星: 0個", bg="#FFFFFF", font=("Meiryo", 10))
        self.lbl_star_count.pack(anchor="w", padx=15, pady=(0, 10))

        # 3. ログエリア
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 ログ ", 
                                 font=("Meiryo", 10, "bold"), bg="#FFFFFF", 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Consolas", 9), 
                                                 bg="#FFFFFF", relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.write_log("システム準備完了。")

        # ヒント
        guide_text = "【Tips】\n・日本語名のファイルにも対応しました。\n・星が白くハッキリ映った画像を\n　選んでください。"
        tk.Label(self.left_panel, text=guide_text, bg="#FFFBEB", justify=tk.LEFT, 
                 font=("Meiryo", 9), fg="#95A5A6").pack(side=tk.BOTTOM, pady=10)

        # --- 右側：プレビューモニター ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ AR 観測・解析モニター ", 
                                     font=("Meiryo", 11, "bold"), bg="#FFFFFF", 
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

    def load_star_image(self):
        """日本語パスに対応した画像読み込みロジック"""
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")])
        if path:
            try:
                # 【重要】cv2.imread(path) の代わりに numpy を使用して日本語パスに対応
                with open(path, "rb") as f:
                    file_bytes = np.asarray(bytearray(f.read()), dtype=np.uint8)
                    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

                if img is not None:
                    self.loaded_image = img
                    self.mode = "image"
                    self.lbl_mode.config(text="モード: 画像ファイル 🖼️", fg=self.PRIMARY_COLOR)
                    self.btn_camera.config(bg=self.SAFE_COLOR)
                    self.write_log(f"画像を読み込みました: {os.path.basename(path)}")
                    # 読み込み直後に1回描画を走らせる
                    self.root.update_idletasks()
                else:
                    raise Exception("デコード失敗")
            except Exception as e:
                self.write_log(f"読み込み失敗: {str(e)}")
                messagebox.showerror("エラー", f"画像の読み込みに失敗しました。\nファイルが壊れているか、形式が未対応です。")

    def back_to_camera(self):
        self.mode = "camera"
        self.lbl_mode.config(text="モード: カメラ映像 🎥", fg=self.SAFE_COLOR)
        self.btn_camera.config(bg="#BDC3C7")
        self.write_log("カメラ映像に復帰しました。")

    def update_loop(self):
        """メインの表示・解析ループ"""
        frame = None
        
        if self.mode == "camera":
            ret, frame = self.cap.read()
        else:
            if self.loaded_image is not None:
                frame = self.loaded_image.copy()

        if frame is not None:
            # 星の検出とAR描画
            stars = self.engine.detect_stars(frame)
            self.lbl_star_count.config(text=f"検出された星: {len(stars)}個")
            
            display_frame = self.engine.draw_ar_overlay(frame, stars)
            
            # 中央照準の描画
            h, w = display_frame.shape[:2]
            cv2.drawMarker(display_frame, (w//2, h//2), (46, 204, 113), cv2.MARKER_CROSS, 30, 2)

            # Tkinter Canvasへの転送
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            
            if cw > 50 and ch > 50:
                rgb_img = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_img)
                
                # アスペクト比を保ってリサイズ
                fw, fh = pil_img.size
                ratio = min(cw/fw, ch/fh)
                new_size = (int(fw*ratio), int(fh*ratio))
                pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
                
                self.tk_img = ImageTk.PhotoImage(pil_img)
                self.canvas.itemconfig(self.image_item, image=self.tk_img)
                # 中央寄せ
                self.canvas.coords(self.image_item, (cw-new_size[0])//2, (ch-new_size[1])//2)

        if self.is_running:
            # カメラ時はリアルタイム、画像時はリソース節約のため少し遅延
            interval = 30 if self.mode == "camera" else 150
            self.root.after(interval, self.update_loop)

    def on_closing(self):
        self.is_running = False
        if self.cap: self.cap.release()
        self.root.destroy()
        sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    # Windows高DPI対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = StarrySkyApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()