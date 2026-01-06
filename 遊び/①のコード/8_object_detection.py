# AI物体認識システム・高速版 ✨
# インストール: pip install tkinter ultralytics opencv-python numpy pillow
# 実行方法: python object_detection.py
# Select Interpreter: Python 3.11.9

import cv2
from ultralytics import YOLO
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import time
import os
import sys
import threading

class ObjectDetectionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI物体認識システム (高速版) ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"
        self.SECONDARY_COLOR = "#FFCC33"
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"

        # AIモデルの初期化
        print("AIモデルを読み込んでいます...")
        try:
            # 推論速度重視で軽量なnモデルを使用
            self.model = YOLO('yolov8n.pt') 
        except Exception as e:
            messagebox.showerror("モデルエラー", f"YOLOモデルの読み込みに失敗しました: {e}")
            sys.exit(1)

        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        
        # 非同期処理用の変数
        self.latest_frame = None       # 最新の生フレーム
        self.annotated_frame = None    # AIが書き込んだフレーム
        self.current_counts_text = "スキャン中..."
        self.fps = 0
        self.prev_time = time.time()
        self.lock = threading.Lock() # スレッド間のデータ保護

        self.setup_ui()
        
        # 1. AI推論を専用のバックグラウンドスレッドで開始 (FPS向上の核)
        self.inference_thread = threading.Thread(target=self._inference_loop, daemon=True)
        self.inference_thread.start()
        
        # 2. UI/映像更新ループを開始
        self.update_loop()

    def setup_ui(self):
        # タイトル
        title_label = tk.Label(self.root, text="🔍 AI リアルタイム物体認識 (High-Performance)", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 統計
        stats_frame = tk.LabelFrame(self.left_panel, text=" 📊 検出オブジェクト ", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        self.lbl_counts = tk.Label(stats_frame, text="スキャン中...", bg=self.BG_WHITE, 
                                  font=("Meiryo", 11), fg=self.TEXT_COLOR, justify=tk.LEFT, padx=10, pady=15)
        self.lbl_counts.pack(fill=tk.X)

        # パフォーマンス
        fps_frame = tk.LabelFrame(self.left_panel, text=" ⚡ リアルタイムFPS ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        fps_frame.pack(fill=tk.X, pady=5)
        
        self.lbl_fps = tk.Label(fps_frame, text="FPS: 0.0", bg=self.BG_WHITE, 
                               font=("Impact", 24), fg=self.SAFE_COLOR, pady=10)
        self.lbl_fps.pack()

        # ログ
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 システムログ ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.write_log("非同期推論エンジンを起動しました。")

        # 撮影ボタン
        self.shot_btn = tk.Button(self.left_panel, text="画像を保存 📸 (S)", command=self.save_screenshot,
                                 bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 10, "bold"),
                                 relief=tk.FLAT, cursor="hand2", pady=10)
        self.shot_btn.pack(fill=tk.X, pady=5)

        guide_text = "【最適化内容】\n・推論を別スレッド化\n・入力解像度を320pxに調整\n・フレームスキップの防止"
        tk.Label(self.left_panel, text=guide_text, bg="#FFFBEB", justify=tk.LEFT, 
                 font=("Meiryo", 9), fg="#95A5A6").pack(side=tk.BOTTOM, pady=10)

        # --- 右側パネル ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ AIリアルタイム・モニター ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

        self.root.bind('<s>', lambda e: self.save_screenshot())
        self.root.bind('<q>', lambda e: self.on_closing())

    def write_log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def _inference_loop(self):
        """AI推論を行う独立したループ (UIスレッドを止めない)"""
        while self.is_running:
            frame_to_process = None
            with self.lock:
                if self.latest_frame is not None:
                    frame_to_process = self.latest_frame.copy()
            
            if frame_to_process is not None:
                # imgsz=320 で推論時間を半分以下に短縮
                results = self.model(frame_to_process, conf=0.45, verbose=False, imgsz=320, stream=True)
                
                for result in results:
                    annotated = result.plot()
                    
                    # カウント集計
                    class_counts = {}
                    if result.boxes:
                        for box in result.boxes:
                            cls_id = int(box.cls[0])
                            name = self.model.names[cls_id]
                            class_counts[name] = class_counts.get(name, 0) + 1
                    
                    count_text = ""
                    if not class_counts:
                        count_text = "対象が見つかりません"
                    else:
                        for name, count in class_counts.items():
                            count_text += f"・{name.capitalize()}: {count}\n"
                    
                    # 結果を共有変数に書き戻す
                    with self.lock:
                        self.annotated_frame = annotated
                        self.current_counts_text = count_text
            
            # CPU負荷を抑えるための微小なスリープ
            time.sleep(0.01)

    def update_loop(self):
        """表示を更新するメインスレッドのループ (表示FPSを維持)"""
        ret, frame = self.cap.read()
        if ret:
            # AI側に最新の生フレームを渡す
            with self.lock:
                self.latest_frame = frame
                # AIがまだ1枚も処理していない場合は生フレームを出す
                display_frame = self.annotated_frame if self.annotated_frame is not None else frame

            # FPS計算
            curr_time = time.time()
            self.fps = 1 / (curr_time - self.prev_time) if curr_time != self.prev_time else 0
            self.prev_time = curr_time
            self.lbl_fps.config(text=f"FPS: {self.fps:.1f}")
            self.lbl_counts.config(text=self.current_counts_text)

            # 表示
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
            # 描画自体は30ms(約33FPS)の間隔で予約
            self.root.after(20, self.update_loop)

    def save_screenshot(self):
        with self.lock:
            if self.annotated_frame is not None:
                filename = f"detection_fast_{int(time.time())}.jpg"
                cv2.imwrite(filename, self.annotated_frame)
                self.write_log(f"保存完了: {filename}")

    def on_closing(self):
        self.is_running = False
        time.sleep(0.1) # スレッド停止待ち
        self.cap.release()
        self.root.destroy()
        sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = ObjectDetectionApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()