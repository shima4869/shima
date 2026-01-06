# AI画風変換・アートカメラ ✨
# インストール: pip install opencv-python numpy pillow  
# 実行方法: python 17_neural_style.py
# Select Interpreter: Python 3.11.9

import cv2
import numpy as np
import os
import urllib.request
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import threading
import time
import datetime

# --- 既存の設定を継承 ---
MODELS = [
    {
        "name": "星月夜 (ゴッホ)",
        "file": "starry_night.t7",
        "url": "http://cs.stanford.edu/people/jcjohns/fast-neural-style/models/instance_norm/starry_night.t7"
    },
    {
        "name": "叫び (ムンク)",
        "file": "the_scream.t7",
        "url": "http://cs.stanford.edu/people/jcjohns/fast-neural-style/models/instance_norm/the_scream.t7"
    }
]

class NeuralStyleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI画風変換・アートカメラ ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"        # 緑

        # 既存システムの変数
        self.current_model_idx = 0
        self.net = None
        self.process_width = 320
        self.is_loading = False
        
        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.last_frame = None

        self.setup_ui()
        
        # 最初のモデルをロード（非同期）
        self.change_style(0)
        
        # UI更新ループ開始
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🎨 AI画風変換・アートカメラ", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：左1, 右4
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=4)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # スタイル情報
        style_info_frame = tk.LabelFrame(self.left_panel, text=" 👁️ 現在の画風 ", 
                                        font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                        fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        style_info_frame.pack(fill=tk.X, pady=(0, 10))

        self.style_label = tk.Label(style_info_frame, text="読込中...", bg=self.BG_WHITE, 
                                   font=("Meiryo", 16, "bold"), fg=self.TEXT_COLOR, pady=20)
        self.style_label.pack()

        # 操作ボタン
        btn_frame = tk.Frame(self.left_panel, bg="#FFFBEB")
        btn_frame.pack(fill=tk.X, pady=10)

        self.next_btn = tk.Button(btn_frame, text="次の画風に切り替え ⏭️", 
                                 command=self.next_style,
                                 bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                 relief=tk.FLAT, cursor="hand2", pady=15)
        self.next_btn.pack(fill=tk.X, pady=5)

        self.save_btn = tk.Button(btn_frame, text="アートを保存する 📸", 
                                 command=self.save_image,
                                 bg=self.SAFE_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                 relief=tk.FLAT, cursor="hand2", pady=15)
        self.save_btn.pack(fill=tk.X, pady=5)

        # ログエリア
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 システムログ ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.write_log("システムを起動しました。")

        # ガイド
        guide_label = tk.Label(self.left_panel, text="ヒント:\nモデルの初回ダウンロードには\n数十秒かかる場合があります。", 
                              bg="#FFFBEB", fg="#95A5A6", font=("Meiryo", 9), justify=tk.LEFT)
        guide_label.pack(side=tk.BOTTOM, pady=10)

        # --- 右側：映像プレビュー ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ リアルタイム・アートプレビュー ", 
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

    def download_model(self, model_info):
        """既存のダウンロードロジック"""
        filename = model_info["file"]
        url = model_info["url"]
        if not os.path.exists(filename):
            self.write_log(f"[{model_info['name']}] をダウンロード中...")
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response, open(filename, 'wb') as out_file:
                    out_file.write(response.read())
                self.write_log("ダウンロードが完了しました！")
            except Exception as e:
                self.write_log(f"ダウンロード失敗: {e}")
                return False
        return True

    def change_style(self, idx):
        def _task():
            self.is_loading = True
            self.next_btn.config(state=tk.DISABLED, text="読込中...")
            model_info = MODELS[idx]
            self.style_label.config(text="読込中...", fg="#95A5A6")
            
            if self.download_model(model_info):
                try:
                    self.net = cv2.dnn.readNetFromTorch(model_info["file"])
                    self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                    self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                    self.current_model_idx = idx
                    self.style_label.config(text=model_info["name"], fg=self.PRIMARY_COLOR)
                    self.write_log(f"画風を '{model_info['name']}' に変更しました。")
                except:
                    self.write_log("モデルの読み込みに失敗しました。")
            
            self.is_loading = False
            self.next_btn.config(state=tk.NORMAL, text="次の画風に切り替え ⏭️")

        threading.Thread(target=_task, daemon=True).start()

    def next_style(self):
        new_idx = (self.current_model_idx + 1) % len(MODELS)
        self.change_style(new_idx)

    def save_image(self):
        if self.last_frame is not None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"art_{timestamp}.jpg"
            cv2.imwrite(filename, self.last_frame)
            self.write_log(f"画像を保存しました: {filename}")
            messagebox.showinfo("保存完了", f"アート画像を保存しました！\n{filename}")

    def update_loop(self):
        """メインの更新処理ループ (既存の変換ロジックを統合)"""
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]

            if self.net is not None and not self.is_loading:
                try:
                    # 1. 処理用にリサイズ
                    ratio = self.process_width / w
                    small_frame = cv2.resize(frame, (self.process_width, int(h * ratio)))
                    sh, sw = small_frame.shape[:2]

                    # 2. AI入力形式変換 (既存定数)
                    blob = cv2.dnn.blobFromImage(small_frame, 1.0, (sw, sh), (103.939, 116.779, 123.68), swapRB=False, crop=False)
                    
                    # 3. 推論
                    self.net.setInput(blob)
                    out = self.net.forward()

                    # 4. 出力を画像に戻す
                    out = out.reshape(3, out.shape[2], out.shape[3])
                    out[0] += 103.939
                    out[1] += 116.779
                    out[2] += 123.68
                    out = out.transpose(1, 2, 0)
                    out = np.clip(out, 0, 255).astype(np.uint8)
                    
                    output_frame = cv2.resize(out, (w, h))
                except:
                    output_frame = frame
            else:
                output_frame = frame

            self.last_frame = output_frame.copy()

            # Canvasへ表示
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 50 and ch > 50:
                rgb_img = cv2.cvtColor(output_frame, cv2.COLOR_BGR2RGB)
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
    
    app = NeuralStyleApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()