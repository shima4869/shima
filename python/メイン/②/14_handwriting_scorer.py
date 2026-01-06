# AI美文字採点システム ✨
# インストール: pip install opencv-python numpy pillow
# 実行方法: python 14_handwriting_scorer.py
# Select Interpreter: Python 3.11.9

import cv2
import numpy as np
import os
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk
import threading
import time
import datetime
import sys

# --- AIエンジン (既存のシステムを完全に継承) ---
class HandwritingScorer:
    def __init__(self):
        # 基準となるお手本の設定
        self.target_char = "あ"
        self.model_img_path = f"model_font/{self.target_char}.png"
        self.model_contour = None
        
        # お手本の読み込みと解析
        if os.path.exists(self.model_img_path):
            self.model_contour = self.analyze_image(cv2.imread(self.model_img_path))

    def analyze_image(self, img):
        """画像から文字の輪郭（骨格）を抽出する既存ロジック"""
        if img is None: return None
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # 二値化
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # ノイズ除去
        kernel = np.ones((3,3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        
        # 輪郭抽出
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
            
        c = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(c)
        
        M = cv2.moments(c)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
        else:
            cx, cy = x + w//2, y + h//2
            
        return {
            "cnt": c,
            "rect": (x, y, w, h),
            "center": (cx, cy),
            "aspect_ratio": float(w)/h,
            "img_shape": img.shape[:2]
        }

    def calculate_score(self, input_data):
        """お手本と入力データを比較して採点する既存ロジック"""
        if self.model_contour is None or input_data is None:
            return 0, {}

        # 1. アスペクト比の比較
        ratio_diff = abs(self.model_contour["aspect_ratio"] - input_data["aspect_ratio"])
        score_ratio = max(0, 100 - (ratio_diff * 100))

        # 2. 重心の位置ズレ（バランス）
        mc = self.model_contour
        ic = input_data
        mc_rx = (mc["center"][0] - mc["rect"][0]) / mc["rect"][2]
        mc_ry = (mc["center"][1] - mc["rect"][1]) / mc["rect"][3]
        ic_rx = (ic["center"][0] - ic["rect"][0]) / ic["rect"][2]
        ic_ry = (ic["center"][1] - ic["rect"][1]) / ic["rect"][3]
        dist = np.sqrt((mc_rx - ic_rx)**2 + (mc_ry - ic_ry)**2)
        score_balance = max(0, 100 - (dist * 200))

        # 3. 形状の一致度
        match_val = cv2.matchShapes(mc["cnt"], ic["cnt"], 1, 0.0)
        score_shape = max(0, 100 - (match_val * 200))

        # 総合得点
        total_score = int((score_ratio * 0.2) + (score_balance * 0.3) + (score_shape * 0.5))
        
        details = {
            "配置・比率": int(score_ratio),
            "バランス": int(score_balance),
            "字の形": int(score_shape)
        }
        
        return total_score, details

class HandwritingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI美文字採点システム ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数 (シリーズ統一)
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"        # 緑
        self.ALERT_COLOR = "#E74C3C"       # 赤

        # エンジン初期化
        self.ai = HandwritingScorer()
        
        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.current_score = 0
        self.current_details = {}
        self.advice_text = "カメラに文字を映して採点ボタンを押してね！"
        
        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🖌️ AI美文字採点システム", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率：左1, 右3
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：採点・操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 1. 採点ボタン
        self.score_btn = tk.Button(self.left_panel, text="美文字採点を実行 🚀", 
                                  command=self.perform_scoring,
                                  bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 14, "bold"),
                                  relief=tk.FLAT, cursor="hand2", pady=15)
        self.score_btn.pack(fill=tk.X, pady=(0, 10))

        # 2. 総合スコア表示
        res_frame = tk.LabelFrame(self.left_panel, text=" 📊 採点結果 ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        res_frame.pack(fill=tk.X, pady=5)
        
        self.lbl_total_score = tk.Label(res_frame, text="0", bg=self.BG_WHITE, 
                                       font=("Impact", 64), fg=self.TEXT_COLOR)
        self.lbl_total_score.pack(pady=(10, 0))
        tk.Label(res_frame, text="POINTS", bg=self.BG_WHITE, font=("Impact", 12), fg="#95A5A6").pack(pady=(0, 10))

        # 3. 詳細スコア
        self.details_frame = tk.Frame(res_frame, bg=self.BG_WHITE)
        self.details_frame.pack(fill=tk.X, padx=20, pady=10)
        self.detail_labels = {}
        for key in ["配置・比率", "バランス", "字の形"]:
            f = tk.Frame(self.details_frame, bg=self.BG_WHITE)
            f.pack(fill=tk.X, pady=2)
            tk.Label(f, text=key, bg=self.BG_WHITE, font=("Meiryo", 9)).pack(side=tk.LEFT)
            lbl = tk.Label(f, text="--", bg=self.BG_WHITE, font=("Meiryo", 9, "bold"), fg=self.PRIMARY_COLOR)
            lbl.pack(side=tk.RIGHT)
            self.detail_labels[key] = lbl

        # 4. アドバイス表示
        advice_frame = tk.LabelFrame(self.left_panel, text=" 💡 AIのアドバイス ", 
                                    font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        advice_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.lbl_advice = tk.Label(advice_frame, text=self.advice_text, bg=self.BG_WHITE, 
                                  font=("Meiryo", 11), fg=self.TEXT_COLOR, wraplength=300, justify=tk.LEFT)
        self.lbl_advice.pack(padx=15, pady=15)

        # お手本登録ボタン
        self.reg_btn = tk.Button(self.left_panel, text="現在を「お手本」に設定 ✍️", 
                                command=self.register_model,
                                bg="#BDC3C7", fg="white", font=("Meiryo", 9),
                                relief=tk.FLAT, cursor="hand2", pady=8)
        self.reg_btn.pack(fill=tk.X)

        # --- 右側：カメラプレビュー ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        cam_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ スキャン画面 (緑の枠内に文字を書いてね) ", 
                                 font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        cam_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(cam_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def perform_scoring(self):
        """現在のROIを切り出して採点"""
        if not hasattr(self, 'current_roi'): return
        
        input_data = self.ai.analyze_image(self.current_roi)
        if input_data:
            self.current_score, self.current_details = self.ai.calculate_score(input_data)
            
            # アドバイスの決定
            if self.current_score > 90: self.advice_text = "素晴らしい！まるでプロのような美しさです。この調子で練習しましょう！"
            elif self.current_score > 70: self.advice_text = "とても上手です！あともう少し、全体のバランスを整えると完璧です。"
            elif self.current_score > 50: self.advice_text = "形は捉えられています。お手本をよく見て、丁寧になぞる意識を持つとさらに良くなります。"
            else: self.advice_text = "まずは一画一画、止める・はねるを意識して、ゆっくり書いてみましょう。"
            
            self.update_ui_results()
        else:
            messagebox.showwarning("認識エラー", "文字を検出できませんでした。枠内にハッキリと書いてください。")

    def register_model(self):
        """現在映っている文字をお手本として上書き"""
        if not hasattr(self, 'current_roi'): return
        new_model = self.ai.analyze_image(self.current_roi)
        if new_model:
            self.ai.model_contour = new_model
            messagebox.showinfo("お手本登録", "新しいお手本を記憶しました！これからはこの文字が基準になります。")
        else:
            messagebox.showerror("エラー", "お手本にする文字が見つかりませんでした。")

    def update_ui_results(self):
        """採点結果を画面に反映"""
        self.lbl_total_score.config(text=str(self.current_score))
        
        # スコアに応じた色分け
        if self.current_score > 80: color = self.SAFE_COLOR
        elif self.current_score < 50: color = self.ALERT_COLOR
        else: color = self.PRIMARY_COLOR
        self.lbl_total_score.config(fg=color)

        for key, val in self.current_details.items():
            if key in self.detail_labels:
                self.detail_labels[key].config(text=f"{val}点")
        
        self.lbl_advice.config(text=self.advice_text)

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1) # 鏡表示
            h, w, _ = frame.shape
            
            # ガイド枠の設定 (既存の250pxベース)
            box_size = 300
            x1 = (w - box_size) // 2
            y1 = (h - box_size) // 2
            x2 = x1 + box_size
            y2 = y1 + box_size
            
            # 採点用にROIを保持
            self.current_roi = frame[y1:y2, x1:x2].copy()
            
            display_frame = frame.copy()
            color = (0, 159, 255) # オレンジ (BGR)
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 3)
            # 角に装飾
            d = 30
            cv2.line(display_frame, (x1, y1), (x1+d, y1), color, 8)
            cv2.line(display_frame, (x1, y1), (x1, y1+d), color, 8)
            cv2.line(display_frame, (x2, y2), (x2-d, y2), color, 8)
            cv2.line(display_frame, (x2, y2), (x2, y2-d), color, 8)

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
    
    app = HandwritingApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()