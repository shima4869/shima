# AIインテリアコーディネーター ✨
# インストール: pip install tkinter requests pillow numpy opencv-python
# 実行方法: python 4_interior_coordinator.py
# Select Interpreter: Python 3.11.9

import tkinter as tk
from tkinter import messagebox, filedialog, scrolledtext, ttk
import requests
import json
import threading
import io
import base64
import time
import os
import cv2
import numpy as np
from PIL import Image, ImageTk

class InteriorAI:
    """Gemini AIを使用してインテリアの提案と画像加工を行うエンジン"""
    def __init__(self):
        # APIキーは実行環境から自動供給されるため、UIからは削除
        self.api_key = "AIzaSyBzOeROpVGYEC1miK2ukPVeOdE0vEChv8Y"
        # 画像編集(Image-to-Image)に対応したプレビューモデル
        self.model_id = "gemini-2.5-flash-image-preview"

    def process_interior(self, image_base64, style, request_text):
        """画像とスタイルを元にAIに加工を依頼する"""
        prompt = (
            f"あなたはプロのインテリアコーディネーターです。提供された部屋の写真を分析し、"
            f"「{style}」のスタイルで、家具の配置やカーテン・壁紙の色を最適化した合成画像を1枚生成してください。\n"
            f"追加のリクエスト: {request_text}\n"
            "部屋の基本的な骨組み（窓の位置や壁の形）は維持しつつ、魅力的で住みたくなるような空間に仕上げてください。"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": "image/png", "data": image_base64}}
                ]
            }],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"]
            }
        }

        # 指数バックオフによるリトライ処理 (最大5回)
        for i in range(5):
            try:
                response = requests.post(url, json=payload, timeout=90)
                if response.status_code == 200:
                    data = response.json()
                    
                    # テキスト解説の抽出
                    explanation = data['candidates'][0]['content']['parts'][0]['text']
                    
                    # 生成画像の抽出
                    img_part = next((p for p in data['candidates'][0]['content']['parts'] if 'inlineData' in p), None)
                    if img_part:
                        img_data = base64.b64decode(img_part['inlineData']['data'])
                        return Image.open(io.BytesIO(img_data)), explanation, None
                    else:
                        return None, explanation, "画像が生成されませんでした。プロンプトを調整してください。"
                
                # エラー時の処理
                err_data = response.json()
                err_msg = err_data.get("error", {}).get("message", "Unknown error")
                if response.status_code not in [429, 500, 503]:
                    return None, None, f"APIエラー: {err_msg}"
                
            except Exception as e:
                if i == 4: return None, None, str(e)
            
            time.sleep(2 ** i)
            
        return None, None, "AIサーバーへの接続に失敗しました。"

class InteriorCoordinatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIインテリアコーディネーター ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数 (シリーズ統一)
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SUCCESS_COLOR = "#2ECC71"

        self.ai = InteriorAI()
        
        # 状態管理
        self.original_img = None 
        self.result_img = None   
        self.source_base64 = None
        
        self.setup_ui()

    def setup_ui(self):
        # メインタイトル
        header = tk.Frame(self.root, bg="#FFFBEB")
        header.pack(pady=15)
        tk.Label(header, text="🏠 AIインテリアコーディネーター", 
                 font=("Meiryo", 28, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR).pack()

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=40, pady=5)
        
        # 比率：左(操作)1, 右(プレビュー)2
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=2)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：設定・操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=400)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 1. 画像アップロード (一番上に配置)
        self.upload_btn = tk.Button(self.left_panel, text="部屋の写真をアップロード 📁", 
                                   command=self.load_image,
                                   bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 11, "bold"),
                                   relief=tk.FLAT, cursor="hand2", pady=15)
        self.upload_btn.pack(fill=tk.X, pady=(0, 15))

        # 2. スタイル選択
        style_frame = tk.LabelFrame(self.left_panel, text=" 🎭 スタイルの選択 ", 
                                   font=("Meiryo", 9, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        style_frame.pack(fill=tk.X, pady=10)
        self.style_combo = ttk.Combobox(style_frame, values=[
            "北欧風 (Scandinavian)", "和モダン (Japanese Modern)", "ミニマリスト (Minimalist)",
            "インダストリアル (Industrial)", "モダン (Modern)", "ナチュラル (Natural)"
        ], state="readonly", font=("Meiryo", 10))
        self.style_combo.set("北欧風 (Scandinavian)")
        self.style_combo.pack(fill=tk.X, padx=10, pady=15)

        # 3. 詳細リクエスト
        req_frame = tk.LabelFrame(self.left_panel, text=" 📝 追加のリクエスト ", 
                                 font=("Meiryo", 9, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        req_frame.pack(fill=tk.X, pady=10)
        self.req_entry = tk.Entry(req_frame, font=("Meiryo", 11), relief=tk.FLAT)
        self.req_entry.pack(fill=tk.X, padx=10, pady=15)
        self.req_entry.insert(0, "青色のクッションを追加して")

        # 4. 実行ボタン
        self.gen_btn = tk.Button(self.left_panel, text="コーディネートを開始 🚀", 
                                command=self.start_generation,
                                bg=self.SUCCESS_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                relief=tk.FLAT, cursor="hand2", pady=18)
        self.gen_btn.pack(fill=tk.X, pady=20)

        # 5. AIアドバイス表示
        self.info_area = scrolledtext.ScrolledText(self.left_panel, font=("Meiryo", 9), height=10,
                                                  bg=self.BG_WHITE, relief=tk.FLAT, fg=self.TEXT_COLOR)
        self.info_area.pack(fill=tk.BOTH, expand=True, pady=10)
        self.write_info("写真を読み込んで、スタイルを選んでください。")

        # --- 右側：プレビューパネル ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        # タブ切り替え
        self.tabs = ttk.Notebook(self.right_panel)
        self.tabs.pack(fill=tk.BOTH, expand=True)

        self.tab_orig = tk.Frame(self.tabs, bg="#1A1A1A")
        self.tab_res = tk.Frame(self.tabs, bg="#1A1A1A")
        self.tabs.add(self.tab_orig, text="   元の写真   ")
        self.tabs.add(self.tab_res, text=" ✨ AI提案イメージ ")

        self.canvas_orig = tk.Canvas(self.tab_orig, bg="#1A1A1A", highlightthickness=0)
        self.canvas_orig.pack(fill=tk.BOTH, expand=True)
        self.canvas_res = tk.Canvas(self.tab_res, bg="#1A1A1A", highlightthickness=0)
        self.canvas_res.pack(fill=tk.BOTH, expand=True)

        self.status_label = tk.Label(self.root, text="準備完了", bg="#FFFBEB", fg="#95A5A6", font=("Meiryo", 9))
        self.status_label.pack(pady=10)

    def write_info(self, msg):
        self.info_area.config(state=tk.NORMAL)
        self.info_area.delete("1.0", tk.END)
        self.info_area.insert(tk.END, f"【AIからの提案】\n{msg}")
        self.info_area.config(state=tk.DISABLED)

    def load_image(self):
        """画像ファイルを読み込んでプレビューを表示"""
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")])
        if path:
            try:
                self.original_img = Image.open(path)
                # ファイルから読み込む際、EXIF情報に基づいて回転を補正
                try:
                    from PIL import ImageOps
                    self.original_img = ImageOps.exif_transpose(self.original_img)
                except: pass
                
                with open(path, "rb") as f:
                    self.source_base64 = base64.b64encode(f.read()).decode('utf-8')
                
                self.update_preview(self.canvas_orig, self.original_img)
                self.tabs.select(0)
                self.status_label.config(text=f"読込完了: {os.path.basename(path)}")
            except Exception as e:
                messagebox.showerror("エラー", f"画像の読み込みに失敗しました: {e}")

    def update_preview(self, canvas, pil_img):
        """Canvasに画像をフィットさせて描画"""
        canvas.delete("all")
        self.root.update_idletasks()
        cw, ch = canvas.winfo_width(), canvas.winfo_height()
        if cw < 50 or ch < 50: return

        ratio = min(cw / pil_img.width, ch / pil_img.height)
        new_size = (int(pil_img.width * ratio), int(pil_img.height * ratio))
        disp_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
        
        tk_img = ImageTk.PhotoImage(disp_img)
        if canvas == self.canvas_orig: self.tk_orig = tk_img
        else: self.tk_res = tk_img
        
        canvas.create_image(cw//2, ch//2, anchor=tk.CENTER, image=tk_img)

    def start_generation(self):
        """生成スレッドの開始"""
        if not self.source_base64:
            messagebox.showwarning("画像不足", "写真をアップロードしてください。")
            return

        self.gen_btn.config(state=tk.DISABLED, text="AIがデザイン中...")
        self.status_label.config(text="✨ AIが最適な家具と配色をシミュレーションしています...", fg=self.PRIMARY_COLOR)
        
        threading.Thread(target=self.run_logic, daemon=True).start()

    def run_logic(self):
        """AI処理の実行ロジック"""
        style = self.style_combo.get()
        req = self.req_entry.get()
        
        img, explanation, err = self.ai.process_interior(self.source_base64, style, req)
        
        if err:
            self.root.after(0, lambda: self.handle_error(err))
            return

        self.result_img = img
        self.root.after(0, lambda: self.finish_generation(explanation))

    def finish_generation(self, explanation):
        """結果を画面に表示"""
        self.update_preview(self.canvas_res, self.result_img)
        self.tabs.select(1)
        self.write_info(explanation)
        
        self.gen_btn.config(state=tk.NORMAL, text="コーディネートを開始 🚀")
        self.status_label.config(text="✅ コーディネート完了！", fg=self.SUCCESS_COLOR)

    def handle_error(self, msg):
        messagebox.showerror("生成失敗", f"処理中にエラーが発生しました:\n{msg}")
        self.gen_btn.config(state=tk.NORMAL, text="コーディネートを開始 🚀")
        self.status_label.config(text="❌ エラーが発生しました", fg="red")

if __name__ == "__main__":
    root = tk.Tk()
    # Windows高DPIディスプレイ対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = InteriorCoordinatorApp(root)
    root.mainloop()