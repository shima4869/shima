# AI要約マンガ生成機
# インストール: pip install Pillow
# 実行方法: python 3_manga_generator.py
# Select Interpreter: Python 3.11.9

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk, filedialog
from PIL import Image, ImageDraw, ImageFont, ImageTk
import os
import textwrap

class MangaGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI要約マンガ生成機 ✨")
        self.root.geometry("1400x850") # 全体幅
        self.root.configure(bg="#FFFBEB")  # 温かみのあるクリーム色

        # アプリ全体で使用する定数
        self.PRIMARY_COLOR = "#FF9F43"     # 元気なオレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # 明るいイエロー
        self.SUCCESS_COLOR = "#2ECC71"     # 保存用の緑
        self.TEXT_COLOR = "#4B4B4B"        # 柔らかい黒
        self.BG_WHITE = "#FFFFFF"
        
        # 生成された画像を保持する変数
        self.current_manga_img = None
        
        self.setup_ui()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🎨 AI要約マンガ生成機", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        # メインコンテナ
        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：左(入力)を1、右(プレビュー)を12に設定
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=12)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル (STEP 1) ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))

        input_frame = tk.LabelFrame(self.left_panel, text=" 📖 STEP 1: 入力 ", 
                                   font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        input_frame.pack(fill=tk.X, expand=False, pady=(0, 10))

        self.text_input = scrolledtext.ScrolledText(input_frame, font=("Meiryo", 10), height=20,
                                                   width=30, relief=tk.FLAT, padx=8, pady=8, wrap=tk.WORD)
        self.text_input.pack(fill=tk.X, padx=5, pady=5)

        # 生成ボタン
        self.generate_btn = tk.Button(self.left_panel, text="マンガ生成 🚀", 
                                     command=self.generate_manga, 
                                     bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 12, "bold"), 
                                     relief=tk.FLAT, cursor="hand2", pady=12, activebackground=self.SECONDARY_COLOR)
        self.generate_btn.pack(fill=tk.X, pady=(10, 5))

        # 保存ボタン (初期状態は少し薄い色)
        self.save_btn = tk.Button(self.left_panel, text="画像として保存 💾", 
                                 command=self.save_manga, 
                                 bg="#BDC3C7", fg="white", font=("Meiryo", 11, "bold"), 
                                 relief=tk.FLAT, cursor="hand2", pady=10, state=tk.DISABLED)
        self.save_btn.pack(fill=tk.X, pady=5)

        # ステータス表示
        self.status_label = tk.Label(self.left_panel, text="文章を入れてね", 
                                    bg="#FFFBEB", fg=self.TEXT_COLOR, font=("Meiryo", 9))
        self.status_label.pack(pady=(5, 10))

        # --- 右側：プレビューパネル (STEP 2) ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ STEP 2: 完成プレビュー ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        # キャンバス
        self.canvas = tk.Canvas(preview_frame, bg="#F7F7F7", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def summarize_text(self, text):
        """文章を4つのパートに要約・分割"""
        sentences = [s.strip() for s in text.replace('。', '。\n').split('\n') if s.strip()]
        
        if len(sentences) < 4:
            while len(sentences) < 4:
                sentences.append("……つづく。")
            return sentences[:4]
        
        chunk_size = max(1, len(sentences) // 4)
        summary = [
            sentences[0],
            sentences[chunk_size],
            sentences[chunk_size * 2],
            sentences[-1]
        ]
        return summary

    def get_font(self, size):
        """システムに存在するフォントを安全に取得"""
        font_paths = [
            "C:\\Windows\\Fonts\\msgothic.ttc",
            "C:\\Windows\\Fonts\\msjh.ttc",
            "/System/Library/Fonts/jpn/ヒラギノ角ゴ ProN.ttc",
            "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
        ]
        for path in font_paths:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        return ImageFont.load_default()

    def create_manga_image(self, summary_texts):
        """2x2のグリッド配置でマンガ画像を生成"""
        panel_w = 480
        panel_h = 320
        margin = 15
        total_w = (panel_w + margin) * 2 + margin
        total_h = (panel_h + margin) * 2 + margin
        
        img = Image.new('RGB', (total_w, total_h), color=self.BG_WHITE)
        draw = ImageDraw.Draw(img)
        
        font_main = self.get_font(18)
        font_label = self.get_font(28)

        colors = ["#FFF0F0", "#F0F7FF", "#F0FFF0", "#FFFFF0"]
        labels = ["起", "承", "転", "結"]

        for i, text in enumerate(summary_texts):
            col = i % 2
            row = i // 2
            
            left = margin + col * (panel_w + margin)
            top = margin + row * (panel_h + margin)
            right = left + panel_w
            bottom = top + panel_h
            
            draw.rectangle([left, top, right, bottom], outline="#333333", fill=colors[i], width=3)
            
            center_x = left + (panel_w // 2)
            circle_r = 50
            draw.ellipse([center_x - circle_r, top + 30, center_x + circle_r, top + 130], 
                         fill=self.BG_WHITE, outline=self.PRIMARY_COLOR, width=2)
            
            draw.text((center_x - 14, top + 65), labels[i], fill=self.PRIMARY_COLOR, font=font_label)

            wrapped_lines = textwrap.wrap(text, width=22)
            display_text = "\n".join(wrapped_lines[:4])
            if len(wrapped_lines) > 4:
                display_text += "..."

            draw.text((left + 30, top + 160), display_text, fill=self.TEXT_COLOR, font=font_main)

        return img

    def generate_manga(self):
        input_text = self.text_input.get("1.0", tk.END).strip()
        
        if not input_text:
            messagebox.showwarning("入力エラー", "文章を入力してね。")
            return

        try:
            self.status_label.config(text="✨ 生成中...", fg=self.PRIMARY_COLOR)
            self.root.update()

            summary = self.summarize_text(input_text)
            self.current_manga_img = self.create_manga_image(summary)
            
            # プレビュー表示
            self.root.update_idletasks()
            canvas_w = self.canvas.winfo_width()
            canvas_h = self.canvas.winfo_height()
            
            img_w, img_h = self.current_manga_img.size
            ratio = min(canvas_w / img_w, canvas_h / img_h)
            new_size = (int(img_w * ratio), int(img_h * ratio))
            manga_display_img = self.current_manga_img.resize(new_size, Image.Resampling.LANCZOS)

            self.photo_img = ImageTk.PhotoImage(manga_display_img)
            self.canvas.itemconfig(self.image_item, image=self.photo_img)
            self.canvas.coords(self.image_item, (canvas_w - new_size[0]) // 2, (canvas_h - new_size[1]) // 2)

            # 保存ボタンを有効化
            self.save_btn.config(state=tk.NORMAL, bg=self.SUCCESS_COLOR)
            self.status_label.config(text=f"✅ 完成！保存できるよ", fg="green")

        except Exception as e:
            messagebox.showerror("エラー", f"エラーが発生しました:\n{str(e)}")
            self.status_label.config(text="❌ 失敗", fg="red")

    def save_manga(self):
        """生成された画像をファイルに保存"""
        if self.current_manga_img is None:
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg"), ("All Files", "*.*")],
            initialfile="summary_manga.png",
            title="マンガを保存する"
        )
        
        if file_path:
            try:
                self.current_manga_img.save(file_path)
                messagebox.showinfo("保存完了", f"画像を保存しました！\n{file_path}")
                self.status_label.config(text="💾 保存しました", fg="green")
            except Exception as e:
                messagebox.showerror("保存エラー", f"保存中にエラーが発生しました:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = MangaGeneratorApp(root)
    root.mainloop()