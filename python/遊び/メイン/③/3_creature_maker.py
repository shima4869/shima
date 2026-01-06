# AI架空生物図鑑メーカー ✨
# インストール: pip install requests pillow pillowtk
# 実行方法: python 3_creature_maker.py
# Select Interpreter: Python 3.11.9

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import requests
import json
import threading
import io
import base64
import re
from PIL import Image, ImageTk

class CreatureGeneratorAI:
    """Gemini APIを使用して生物の生態生成と画像生成を行うエンジン"""
    def __init__(self):
        # APIキーは実行環境から自動供給
        self.api_key = "AIzaSyBzOeROpVGYEC1miK2ukPVeOdE0vEChv8Y" 
        self.text_model = "gemini-2.5-flash-preview-09-2025"
        self.image_model = "imagen-4.0-generate-001"

    def generate_info(self, query):
        """生物の名前や生態（JSON）を生成する"""
        prompt = (
            f"「{query}」という特徴を持つ、まだ誰も見たことがない架空の生物を1種類考えてください。\n"
            "以下の厳密なJSON形式のみで回答してください。挨拶は不要です。\n\n"
            "{\n"
            '  "name": "生物の和名（例：カザキリクジラ）",\n'
            '  "habitat": "生息地（例：高度1万メートルの雲海）",\n'
            '  "diet": "主食（例：雷雲の静電気）",\n'
            '  "description": "生態の詳細説明（200文字程度）",\n'
            '  "image_prompt": "この生物の姿をImagenで生成するための詳細な英語プロンプト"\n'
            "}"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.text_model}:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                res_text = response.json()['candidates'][0]['content']['parts'][0]['text']
                json_match = re.search(r'\{.*\}', res_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0)), None
            return None, f"テキスト生成エラー: {response.status_code}"
        except Exception as e:
            return None, str(e)

    def generate_image(self, image_prompt):
        """Imagen 4.0を使用して生物の画像を生成する"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.image_model}:predict?key={self.api_key}"
        # 高品質な生物イラスト用の追加指示
        full_prompt = f"A realistic biological illustration of a legendary creature: {image_prompt}. White background, detailed texture, scientific encyclopedia style."
        
        payload = {
            "instances": [{"prompt": full_prompt}],
            "parameters": {"sampleCount": 1}
        }

        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 200:
                result = response.json()
                base64_data = result['predictions'][0]['bytesBase64Encoded']
                img_data = base64.b64decode(base64_data)
                return Image.open(io.BytesIO(img_data)), None
            return None, f"画像生成エラー: {response.status_code}"
        except Exception as e:
            return None, str(e)

class CreatureMakerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI架空生物図鑑メーカー ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"

        self.ai = CreatureGeneratorAI()
        self.setup_ui()

    def setup_ui(self):
        # タイトル
        header = tk.Frame(self.root, bg="#FFFBEB")
        header.pack(pady=20)
        tk.Label(header, text="📖 AI架空生物図鑑", 
                 font=("Meiryo", 28, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR).pack()
        tk.Label(header, text="〜 想像を形にする、未来の博物誌 〜", 
                 font=("Meiryo", 10), bg="#FFFBEB", fg="#95A5A6").pack()

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=40, pady=10)
        
        self.main_container.columnconfigure(0, weight=1) # 左：情報
        self.main_container.columnconfigure(1, weight=1) # 右：画像
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：情報パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))

        # 1. 入力エリア
        input_frame = tk.LabelFrame(self.left_panel, text=" 🧬 発想の種を入力 ", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        input_frame.pack(fill=tk.X, pady=(0, 15))

        self.input_entry = tk.Entry(input_frame, font=("Meiryo", 14), relief=tk.FLAT)
        self.input_entry.pack(fill=tk.X, padx=15, pady=15)
        self.input_entry.insert(0, "雲を食べる光るクラゲ")
        self.input_entry.bind("<Return>", lambda e: self.start_creation())

        self.gen_btn = tk.Button(self.left_panel, text="新種を特定する 🔍", 
                                command=self.start_creation,
                                bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                relief=tk.FLAT, cursor="hand2", pady=15)
        self.gen_btn.pack(fill=tk.X, pady=(0, 20))

        # 2. 生成されたデータ表示
        data_frame = tk.LabelFrame(self.left_panel, text=" 📜 調査報告書 ", 
                                  font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                  fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        data_frame.pack(fill=tk.BOTH, expand=True)

        self.info_area = scrolledtext.ScrolledText(data_frame, font=("Meiryo", 11), 
                                                  bg=self.BG_WHITE, relief=tk.FLAT,
                                                  fg=self.TEXT_COLOR, state=tk.DISABLED,
                                                  padx=20, pady=20)
        self.info_area.pack(fill=tk.BOTH, expand=True)

        # --- 右側：ビジュアルパネル ---
        self.right_panel = tk.Frame(self.main_container, bg=self.BG_WHITE, relief=tk.RIDGE, bd=2)
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        self.img_canvas = tk.Canvas(self.right_panel, bg="#F9F9F9", highlightthickness=0)
        self.img_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.img_canvas.create_image(0, 0, anchor=tk.NW)

        # ローディング
        self.status_label = tk.Label(self.root, text="準備完了", bg="#FFFBEB", fg="#95A5A6", font=("Meiryo", 9))
        self.status_label.pack(pady=10)

    def start_creation(self):
        query = self.input_entry.get().strip()
        if not query: return
        
        self.gen_btn.config(state=tk.DISABLED, text="調査中...")
        self.status_label.config(text="✨ AIが新種の生態を解明しています...")
        self.info_area.config(state=tk.NORMAL)
        self.info_area.delete("1.0", tk.END)
        self.info_area.insert(tk.END, "新種を発見しました！\n現在、詳しい特徴を分析中です...")
        self.info_area.config(state=tk.DISABLED)
        
        threading.Thread(target=self.run_logic, args=(query,), daemon=True).start()

    def run_logic(self, query):
        # 1. テキスト生成
        info, err = self.ai.generate_info(query)
        if err:
            self.root.after(0, lambda: self.handle_error(err))
            return

        # 中間報告
        self.root.after(0, lambda: self.update_info(info))
        self.root.after(0, lambda: self.status_label.config(text="🎨 生物の姿を可視化しています..."))

        # 2. 画像生成
        img, img_err = self.ai.generate_image(info['image_prompt'])
        if img_err:
            self.root.after(0, lambda: self.handle_error(img_err))
            return

        self.root.after(0, lambda: self.display_creature(img))

    def update_info(self, info):
        self.info_area.config(state=tk.NORMAL)
        self.info_area.delete("1.0", tk.END)
        
        report = (
            f"【個体名】\n{info.get('name')}\n\n"
            f"【生息環境】\n{info.get('habitat')}\n\n"
            f"【食性】\n{info.get('diet')}\n\n"
            f"【生態的特徴】\n{info.get('description')}\n"
        )
        self.info_area.insert(tk.END, report)
        self.info_area.config(state=tk.DISABLED)

    def display_creature(self, pil_img):
        self.root.update_idletasks()
        cw = self.img_canvas.winfo_width()
        ch = self.img_canvas.winfo_height()
        
        # キャンバスにフィットさせる
        ratio = min(cw / pil_img.width, ch / pil_img.height)
        new_size = (int(pil_img.width * ratio), int(pil_img.height * ratio))
        disp_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
        
        self.tk_img = ImageTk.PhotoImage(disp_img)
        self.img_canvas.delete("all")
        self.img_canvas.create_image(cw//2, ch//2, anchor=tk.CENTER, image=self.tk_img)
        
        self.gen_btn.config(state=tk.NORMAL, text="新種を特定する 🔍")
        self.status_label.config(text="✅ 登録が完了しました！", fg="#2ECC71")

    def handle_error(self, msg):
        messagebox.showerror("観測エラー", f"情報の取得に失敗しました:\n{msg}")
        self.gen_btn.config(state=tk.NORMAL, text="新種を特定する 🔍")
        self.status_label.config(text="❌ エラーが発生しました", fg="red")

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    app = CreatureMakerApp(root)
    root.mainloop()