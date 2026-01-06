# AI偽物画像（Deepfake）見破り機 ✨
# インストール: pip install tkinter matplotlib pillow opencv-python numpy
# 実行方法: python 16_deepfake_detector.py
# Select Interpreter: Python 3.11.9

import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox, filedialog, scrolledtext, ttk
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
import os
import sys # プロセス終了のために追加

class DeepfakeEngine:
    """周波数解析(FFT)を用いて画像の真偽を判定するエンジン"""
    
    def analyze_frequency(self, image_cv):
        """画像を周波数ドメインに変換し、特徴を抽出する"""
        if image_cv is None:
            return None, 0
            
        # グレースケール変換
        gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
        # 解析サイズを統一 (256x256)
        gray = cv2.resize(gray, (256, 256))
        
        # 2次元高速フーリエ変換 (FFT)
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        
        # マグニチュード・スペクトル（視覚化用）
        magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1)
        
        # 統計的特徴：高周波成分の強度を算出
        rows, cols = gray.shape
        crow, ccol = rows // 2, cols // 2
        
        mask = np.ones((rows, cols), np.uint8)
        r = 60 # 中心からの半径（低周波カット領域）
        cv2.circle(mask, (ccol, crow), r, 0, -1)
        
        high_freq_area = np.abs(fshift) * mask
        avg_high_freq = np.mean(high_freq_area[mask > 0])
        
        # 本物/偽物の判定スコアリング（簡易ヒューリスティック）
        score = min(100, max(0, 100 - (avg_high_freq / 5.0)))
        
        return magnitude_spectrum, score

class DeepfakeDetectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI偽物画像（Deepfake）見破り機 ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数 (シリーズ統一)
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"        # 緑
        self.ALERT_COLOR = "#E74C3C"       # 赤

        self.engine = DeepfakeEngine()
        
        # 状態管理
        self.img_paths = [None, None]
        
        self.setup_ui()

        # 【修正点】ウィンドウの×ボタンが押された時の動作を指定
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="👁️ AI偽物画像（Deepfake）見破り機", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=4)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        btn_frame = tk.LabelFrame(self.left_panel, text=" 📂 解析対象を選択 ", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        self.btn_a = tk.Button(btn_frame, text="画像 A を選択", command=lambda: self.load_image(0),
                              bg="#F7F7F7", font=("Meiryo", 10), pady=8, cursor="hand2")
        self.btn_a.pack(fill=tk.X, padx=15, pady=10)

        self.btn_b = tk.Button(btn_frame, text="画像 B を選択", command=lambda: self.load_image(1),
                              bg="#F7F7F7", font=("Meiryo", 10), pady=8, cursor="hand2")
        self.btn_b.pack(fill=tk.X, padx=15, pady=(0, 10))

        self.run_btn = tk.Button(self.left_panel, text="真偽解析を実行 🚀", 
                                command=self.run_analysis,
                                bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                relief=tk.FLAT, cursor="hand2", pady=15)
        self.run_btn.pack(fill=tk.X, pady=15)

        self.res_frame = tk.LabelFrame(self.left_panel, text=" 🧠 解析結果レポート ", 
                                      font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                      fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        self.res_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.summary_label = tk.Label(self.res_frame, text="画像を読み込んで\n解析ボタンを押してください", 
                                     font=("Meiryo", 11), bg=self.BG_WHITE, fg=self.TEXT_COLOR, 
                                     wraplength=300, justify=tk.LEFT)
        self.summary_label.pack(padx=15, pady=20)

        # --- 右側：画像＆グラフエリア ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.Frame(self.right_panel, bg="#FFFBEB")
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas_a = tk.Canvas(preview_frame, bg=self.BG_WHITE, highlightthickness=2, highlightbackground="#EEE")
        self.canvas_a.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.canvas_b = tk.Canvas(preview_frame, bg=self.BG_WHITE, highlightthickness=2, highlightbackground="#EEE")
        self.canvas_b.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        graph_frame = tk.LabelFrame(self.right_panel, text=" 📊 周波数マグニチュード・スペクトル (画像A vs 画像B) ", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        graph_frame.pack(fill=tk.BOTH, expand=True, pady=(15, 0))

        # Matplotlib Figure の作成
        self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(10, 4))
        self.fig.patch.set_facecolor('white')
        for ax in [self.ax1, self.ax2]:
            ax.axis('off')
            ax.set_title("Waiting for Analysis...")
            
        self.canvas_graph = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas_graph.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def load_image(self, idx):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")])
        if path:
            self.img_paths[idx] = path
            img = Image.open(path)
            img.thumbnail((500, 500))
            tk_img = ImageTk.PhotoImage(img)
            
            canvas = self.canvas_a if idx == 0 else self.canvas_b
            canvas.delete("all")
            # キャンバスサイズが確定していない場合があるため、遅延して中心に配置
            self.root.update_idletasks()
            canvas.create_image(canvas.winfo_width()//2, canvas.winfo_height()//2, image=tk_img)
            
            if idx == 0: self.tk_img_a = tk_img
            else: self.tk_img_b = tk_img
            
            btn = self.btn_a if idx == 0 else self.btn_b
            btn.config(text=os.path.basename(path), bg=self.SECONDARY_COLOR)

    def run_analysis(self):
        if not self.img_paths[0] or not self.img_paths[1]:
            messagebox.showwarning("入力不足", "2枚の画像を選択してください。")
            return

        self.summary_label.config(text="AIが周波数アーティファクトをスキャン中...", fg=self.PRIMARY_COLOR)
        self.root.update()

        results = []
        for path in self.img_paths:
            img_cv = cv2.imread(path)
            spec, score = self.engine.analyze_frequency(img_cv)
            results.append((spec, score))

        # グラフ描画
        self.ax1.clear()
        self.ax1.imshow(results[0][0], cmap='magma')
        self.ax1.set_title(f"Image A Spec (Score: {results[0][1]:.1f})")
        self.ax1.axis('off')

        self.ax2.clear()
        self.ax2.imshow(results[1][0], cmap='magma')
        self.ax2.set_title(f"Image B Spec (Score: {results[1][1]:.1f})")
        self.ax2.axis('off')
        
        self.canvas_graph.draw()

        score_a = results[0][1]
        score_b = results[1][1]
        winner = "A" if score_a > score_b else "B"
        diff = abs(score_a - score_b)
        
        status_msg = f"【解析完了】\n\n画像 A の信頼度: {score_a:.1f}%\n画像 B の信頼度: {score_b:.1f}%\n\n"
        
        if diff < 5:
            status_msg += "結果：両者とも同様の特性を持っています。"
            res_color = self.TEXT_COLOR
        else:
            status_msg += f"判定：画像 {winner} の方がより「本物」である確率が高いです。"
            res_color = self.SAFE_COLOR

        self.summary_label.config(text=status_msg, fg=res_color)

    def on_closing(self):
        """【重要】プログラムを完全に終了させるためのクリーンアップ処理"""
        try:
            plt.close(self.fig) # Matplotlibのグラフウィンドウを閉じる
            self.root.destroy() # Tkinterウィンドウを破棄
        except:
            pass
        sys.exit(0) # Pythonプロセスを強制終了

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = DeepfakeDetectorApp(root)
    root.mainloop()