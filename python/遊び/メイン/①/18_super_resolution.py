# AI画像高画質化・アップスケーラー (縦比較版)
# インストール: pip install opencv-python numpy pillow
# 実行方法: python 18_super_resolution.py
# Select Interpreter: Python 3.11.9

import cv2
import os
import urllib.request
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import threading
import time
import datetime

# --- モデル設定 ---
MODEL_NAME = "ESPCN_x4.pb"
MODEL_URL = "https://github.com/fannymonori/TF-ESPCN/raw/master/export/ESPCN_x4.pb"
SCALE = 4

class SuperResolutionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI画像高画質化・アップスケーラー (縦比較版) ✨")
        self.root.geometry("1400x950") # 縦並び用に少し高さを確保
        self.root.configure(bg="#FFFBEB")

        # カラー定数 (シリーズ統一デザイン)
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"        # 緑

        # 超解像エンジンの準備
        self.sr = cv2.dnn_superres.DnnSuperResImpl_create()
        self.is_model_loaded = False
        
        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.last_combined_frame = None

        self.setup_ui()
        
        # モデル準備スレッド開始
        threading.Thread(target=self.prepare_engine, daemon=True).start()
        
        # UI更新ループ開始
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="✨ AI画像高画質化・アップスケーラー", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(15, 5))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=5)
        
        # 比率調整：左(操作)1 : 右(プレビュー)5 
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=5)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=300)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # ステータス情報
        status_frame = tk.LabelFrame(self.left_panel, text=" 👁️ システム状態 ", 
                                    font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        self.status_label = tk.Label(status_frame, text="準備中...", bg=self.BG_WHITE, 
                                    font=("Meiryo", 11, "bold"), fg=self.TEXT_COLOR, pady=15)
        self.status_label.pack()

        # 保存ボタン
        self.save_btn = tk.Button(self.left_panel, text="比較画像を保存 📸", 
                                 command=self.save_comparison,
                                 bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 11, "bold"),
                                 relief=tk.FLAT, cursor="hand2", pady=15)
        self.save_btn.pack(fill=tk.X, pady=10)

        # ログエリア
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 ログ ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 8), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.write_log("起動完了。")

        # ヒント
        hint_label = tk.Label(self.left_panel, text="【改善内容】\n・比較を縦に並べました\n・カメラの全画角を使用\n・表示サイズを最大化しました", 
                             bg="#FFFBEB", fg="#95A5A6", font=("Meiryo", 9), justify=tk.LEFT)
        hint_label.pack(side=tk.BOTTOM, pady=10)

        # --- 右側：映像表示パネル (拡大) ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ 高画質化比較 (上: 通常拡大 / 下: AI超解像) ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="#222222", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def write_log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def prepare_engine(self):
        """AIモデルの準備と読み込み"""
        if not os.path.exists(MODEL_NAME):
            self.write_log(f"モデルをダウンロード中...")
            try:
                req = urllib.request.Request(MODEL_URL, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response, open(MODEL_NAME, 'wb') as out_file:
                    out_file.write(response.read())
                self.write_log("完了しました。")
            except Exception as e:
                self.status_label.config(text="エラー: DL失敗", fg="red")
                return

        try:
            self.sr.readModel(MODEL_NAME)
            self.sr.setModel("espcn", SCALE) 
            self.is_model_loaded = True
            self.status_label.config(text="AI稼働中 ✨", fg=self.SAFE_COLOR)
            self.write_log("AIエンジンの準備が完了しました。")
        except:
            self.status_label.config(text="エラー: ロード失敗", fg="red")

    def save_comparison(self):
        """現在の比較画像をファイルに保存"""
        if self.last_combined_frame is not None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sr_vertical_{timestamp}.jpg"
            cv2.imwrite(filename, self.last_combined_frame)
            self.write_log(f"画像を保存: {filename}")
            messagebox.showinfo("保存完了", f"比較画像を保存しました！\n{filename}")

    def update_loop(self):
        """メインループ（縦並び・広角対応）"""
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1) # 鏡表示
            h_orig, w_orig = frame.shape[:2]
            
            # --- 【改善】画角を崩さず、カメラ全域を処理対象にする ---
            # 処理負荷を最適化するため、全画角を一度1/SCALEサイズに縮小し「低画質版」とする
            low_res_w, low_res_h = w_orig // SCALE, h_orig // SCALE
            low_res_img = cv2.resize(frame, (low_res_w, low_res_h), interpolation=cv2.INTER_LINEAR)

            # 1. 比較用：普通の拡大 (Bicubic)
            bicubic_img = cv2.resize(low_res_img, (w_orig, h_orig), interpolation=cv2.INTER_CUBIC)

            # 2. AIによる超解像
            if self.is_model_loaded:
                try:
                    ai_img = self.sr.upsample(low_res_img)
                except:
                    ai_img = bicubic_img
            else:
                ai_img = bicubic_img

            # 3. 画面の縦結合 (Bicubicを上、AIを下)
            if ai_img.shape == bicubic_img.shape:
                # 縦に結合
                combined = np.vstack((bicubic_img, ai_img))
                
                # 分離線の描画
                cv2.line(combined, (0, h_orig), (w_orig, h_orig), (255, 255, 255), 2)
                
                # ラベル文字の描画
                font_scale = 1.0
                thickness = 2
                cv2.putText(combined, "Normal Zoom (Bicubic)", (20, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness)
                cv2.putText(combined, "AI Super Resolution", (20, h_orig + 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness)
                
                self.last_combined_frame = combined.copy()

                # --- Canvas表示の最大化処理 ---
                self.root.update_idletasks()
                cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
                
                if cw > 50 and ch > 50:
                    rgb_img = cv2.cvtColor(combined, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(rgb_img)
                    
                    # 画面サイズに合わせて最適な倍率でリサイズ
                    img_w, img_h = pil_img.size
                    ratio = min(cw / img_w, ch / img_h)
                    new_size = (int(img_w * ratio), int(img_h * ratio))
                    
                    display_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
                    
                    self.tk_img = ImageTk.PhotoImage(display_img)
                    self.canvas.itemconfig(self.image_item, image=self.tk_img)
                    # 中央配置
                    self.canvas.coords(self.image_item, (cw - new_size[0]) // 2, (ch - new_size[1]) // 2)

        if self.is_running:
            self.root.after(30, self.update_loop)

    def on_closing(self):
        self.is_running = False
        if self.cap.isOpened():
            self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    # 高解像度ディスプレイ対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = SuperResolutionApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()