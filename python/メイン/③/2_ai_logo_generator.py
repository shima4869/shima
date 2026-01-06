# AIロゴデザイン自動生成機 ✨
# インストール: pip install requests pillow
# 実行方法: python 2_ai_logo_generator.py
# Select Interpreter: Python 3.11.9

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk, filedialog
import requests
import json
import threading
import time
import os
import re
from PIL import Image, ImageDraw, ImageFont, ImageTk

class LogoGeneratorAI:
    """Gemini APIを使用してロゴのデザインコンセプトを生成するエンジン"""
    def __init__(self):
        # APIキーは環境から自動供給
        self.api_key = "AIzaSyBzOeROpVGYEC1miK2ukPVeOdE0vEChv8Y" 
        self.model_id = "gemini-2.5-flash-preview-09-2025"

    def get_design_concept(self, brand_name, description):
        """ブランド名と概要からデザイン案（JSON）を取得する"""
        prompt = (
            f"ブランド名: 「{brand_name}」\n"
            f"サービス内容: 「{description}」\n\n"
            "この情報に基づき、プロのデザイナーとしてロゴデザインを設計してください。"
            "以下の厳密なJSON形式のみで回答してください。説明文は一切不要です。\n\n"
            "{\n"
            '  "bg_color": "#Hex値",\n'
            '  "text_color": "#Hex値",\n'
            '  "accent_color": "#Hex値",\n'
            '  "font_type": "serif" または "sans-serif" または "gothic",\n'
            '  "layout": "vertical" または "horizontal",\n'
            '  "icon_shape": "circle" または "square" または "triangle" または "diamond",\n'
            '  "concept": "デザインに込めた想いを1文で"\n'
            "}"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        # 指数バックオフによるリトライ処理
        for i in range(5):
            try:
                response = requests.post(url, json=payload, timeout=30)
                if response.status_code == 200:
                    res_text = response.json()['candidates'][0]['content']['parts'][0]['text']
                    json_match = re.search(r'\{.*\}', res_text, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group(0)), None
                time.sleep(2**i)
            except:
                pass
        return None, "AIとの通信に失敗しました。"

class LogoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIロゴデザイン自動生成機 ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SUCCESS_COLOR = "#2ECC71"

        self.ai = LogoGeneratorAI()
        self.generated_img = None
        
        self.setup_ui()

    def setup_ui(self):
        # タイトル
        tk.Label(self.root, text="🎨 AIロゴデザイン自動生成機", 
                 font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR).pack(pady=20)

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：設定パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 入力エリア
        input_frame = tk.LabelFrame(self.left_panel, text=" 📖 STEP 1: ブランド情報 ", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        input_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(input_frame, text="会社名 / ブランド名:", bg=self.BG_WHITE, font=("Meiryo", 9)).pack(anchor="w", padx=15, pady=(10, 0))
        self.name_entry = tk.Entry(input_frame, font=("Meiryo", 12), relief=tk.SOLID, bd=1)
        self.name_entry.pack(fill=tk.X, padx=15, pady=10)
        self.name_entry.insert(0, "Next Dimension")

        tk.Label(input_frame, text="サービス概要 / 想い:", bg=self.BG_WHITE, font=("Meiryo", 9)).pack(anchor="w", padx=15, pady=(5, 0))
        self.desc_entry = tk.Entry(input_frame, font=("Meiryo", 12), relief=tk.SOLID, bd=1)
        self.desc_entry.pack(fill=tk.X, padx=15, pady=10)
        self.desc_entry.insert(0, "未来を創るITスタートアップ")

        # ボタン類
        self.gen_btn = tk.Button(self.left_panel, text="ロゴをデザインする 🚀", 
                                command=self.start_generation,
                                bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                relief=tk.FLAT, cursor="hand2", pady=15)
        self.gen_btn.pack(fill=tk.X, pady=10)

        self.save_btn = tk.Button(self.left_panel, text="高画質で保存する 💾", 
                                 command=self.save_logo,
                                 bg="#BDC3C7", fg="white", font=("Meiryo", 11, "bold"),
                                 relief=tk.FLAT, cursor="hand2", pady=12, state=tk.DISABLED)
        self.save_btn.pack(fill=tk.X, pady=5)

        # AIの解説
        self.info_frame = tk.LabelFrame(self.left_panel, text=" 🧠 AIデザイン解説 ", 
                                       font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                       fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        self.info_frame.pack(fill=tk.BOTH, expand=True, pady=15)
        
        self.concept_text = tk.Label(self.info_frame, text="ブランド名を入力して\n生成ボタンを押してください。", 
                                     bg=self.BG_WHITE, font=("Meiryo", 10), wraplength=320, justify=tk.LEFT)
        self.concept_text.pack(padx=15, pady=20)

        # --- 右側：プレビューパネル ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ ロゴ・キャンバス ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="#F0F0F0", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def start_generation(self):
        brand = self.name_entry.get().strip()
        desc = self.desc_entry.get().strip()
        if not brand:
            messagebox.showwarning("入力不足", "ブランド名を入力してください。")
            return
        
        self.gen_btn.config(state=tk.DISABLED, text="AIがデザイン中...")
        threading.Thread(target=self.run_logic, args=(brand, desc), daemon=True).start()

    def run_logic(self, brand, desc):
        design, error = self.ai.get_design_concept(brand, desc)
        self.root.after(0, lambda: self.finish_generation(design, error, brand))

    def finish_generation(self, design, error, brand):
        self.gen_btn.config(state=tk.NORMAL, text="ロゴをデザインする 🚀")
        if error:
            messagebox.showerror("失敗", error)
            return

        self.concept_text.config(text=f"【コンセプト】\n{design.get('concept')}\n\n【カラー】\nBG: {design.get('bg_color')}\nAccent: {design.get('accent_color')}")
        
        # ロゴ画像の描画
        self.generated_img = self.draw_logo(brand, design)
        self.update_preview()
        
        self.save_btn.config(state=tk.NORMAL, bg=self.SUCCESS_COLOR)

    def draw_logo(self, text, design):
        """AIのパラメータに基づいて実際に画像を作成する"""
        size = 1000
        img = Image.new("RGB", (size, size), design.get("bg_color", "#FFFFFF"))
        draw = ImageDraw.Draw(img)
        
        accent = design.get("accent_color", "#FF0000")
        text_color = design.get("text_color", "#000000")
        shape = design.get("icon_shape", "circle")
        
        # 1. アイコンの描画
        icon_size = 300
        cx, cy = size // 2, size // 2 - 100
        
        if shape == "circle":
            draw.ellipse([cx - icon_size//2, cy - icon_size//2, cx + icon_size//2, cy + icon_size//2], fill=accent)
        elif shape == "square":
            draw.rectangle([cx - icon_size//2, cy - icon_size//2, cx + icon_size//2, cy + icon_size//2], fill=accent)
        elif shape == "triangle":
            draw.polygon([(cx, cy - icon_size//2), (cx - icon_size//2, cy + icon_size//2), (cx + icon_size//2, cy + icon_size//2)], fill=accent)
        elif shape == "diamond":
            draw.polygon([(cx, cy - icon_size//2), (cx + icon_size//2, cy), (cx, cy + icon_size//2), (cx - icon_size//2, cy)], fill=accent)

        # 2. フォントの読み込み
        font_path = "C:/Windows/Fonts/meiryo.ttc" # Windows標準
        if not os.path.exists(font_path):
            font_path = "/System/Library/Fonts/Helvetica.ttcl" # Fallback
            
        try:
            font = ImageFont.truetype(font_path, 80)
        except:
            font = ImageFont.load_default()

        # 3. テキストの配置
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((size - tw) // 2, cy + icon_size//2 + 50), text, fill=text_color, font=font)
        
        return img

    def update_preview(self):
        if not self.generated_img: return
        
        self.root.update_idletasks()
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        
        # キャンバスにフィットするようにリサイズ
        ratio = min(cw / 1000, ch / 1000)
        new_size = (int(1000 * ratio), int(1000 * ratio))
        disp_img = self.generated_img.resize(new_size, Image.Resampling.LANCZOS)
        
        self.tk_img = ImageTk.PhotoImage(disp_img)
        self.canvas.delete("all")
        self.canvas.create_image(cw//2, ch//2, anchor=tk.CENTER, image=self.tk_img)

    def save_logo(self):
        if not self.generated_img: return
        path = filedialog.asksaveasfilename(defaultextension=".png", 
                                            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg")])
        if path:
            self.generated_img.save(path)
            messagebox.showinfo("成功", "ロゴを保存しました！")

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    app = LogoApp(root)
    root.mainloop()