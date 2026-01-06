# AI似顔絵ジェネレーター
# インストール: pip install torch torchvision opencv-python Pillow
# 実行方法: python 1_anime_face_gen.py
# Select Interpreter: Python 3.11.9

import cv2
import torch
import numpy as np
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk
import torchvision.transforms as transforms
import threading
import time
import os

class AnimeGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI似顔絵ジェネレーター ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー設定
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"

        # AIモデル設定
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.styles = {
            '0': (None, "オリジナル (Original)"),
            '1': ('face_paint_512_v1', "ジブリ風 (Ghibli)"),
            '2': ('face_paint_512_v2', "新海誠風 (Shinkai)"),
            '3': ('celeba_distill', "パプリカ風 (Paprika)")
        }
        
        self.current_style_key = '0'
        self.model = None
        self.model_name = None
        self.is_loading = False
        
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
        ])

        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.raw_frame = None
        self.processed_frame = None
        self.lock = threading.Lock()

        self.setup_ui()
        
        # 推論スレッド開始
        self.inference_thread = threading.Thread(target=self._inference_loop, daemon=True)
        self.inference_thread.start()
        
        # UI更新ループ
        self.update_ui_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🎨 AI似顔絵ジェネレーター", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：左(操作)1, 右(表示)4
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=4)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=300)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # スタイル選択フレーム
        style_frame = tk.LabelFrame(self.left_panel, text=" 🎭 スタイルを選択 ", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        style_frame.pack(fill=tk.X, pady=(0, 10))

        # スタイルボタンの生成
        self.style_buttons = {}
        for key, info in self.styles.items():
            btn = tk.Button(style_frame, text=info[1], 
                           command=lambda k=key: self.change_style(k),
                           bg="#F7F7F7", font=("Meiryo", 10), relief=tk.FLAT, 
                           pady=8, cursor="hand2")
            btn.pack(fill=tk.X, padx=10, pady=5)
            self.style_buttons[key] = btn
        
        self.update_button_highlight()

        # ステータス表示
        status_frame = tk.LabelFrame(self.left_panel, text=" 📊 ステータス ", 
                                    font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, pady=10)
        
        self.status_label = tk.Label(status_frame, text="準備完了", bg=self.BG_WHITE, 
                                    font=("Meiryo", 10), fg=self.TEXT_COLOR)
        self.status_label.pack(pady=10)

        # デバイス情報
        device_label = tk.Label(self.left_panel, text=f"処理デバイス: {self.device.upper()}", 
                               bg="#FFFBEB", fg="#95A5A6", font=("Meiryo", 9))
        device_label.pack(side=tk.BOTTOM, pady=10)

        # --- 右側：プレビューパネル ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ AIリアルタイム変換プレビュー ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def change_style(self, key):
        self.current_style_key = key
        self.update_button_highlight()
        self.status_label.config(text=f"スタイル変更: {self.styles[key][1]}")

    def update_button_highlight(self):
        for key, btn in self.style_buttons.items():
            if key == self.current_style_key:
                btn.config(bg=self.PRIMARY_COLOR, fg="white")
            else:
                btn.config(bg="#F7F7F7", fg=self.TEXT_COLOR)

    def _load_model_internal(self, model_name):
        if model_name == self.model_name:
            return
        try:
            self.is_loading = True
            self.root.after(0, lambda: self.status_label.config(text="✨ AIモデル読込中...", fg="blue"))
            
            self.model = torch.hub.load("bryandlee/animegan2-pytorch:main", "generator", pretrained=model_name).to(self.device)
            self.model.eval()
            self.model_name = model_name
            self.is_loading = False
            self.root.after(0, lambda: self.status_label.config(text="✅ 読込完了", fg="green"))
        except Exception as e:
            self.is_loading = False
            self.root.after(0, lambda: self.status_label.config(text=f"❌ エラー: {str(e)[:20]}", fg="red"))

    def _run_inference(self, frame):
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        
        # 速度重視で512px固定
        input_size = 512
        img_resized = img.resize((input_size, input_size), Image.BICUBIC)
        
        input_tensor = self.transform(img_resized).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            out = self.model(input_tensor)
            out = out.squeeze(0).cpu()
            out = (out * 0.5 + 0.5).clip(0, 1)
            
        out_img = transforms.ToPILImage()(out)
        # 表示サイズに合わせてリサイズ
        out_img = out_img.resize((frame.shape[1], frame.shape[0]), Image.BICUBIC)
        return cv2.cvtColor(np.array(out_img), cv2.COLOR_RGB2BGR)

    def _inference_loop(self):
        while self.is_running:
            target_frame = None
            style_key = None
            
            with self.lock:
                if self.raw_frame is not None:
                    target_frame = self.raw_frame.copy()
                    style_key = self.current_style_key
            
            if target_frame is not None:
                if style_key == '0':
                    res = target_frame
                else:
                    if self.model_name != self.styles[style_key][0]:
                        self._load_model_internal(self.styles[style_key][0])
                    
                    if self.model is not None and not self.is_loading:
                        res = self._run_inference(target_frame)
                    else:
                        res = target_frame
                
                with self.lock:
                    self.processed_frame = res
            
            time.sleep(0.01)

    def update_ui_loop(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            with self.lock:
                self.raw_frame = frame.copy()
                display_frame = self.processed_frame if self.processed_frame is not None else frame
            
            # Canvas描画
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 50 and ch > 50:
                # BGR -> RGB 変換
                rgb_img = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_img)
                
                # アスペクト比維持
                fw, fh = pil_img.size
                ratio = min(cw/fw, ch/fh)
                new_size = (int(fw*ratio), int(fh*ratio))
                pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
                
                self.tk_img = ImageTk.PhotoImage(pil_img)
                self.canvas.itemconfig(self.image_item, image=self.tk_img)
                self.canvas.coords(self.image_item, (cw-new_size[0])//2, (ch-new_size[1])//2)

        if self.is_running:
            self.root.after(30, self.update_ui_loop)

    def on_closing(self):
        self.is_running = False
        self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    # Windows高解像度対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = AnimeGeneratorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()