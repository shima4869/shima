# AI数独自動解答カメラ ✨
# インストール: pip install tkinter requests pillow opencv-python numpy pytesseract
# 実行方法: python 15_sudoku_solver_camera.py
# Select Interpreter: Python 3.11.9

import cv2
import numpy as np
import pytesseract
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import threading
import time
import os
import sys
import platform

class SudokuEngine:
    """数独の画像解析と解答アルゴリズムを担当するエンジン"""
    def __init__(self):
        self._setup_tesseract()
        self.grid_size = 9

    def _setup_tesseract(self):
        """Tesseractの実行パスを自動設定"""
        if platform.system() == "Windows":
            paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
            ]
            for p in paths:
                if os.path.exists(p):
                    pytesseract.pytesseract.tesseract_cmd = p
                    break

    def solve(self, board):
        """バックトラッキングによる数独解答アルゴリズム"""
        def is_valid(b, row, col, num):
            for i in range(9):
                if b[row][i] == num or b[i][col] == num: return False
            start_row, start_col = 3 * (row // 3), 3 * (col // 3)
            for i in range(3):
                for j in range(3):
                    if b[start_row + i][start_col + j] == num: return False
            return True

        def find_empty(b):
            for i in range(9):
                for j in range(9):
                    if b[i][j] == 0: return i, j
            return None

        empty = find_empty(board)
        if not empty: return True
        row, col = empty

        for i in range(1, 10):
            if is_valid(board, row, col, i):
                board[row][col] = i
                if self.solve(board): return True
                board[row][col] = 0
        return False

    def preprocess_and_find_grid(self, frame):
        """画像から数独の枠線を検出して平坦化する"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours: return None, None
        
        # 最大の四角形を探す
        best_cnt = None
        max_area = 0
        for c in contours:
            area = cv2.contourArea(c)
            if area > 20000:
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)
                if len(approx) == 4 and area > max_area:
                    best_cnt = approx
                    max_area = area
        
        if best_cnt is None: return None, None

        # 頂点の整理と透視変換
        pts = best_cnt.reshape(4, 2)
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        
        side = 450
        dst = np.array([[0, 0], [side-1, 0], [side-1, side-1], [0, side-1]], dtype="float32")
        matrix = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(gray, matrix, (side, side))
        
        return warped, matrix

    def extract_digits(self, warped_img):
        """平坦化した画像から81マスの数字をOCRで読み取る"""
        board = np.zeros((9, 9), dtype=int)
        side = warped_img.shape[0]
        cell_w = side // 9
        
        for r in range(9):
            for c in range(9):
                cell = warped_img[r*cell_w:(r+1)*cell_w, c*cell_w:(c+1)*cell_w]
                # マスの端の線を消すために少し内側を切り抜く
                margin = cell_w // 5
                cell_inner = cell[margin:-margin, margin:-margin]
                
                # 二値化
                _, cell_thresh = cv2.threshold(cell_inner, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                
                # OCR実行 (数字1文字のみに最適化)
                config = "--psm 10 -c tessedit_char_whitelist=123456789"
                text = pytesseract.image_to_string(cell_thresh, config=config).strip()
                
                if text.isdigit():
                    board[r][c] = int(text)
        return board

class SudokuApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI数独自動解答カメラ ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"
        self.SECONDARY_COLOR = "#FFCC33"
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"

        self.engine = SudokuEngine()
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.is_solving = False
        
        # 解答データ保持
        self.solved_board = None
        self.original_board = None
        self.last_matrix = None
        
        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🧩 AI数独自動解答カメラ", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 解析ボタン
        self.solve_btn = tk.Button(self.left_panel, text="パズルを解く 🚀", 
                                  command=self.start_solve_thread,
                                  bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 14, "bold"),
                                  relief=tk.FLAT, cursor="hand2", pady=15)
        self.solve_btn.pack(fill=tk.X, pady=(0, 15))

        self.reset_btn = tk.Button(self.left_panel, text="リセット 🔄", 
                                  command=self.reset_puzzle,
                                  bg="#BDC3C7", fg="white", font=("Meiryo", 11),
                                  relief=tk.FLAT, cursor="hand2", pady=10)
        self.reset_btn.pack(fill=tk.X, pady=5)

        # ステータス
        self.status_label = tk.Label(self.left_panel, text="状態: 待機中", bg="#FFFBEB", 
                                    font=("Meiryo", 10, "bold"), fg=self.TEXT_COLOR)
        self.status_label.pack(pady=20)

        # ログ
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 ログ ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.write_log("システムを起動しました。")

        # ヒント
        guide_text = "【使い方】\n・新聞等の数独を枠いっぱいに映してね。\n・ボタンを押すとAIが数字をスキャンします。\n・解答はARとして画面に合成されます。"
        tk.Label(self.left_panel, text=guide_text, bg="#FFFBEB", justify=tk.LEFT, 
                 font=("Meiryo", 9), fg="#95A5A6").pack(side=tk.BOTTOM, pady=20)

        # --- 右側：カメラプレビュー ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ AR 解答モニター ", 
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

    def reset_puzzle(self):
        self.solved_board = None
        self.original_board = None
        self.status_label.config(text="状態: 待機中", fg=self.TEXT_COLOR)
        self.write_log("パズルをリセットしました。")

    def start_solve_thread(self):
        if self.is_solving: return
        self.is_solving = True
        self.solve_btn.config(state=tk.DISABLED, text="解析中...")
        threading.Thread(target=self.solve_logic, daemon=True).start()

    def solve_logic(self):
        ret, frame = self.cap.read()
        if not ret: return
        
        self.write_log("1. グリッドを検出中...")
        warped, matrix = self.engine.preprocess_and_find_grid(frame)
        
        if warped is None:
            self.root.after(0, lambda: self.handle_error("数独の枠が見つかりませんでした。"))
            return
        
        self.write_log("2. 数字をスキャン中...")
        board = self.engine.extract_digits(warped)
        self.original_board = board.copy()
        
        self.write_log("3. 数学的に解答を計算中...")
        solve_board = board.copy()
        if self.engine.solve(solve_board):
            self.solved_board = solve_board
            self.last_matrix = matrix
            self.root.after(0, self.handle_success)
        else:
            self.root.after(0, lambda: self.handle_error("このパズルは解けませんでした（誤認識の可能性があります）。"))

    def handle_success(self):
        self.is_solving = False
        self.solve_btn.config(state=tk.NORMAL, text="パズルを解く 🚀")
        self.status_label.config(text="状態: 解答完了！ ✅", fg=self.SAFE_COLOR)
        self.write_log("解答に成功しました！AR表示を維持します。")

    def handle_error(self, msg):
        self.is_solving = False
        self.solve_btn.config(state=tk.NORMAL, text="パズルを解く 🚀")
        self.status_label.config(text="状態: エラー ❌", fg="red")
        messagebox.showwarning("解析失敗", msg)
        self.write_log(f"エラー: {msg}")

    def draw_ar_overlay(self, frame):
        """解いた数字を元のカメラ映像に投影（逆透視変換）"""
        if self.solved_board is None or self.last_matrix is None:
            return frame
        
        h, w = frame.shape[:2]
        overlay = np.zeros((450, 450, 3), dtype=np.uint8)
        cell_w = 450 // 9
        
        for r in range(9):
            for c in range(9):
                # 答えた数字のみを描画（元からある数字は描かない）
                if self.original_board[r][c] == 0:
                    val = self.solved_board[r][c]
                    pos = (c * cell_w + 15, r * cell_w + 40)
                    cv2.putText(overlay, str(val), pos, cv2.FONT_HERSHEY_SIMPLEX, 1.2, (46, 204, 113), 3)

        # 逆透視変換で元の位置に合わせる
        inv_matrix = np.linalg.inv(self.last_matrix)
        ar_layer = cv2.warpPerspective(overlay, inv_matrix, (w, h))
        
        # 合成
        combined = cv2.addWeighted(frame, 1.0, ar_layer, 1.0, 0)
        return combined

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            # 鏡像にすると文字が反転するため、あえてフリップしない（またはOCR直前で戻す）
            # ここでは正像で表示します
            display_frame = self.draw_ar_overlay(frame)
            
            # グリッド検出をリアルタイムで視覚化
            if not self.is_solving and self.solved_board is None:
                # 簡易的な枠線ガイドを描画
                h, w = display_frame.shape[:2]
                cv2.rectangle(display_frame, (w//2-200, h//2-200), (w//2+200, h//2+200), (255, 159, 67), 2)
                cv2.putText(display_frame, "ALIGN SUDOKU HERE", (w//2-120, h//2-210), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 159, 67), 2)

            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 50 and ch > 50:
                rgb_img = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_img)
                ratio = min(cw/w, ch/h)
                new_size = (int(w*ratio), int(h*ratio))
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
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    app = SudokuApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()