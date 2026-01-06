# AI自動家計簿カメラ ✨
# インストール: pip install opencv-python pytesseract pillow
# 実行方法: python 11_python receipt_ocr.py
# Select Interpreter: Python 3.11.9

import cv2
import pytesseract
import re
import datetime
import csv
import os
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import threading
import time
import platform

# --- 既存のエンジンクラス (システムロジックを継承) ---
class ReceiptOCR:
    def __init__(self, csv_file="kakeibo.csv"):
        self.csv_file = csv_file
        # Tesseractのパス設定 (Windows用)
        self._setup_tesseract_path()
        # CSV初期化
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["日付", "店舗名(推測)", "合計金額", "生データ"])

    def _setup_tesseract_path(self):
        """OSに合わせてTesseractのパスを自動または手動で設定"""
        if platform.system() == "Windows":
            # 一般的なインストール先をチェック
            paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
            ]
            for p in paths:
                if os.path.exists(p):
                    pytesseract.pytesseract.tesseract_cmd = p
                    break

    def preprocess_image(self, img):
        """既存の前処理ロジック"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    def extract_info(self, text):
        """既存のテキスト解析ロジック"""
        info = {
            "date": datetime.datetime.now().strftime('%Y-%m-%d'),
            "shop": "不明な店舗",
            "total": 0
        }
        lines = text.split('\n')
        total_pattern = re.compile(r'(合\s*計|小\s*計|Total|お買上計)', re.IGNORECASE)
        max_price = 0

        for line in lines:
            if len(line) < 3: continue
            # 店名推測
            if info["shop"] == "不明な店舗":
                if any(x in line for x in ["店", "株式会社", "マート", "ショップ", "スーパー"]):
                    info["shop"] = line.strip()
            # 金額抽出
            if total_pattern.search(line) or '¥' in line or '円' in line:
                clean_line = line.replace('¥', '').replace('円', '').replace(',', '').replace(' ', '')
                match = re.search(r'\d+', clean_line)
                if match:
                    price = int(match.group())
                    if price > max_price:
                        max_price = price
        
        info["total"] = max_price
        return info

    def save_to_csv(self, info, raw_text):
        """既存のCSV保存ロジック"""
        with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            flat_text = raw_text.replace('\n', ' / ')
            writer.writerow([info["date"], info["shop"], info["total"], flat_text[:50]])
        return True

class ReceiptApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI自動家計簿カメラ ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数 (シリーズ共通)
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"        # 緑

        # OCRエンジンの初期化
        self.ocr_engine = ReceiptOCR()
        
        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.last_processed_view = None
        
        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🧾 AI自動家計簿カメラ", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率：左1, 右3
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：ステータス・結果パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 1. スキャン実行ボタン
        self.scan_btn = tk.Button(self.left_panel, text="レシートをスキャン 🚀", 
                                 command=self.perform_scan,
                                 bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 14, "bold"),
                                 relief=tk.FLAT, cursor="hand2", pady=15)
        self.scan_btn.pack(fill=tk.X, pady=(0, 15))

        # 2. 最新の認識結果
        res_frame = tk.LabelFrame(self.left_panel, text=" 👁️ 最新の読み取り結果 ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        res_frame.pack(fill=tk.X, pady=5)
        
        self.lbl_shop = tk.Label(res_frame, text="店名: ---", bg=self.BG_WHITE, font=("Meiryo", 11), fg=self.TEXT_COLOR)
        self.lbl_shop.pack(anchor="w", padx=15, pady=(10, 5))
        
        self.lbl_total = tk.Label(res_frame, text="金額: ---", bg=self.BG_WHITE, font=("Meiryo", 18, "bold"), fg=self.SAFE_COLOR)
        self.lbl_total.pack(anchor="w", padx=15, pady=(0, 10))

        # 3. AIプレビュー (前処理後の白黒画像)
        debug_frame = tk.LabelFrame(self.left_panel, text=" 🔬 AIが見ている画像 ", 
                                   font=("Meiryo", 9, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        debug_frame.pack(fill=tk.X, pady=10)
        
        self.debug_canvas = tk.Canvas(debug_frame, height=180, bg="#F0F0F0", highlightthickness=0)
        self.debug_canvas.pack(fill=tk.X, padx=5, pady=5)
        self.debug_image_item = self.debug_canvas.create_image(0, 0, anchor=tk.NW)

        # 4. 認識ログ
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 記録履歴 ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.write_log("システムを起動しました。")

        # --- 右側：カメラプレビューパネル ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        cam_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ スキャン画面 (緑の枠に合わせてください) ", 
                                 font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        cam_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(cam_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def write_log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def perform_scan(self):
        """スキャンボタンが押された時の処理 (非同期実行)"""
        if not hasattr(self, 'current_roi'): return
        
        self.scan_btn.config(state=tk.DISABLED, text="スキャン中...")
        self.write_log("OCR解析を開始します...")
        
        # 処理負荷を考慮してスレッドで実行
        threading.Thread(target=self._scan_thread_logic, daemon=True).start()

    def _scan_thread_logic(self):
        try:
            # 枠内の画像を前処理
            processed = self.ocr_engine.preprocess_image(self.current_roi)
            
            # デバッグ用ビューの更新準備
            self.last_processed_view = processed.copy()
            
            # OCR実行
            custom_config = r'--oem 3 --psm 6 -l jpn+eng'
            text = pytesseract.image_to_string(processed, config=custom_config)
            
            # 解析
            info = self.ocr_engine.extract_info(text)
            
            # UI更新 (メインスレッド)
            self.root.after(0, lambda: self.update_scan_result(info, text))
            
        except Exception as e:
            self.root.after(0, lambda: self.write_log(f"エラー: {e}"))
            self.root.after(0, lambda: self.scan_btn.config(state=tk.NORMAL, text="レシートをスキャン 🚀"))

    def update_scan_result(self, info, raw_text):
        """解析結果をUIに反映"""
        if info["total"] > 0:
            self.lbl_shop.config(text=f"店名: {info['shop']}")
            self.lbl_total.config(text=f"金額: {info['total']} 円")
            self.ocr_engine.save_to_csv(info, raw_text)
            self.write_log(f"成功: {info['total']}円 ({info['shop']}) を記録しました。")
        else:
            self.write_log("失敗: 金額が検出できませんでした。")
            messagebox.showwarning("読み取り不可", "金額を特定できませんでした。レシートを枠に合わせて再試行してください。")

        # デバッグ画像の表示
        if self.last_processed_view is not None:
            db_h, db_w = self.last_processed_view.shape
            ratio = self.debug_canvas.winfo_width() / db_w
            new_size = (int(db_w * ratio), int(db_h * ratio))
            db_pil = Image.fromarray(self.last_processed_view).resize(new_size, Image.NEAREST)
            self.tk_debug_img = ImageTk.PhotoImage(db_pil)
            self.debug_canvas.itemconfig(self.debug_image_item, image=self.tk_debug_img)

        self.scan_btn.config(state=tk.NORMAL, text="レシートをスキャン 🚀")

    def update_loop(self):
        """カメラ更新ループ"""
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1) # 鏡像
            h, w = frame.shape[:2]
            
            # ガイド枠の計算 (既存の400x600ベース)
            box_w, box_h = 350, 500
            x1 = (w - box_w) // 2
            y1 = (h - box_h) // 2
            x2 = x1 + box_w
            y2 = y1 + box_h
            
            # OCR用に枠内を保持
            self.current_roi = frame[y1:y2, x1:x2]
            
            # ガイド枠とデザインの描画
            display_frame = frame.copy()
            color = (0, 159, 255) # BGR オレンジ
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 3)
            # 四隅に飾り
            d = 30
            cv2.line(display_frame, (x1, y1), (x1+d, y1), color, 8)
            cv2.line(display_frame, (x1, y1), (x1, y1+d), color, 8)
            cv2.line(display_frame, (x2, y2), (x2-d, y2), color, 8)
            cv2.line(display_frame, (x2, y2), (x2, y2-d), color, 8)

            # メインCanvas表示
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
    
    app = ReceiptApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()