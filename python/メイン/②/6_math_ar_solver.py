# 手書き数式・AR計算機 ✨
# インストール: pip install opencv-python pillow pytesseract sympy
# 実行方法: python 6_math_ar_solver.py
# Select Interpreter: Python 3.11.9

import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk
import sympy as sp
import pytesseract
import threading
import time
import os

class MathARCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("手書き数式・AR計算機 ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー設定
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"

        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.current_result = ""
        self.current_process = ""
        self.debug_img_tk = None # AIプレビュー用参照保持
        
        self.setup_ui()
        
        # カメラのスレッド開始
        self.thread = threading.Thread(target=self.video_loop, daemon=True)
        self.thread.start()

    def setup_ui(self):
        # タイトル
        title_label = tk.Label(self.root, text="🔢 手書き数式・AR計算機", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(15, 5))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # --- 左側：操作パネル (幅を広げてデバッグ枠を確保) ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=500)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        self.left_panel.pack_propagate(False) # 幅を固定

        # 操作ボタン類
        btn_frame = tk.Frame(self.left_panel, bg="#FFFBEB")
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        self.scan_btn = tk.Button(btn_frame, text="数式をスキャン 🔍", command=self.scan_formula,
                                 bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 14, "bold"),
                                 relief=tk.FLAT, cursor="hand2", pady=15)
        self.scan_btn.pack(fill=tk.X)

        # 修正エリア
        manual_frame = tk.LabelFrame(self.left_panel, text=" 📝 読み取り内容の修正 ", font=("Meiryo", 10, "bold"),
                                    bg=self.BG_WHITE, fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        manual_frame.pack(fill=tk.X, pady=10)
        
        self.formula_var = tk.StringVar()
        self.entry = tk.Entry(manual_frame, textvariable=self.formula_var, font=("Consolas", 16), justify="center")
        self.entry.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(manual_frame, text="修正して計算", command=self.manual_calculate,
                  bg="#BDC3C7", fg="white", font=("Meiryo", 10), pady=5).pack(fill=tk.X, padx=10, pady=(0, 10))

        # --- デバッグ表示エリア (ここを大きくしました) ---
        debug_outer = tk.LabelFrame(self.left_panel, text=" 👁️ AIが見ている画像 (ここを確認！) ", font=("Meiryo", 11, "bold"),
                                   bg=self.BG_WHITE, fg="#E67E22", relief=tk.RIDGE, bd=2)
        debug_outer.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.debug_label = tk.Label(debug_outer, text="スキャンするとここに\n拡大画像が表示されます", 
                                   bg="#F7F7F7", font=("Meiryo", 10), fg="#95A5A6")
        self.debug_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- 右側：カメラ表示エリア ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.right_panel, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def preprocess_image(self, img):
        """OCR認識率を上げるための前処理"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 拡大率を3倍にアップ
        gray = cv2.resize(gray, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        
        # ノイズ除去
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # 適応的二値化
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY_INV, 21, 10)
        
        # モルフォロジー変換（細い線を繋げ、ノイズを消す）
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return thresh

    def scan_formula(self):
        if not hasattr(self, 'current_frame_raw'): return
        
        # 【重要】以前の反転修正：
        # current_frame_raw はカメラの「生の画像」です。
        # ほとんどのWebカメラではこの時点で文字は正しい向き（正像）です。
        # 逆に反転させていたことが原因であれば、ここでは反転なしで進めます。
        raw_img = self.current_frame_raw 
        
        # 前処理
        processed = self.preprocess_image(raw_img)
        
        # デバッグ画像の表示サイズを拡大 (幅450px)
        debug_h, debug_w = processed.shape
        disp_w = 450
        ratio = disp_w / debug_w
        debug_disp = cv2.resize(processed, (disp_w, int(debug_h * ratio)))
        
        # 視認性のため白黒反転（背景白、文字黒）
        debug_disp_inv = cv2.bitwise_not(debug_disp)
        img_debug = ImageTk.PhotoImage(Image.fromarray(debug_disp_inv))
        
        self.debug_label.config(image=img_debug, text="")
        self.debug_img_tk = img_debug # 参照保持
        
        try:
            # Tesseract解析
            # psm 6: 均一な1つのテキストブロックとして扱う
            custom_config = r'--psm 6 -c tessedit_char_whitelist=0123456789+-*/^()x'
            text = pytesseract.image_to_string(processed, config=custom_config).strip()
            
            # 記号修正
            text = text.replace('x', '*').replace('=', '').replace(' ', '').replace('—', '-')
            
            if text:
                self.formula_var.set(text)
                self.calculate(text)
            else:
                self.current_process = "スキャン結果：空"
                self.current_result = "読み取れませんでした"
        except Exception:
            self.current_process = "OCR実行エラー"
            self.current_result = "Tesseractが利用可能か確認してください"

    def manual_calculate(self):
        self.calculate(self.formula_var.get())

    def calculate(self, formula_str):
        try:
            formula_str = formula_str.replace('^', '**')
            expr = sp.sympify(formula_str)
            result = sp.simplify(expr)
            self.current_process = f"解析中: {formula_str}"
            self.current_result = f"答え: {result}"
        except Exception:
            self.current_process = "解析エラー"
            self.current_result = "数式を正しく認識できませんでした"

    def draw_japanese_text(self, img, text, pos, font_size, color):
        img_pil = Image.fromarray(img)
        draw = ImageDraw.Draw(img_pil)
        font_path = "C:\\Windows\\Fonts\\msgothic.ttc" if os.name == 'nt' else "/System/Library/Fonts/jpn/ヒラギノ角ゴ ProN.ttc"
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()
        draw.text(pos, text, font=font, fill=color)
        return np.array(img_pil)

    def video_loop(self):
        while self.is_running:
            ret, frame = self.cap.read()
            if not ret: break
            
            # 生の映像（正像）をOCR用に保存
            self.current_frame_raw = frame.copy()
            
            # 画面表示用は鏡像（ユーザーの直感に合わせる）
            frame_preview = cv2.flip(frame, 1)
            h, w = frame_preview.shape[:2]
            
            # 外枠
            padding = 10
            cv2.rectangle(frame_preview, (padding, padding), (w - padding, h - padding), (67, 159, 255), 4)
            
            # 結果表示パネル
            if self.current_result:
                overlay = frame_preview.copy()
                panel_h = 120
                cv2.rectangle(overlay, (padding, padding), (w - padding, panel_h), (255, 255, 255), -1)
                cv2.addWeighted(overlay, 0.7, frame_preview, 0.3, 0, frame_preview)
                
                frame_preview = self.draw_japanese_text(frame_preview, self.current_process, (padding + 30, padding + 20), 18, (100, 100, 100))
                frame_preview = self.draw_japanese_text(frame_preview, self.current_result, (padding + 30, padding + 55), 36, (255, 159, 67))

            # Canvas更新
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 10 and ch > 10:
                resized = cv2.resize(frame_preview, (cw, ch))
                rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                img_tk = ImageTk.PhotoImage(Image.fromarray(rgb))
                self.canvas.itemconfig(self.image_item, image=img_tk)
                self.tk_img = img_tk 

            time.sleep(0.02)

    def on_closing(self):
        self.is_running = False
        if self.cap: self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    app = MathARCalculator(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()