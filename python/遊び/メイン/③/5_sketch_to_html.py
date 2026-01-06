# AI手書きWebサイト変換機 ✨
# インストール: pip install tkinter requests pillow numpy opencv-python
# 実行方法: python 5_sketch_to_html.py
# Select Interpreter: Python 3.11.9

import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import requests
import json
import base64
import threading
import time
import os
import webbrowser
import tempfile

class SketchConverterAI:
    """Gemini AIを使用して手書き画像をHTMLコードに変換するエンジン"""
    def __init__(self):
        # APIキーは実行環境から自動供給
        self.api_key = "AIzaSyBzOeROpVGYEC1miK2ukPVeOdE0vEChv8Y" 
        self.model_id = "gemini-2.5-flash-preview-09-2025"

    def convert_sketch_to_html(self, base64_image):
        """手書きスケッチの画像を解析し、HTML/CSSを生成する"""
        prompt = (
            "提供された画像はWebサイトの手書きラフ画（ワイヤーフレーム）です。 "
            "このスケッチのレイアウト、テキスト、ボタン、ナビゲーション、画像配置を正確に解析し、 "
            "モダンでレスポンシブな単一ファイルのHTMLコード（CSSは内部スタイルシートとして含む）を作成してください。\n\n"
            "以下の条件を守ってください：\n"
            "1. デザインを美しくするため、Tailwind CSS（CDN経由）を使用してください。\n"
            "2. スケッチの文字が読み取れる場合は、そのテキストを反映させてください。\n"
            "3. 動作するボタンやナビゲーションの構造を含めてください。\n"
            "4. 回答は以下の厳密なJSON形式のみで返してください。説明文は不要です。\n\n"
            "{\n"
            '  "html": "<!DOCTYPE html>...（生成されたコード全体）..."\n'
            "}"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": "image/png", "data": base64_image}}
                ]
            }],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }

        # 指数バックオフによるリトライ処理
        for i in range(5):
            try:
                response = requests.post(url, json=payload, timeout=60)
                if response.status_code == 200:
                    data = response.json()
                    res_json = json.loads(data['candidates'][0]['content']['parts'][0]['text'])
                    return res_json.get("html", ""), None
                
                err_msg = response.json().get("error", {}).get("message", "Unknown error")
                if response.status_code not in [429, 500, 503]:
                    return None, f"APIエラー: {err_msg}"
            except Exception as e:
                if i == 4: return None, str(e)
            
            time.sleep(2 ** i)
            
        return None, "接続に失敗しました。"

class SketchToWebsiteApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI手書きWebサイト変換機 ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SUCCESS_COLOR = "#2ECC71"

        self.ai = SketchConverterAI()
        
        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.current_frame = None
        self.generated_code = ""
        
        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # タイトル
        header = tk.Frame(self.root, bg="#FFFBEB")
        header.pack(pady=15)
        tk.Label(header, text="🌐 AI手書きWebサイト変換機", 
                 font=("Meiryo", 28, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR).pack()

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=5)
        
        # 比率調整：左(操作)1, 右(コード/プレビュー)2
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=2)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：カメラ・操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 15))

        # カメラプレビュー
        cam_frame = tk.LabelFrame(self.left_panel, text=" 🖼️ スキャンエリア ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        cam_frame.pack(fill=tk.X, pady=(0, 10))

        self.canvas = tk.Canvas(cam_frame, width=400, height=300, bg="black", highlightthickness=0)
        self.canvas.pack(padx=10, pady=10)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

        # 実行ボタン
        self.gen_btn = tk.Button(self.left_panel, text="スキャンしてWebサイト生成 🚀", 
                                command=self.start_generation,
                                bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                relief=tk.FLAT, cursor="hand2", pady=15)
        self.gen_btn.pack(fill=tk.X, pady=10)

        self.browser_btn = tk.Button(self.left_panel, text="ブラウザでプレビュー 🌍", 
                                    command=self.open_in_browser,
                                    bg=self.SUCCESS_COLOR, fg="white", font=("Meiryo", 11, "bold"),
                                    relief=tk.FLAT, cursor="hand2", pady=12, state=tk.DISABLED)
        self.browser_btn.pack(fill=tk.X, pady=5)

        # ログ表示
        self.log_area = scrolledtext.ScrolledText(self.left_panel, font=("Meiryo", 8), height=10,
                                                 bg="#F7F7F7", relief=tk.FLAT)
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=10)
        self.write_log("システム準備完了。ノートのラフ画を映してください。")

        # --- 右側：コード表示パネル ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        code_frame = tk.LabelFrame(self.right_panel, text=" 📝 生成されたHTML/CSSコード ", 
                                  font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                  fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        code_frame.pack(fill=tk.BOTH, expand=True)

        self.code_area = scrolledtext.ScrolledText(code_frame, font=("Consolas", 10), 
                                                  bg="#2D2D2D", fg="#CCCCCC", relief=tk.FLAT,
                                                  insertbackground="white", padx=15, pady=15)
        self.code_area.pack(fill=tk.BOTH, expand=True)

    def write_log(self, msg):
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_area.see(tk.END)

    def start_generation(self):
        if self.current_frame is None: return
        
        self.gen_btn.config(state=tk.DISABLED, text="AI解析中...")
        self.write_log("画像をキャプチャし、AI解析に送信中...")
        
        # 現在のフレームをBase64に
        _, buffer = cv2.imencode('.png', self.current_frame)
        b64_img = base64.b64encode(buffer).decode('utf-8')
        
        threading.Thread(target=self.run_logic, args=(b64_img,), daemon=True).start()

    def run_logic(self, b64_img):
        html, err = self.ai.convert_sketch_to_html(b64_img)
        self.root.after(0, lambda: self.finish_generation(html, err))

    def finish_generation(self, html, err):
        self.gen_btn.config(state=tk.NORMAL, text="スキャンしてWebサイト生成 🚀")
        if err:
            messagebox.showerror("エラー", f"生成に失敗しました: {err}")
            self.write_log(f"エラー発生: {err}")
            return

        self.generated_code = html
        self.code_area.delete("1.0", tk.END)
        self.code_area.insert(tk.END, html)
        self.browser_btn.config(state=tk.NORMAL)
        self.write_log("コードの生成が完了しました！ブラウザで確認できます。")

    def open_in_browser(self):
        """生成されたコードを一時ファイルとして保存し、ブラウザで開く"""
        if not self.generated_code: return
        
        with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', encoding='utf-8') as f:
            f.write(self.generated_code)
            temp_path = f.name
        
        webbrowser.open(f'file://{temp_path}')
        self.write_log(f"プレビューを表示しました: {os.path.basename(temp_path)}")

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            # プレビュー表示用
            self.current_frame = frame.copy()
            
            # Canvasに合わせる
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 50 and ch > 50:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
                
                ratio = min(cw/pil_img.width, ch/pil_img.height)
                new_size = (int(pil_img.width*ratio), int(pil_img.height*ratio))
                pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
                
                self.tk_img = ImageTk.PhotoImage(pil_img)
                self.canvas.delete("all")
                self.canvas.create_image(cw//2, ch//2, anchor=tk.CENTER, image=self.tk_img)

        if self.is_running:
            self.root.after(30, self.update_loop)

    def on_closing(self):
        self.is_running = False
        self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = SketchToWebsiteApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()