# 冷蔵庫の残り物レシピ提案AI
# インストール: pip install opencv-python Pillow requests
# 実行方法: python 8_fridge_recipe.py
# Select Interpreter: Python 3.11.9

import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox, filedialog, scrolledtext
from PIL import Image, ImageDraw, ImageFont, ImageTk
import requests
import json
import base64
import threading
import time
import os

class FridgeRecipeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("冷蔵庫の残り物レシピ提案AI ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB") # クリーム色の背景

        # 設定
        self.DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1444232363637997659/c9oDNYEjj1dqTTGHaVzs4zCQMiH0ulc7hDAONZVHgH-rv_mB9ImpAKZLAF-NhJWe9i5x"
        self.API_KEY = "AIzaSyBAgdEsFt7bc5GmGb-n-gp3cLYXFo3R5_U" # 実行環境から自動提供されます
        self.MODEL_ID = "gemini-2.5-flash-preview-09-2025"
        
        # カラー設定
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.SUCCESS_COLOR = "#2ECC71"     # 緑
        self.ALERT_COLOR = "#E74C3C"       # 赤
        self.TEXT_COLOR = "#4B4B4B"
        self.BG_WHITE = "#FFFFFF"

        # 状態管理
        self.cap = cv2.VideoCapture(0)
        self.current_frame = None      # 現在保持している画像（分析対象）
        self.is_analyzing = False      # 分析中フラグ
        self.source_mode = "camera"    # "camera" or "file"
        self.last_recipe = ""          # 最後に生成されたレシピ

        self.setup_ui()
        
        # カメラのスレッド
        self.thread = threading.Thread(target=self.video_loop, daemon=True)
        self.thread.start()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🍳 冷蔵庫の残り物レシピ提案AI", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率：左(操作)1, 右(表示)3
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))

        # モード選択フレーム
        mode_frame = tk.LabelFrame(self.left_panel, text=" 🕹️ 読み取り方法の選択 ", 
                                  font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                  fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        mode_frame.pack(fill=tk.X, pady=(0, 10))

        # カメラモード切替
        self.cam_mode_btn = tk.Button(mode_frame, text="カメラ映像を使う 📷", command=self.set_camera_mode,
                                     bg=self.SECONDARY_COLOR, fg=self.TEXT_COLOR, font=("Meiryo", 10, "bold"),
                                     relief=tk.FLAT, cursor="hand2", pady=10)
        self.cam_mode_btn.pack(fill=tk.X, padx=10, pady=(10, 5))

        # ファイルモード切替
        self.file_mode_btn = tk.Button(mode_frame, text="画像ファイルを選択 📁", command=self.set_file_mode,
                                      bg="#ECF0F1", fg=self.TEXT_COLOR, font=("Meiryo", 10, "bold"),
                                      relief=tk.FLAT, cursor="hand2", pady=10)
        self.file_mode_btn.pack(fill=tk.X, padx=10, pady=(5, 10))

        # 分析実行ボタン
        self.scan_btn = tk.Button(self.left_panel, text="この中身でレシピ提案！ 🔍", 
                                 command=self.start_analysis, 
                                 bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 12, "bold"), 
                                 relief=tk.FLAT, cursor="hand2", pady=20)
        self.scan_btn.pack(fill=tk.X, pady=20)

        # Discord送信ボタン
        self.discord_btn = tk.Button(self.left_panel, text="Discordに送る 💬", 
                                    command=self.send_to_discord, 
                                    bg="#BDC3C7", fg="white", font=("Meiryo", 11, "bold"), 
                                    relief=tk.FLAT, cursor="hand2", pady=12, state=tk.DISABLED)
        self.discord_btn.pack(fill=tk.X, pady=10)

        # ステータス
        self.status_label = tk.Label(self.left_panel, text="現在のモード: カメラ映像", 
                                    bg="#FFFBEB", fg=self.TEXT_COLOR, font=("Meiryo", 10, "bold"))
        self.status_label.pack(pady=10)

        # --- 右側：プレビュー＆結果エリア ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")
        self.right_panel.rowconfigure(0, weight=1) # 映像/画像
        self.right_panel.rowconfigure(1, weight=1) # レシピ

        # プレビュー
        cam_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ 冷蔵庫の様子 ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        cam_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        
        self.canvas = tk.Canvas(cam_frame, bg="#333", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

        # レシピ出力
        recipe_frame = tk.LabelFrame(self.right_panel, text=" 📜 AI提案レシピ ", 
                                    font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        recipe_frame.grid(row=1, column=0, sticky="nsew")

        self.recipe_area = scrolledtext.ScrolledText(recipe_frame, font=("Meiryo", 11), 
                                                    bg=self.BG_WHITE, relief=tk.FLAT, padx=15, pady=15)
        self.recipe_area.pack(fill=tk.BOTH, expand=True)

    def set_camera_mode(self):
        """カメラモードに切り替え"""
        self.source_mode = "camera"
        self.status_label.config(text="現在のモード: カメラ映像 🎥", fg="#34495E")
        self.cam_mode_btn.config(bg=self.SECONDARY_COLOR)
        self.file_mode_btn.config(bg="#ECF0F1")
        self.recipe_area.insert(tk.END, "\nカメラモードに切り替えました。")

    def set_file_mode(self):
        """ファイルモードに切り替え（ダイアログを表示）"""
        path = filedialog.askopenfilename(filetypes=[("画像ファイル", "*.jpg *.jpeg *.png *.bmp")])
        if path:
            img = cv2.imread(path)
            if img is not None:
                self.source_mode = "file"
                self.current_frame = img
                self.update_canvas(img)
                self.status_label.config(text="現在のモード: 画像ファイル 🖼️", fg="#34495E")
                self.file_mode_btn.config(bg=self.SECONDARY_COLOR)
                self.cam_mode_btn.config(bg="#ECF0F1")
                self.recipe_area.insert(tk.END, f"\n画像を読み込みました: {os.path.basename(path)}")
        else:
            # キャンセルした場合はカメラモードを維持
            pass

    def update_canvas(self, cv_img):
        """OpenCV画像をCanvasにフィットさせて表示"""
        if cv_img is None: return
        
        self.root.update_idletasks()
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw < 50 or ch < 50: return

        h, w = cv_img.shape[:2]
        ratio = min(cw/w, ch/h)
        new_size = (int(w*ratio), int(h*ratio))
        
        rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img).resize(new_size, Image.Resampling.LANCZOS)
        self.tk_img = ImageTk.PhotoImage(pil_img)
        
        self.canvas.itemconfig(self.image_item, image=self.tk_img)
        self.canvas.coords(self.image_item, (cw-new_size[0])//2, (ch-new_size[1])//2)

    def video_loop(self):
        """カメラのリアルタイム更新ループ"""
        while True:
            # 分析中でなく、かつカメラモードの場合のみ更新
            if not self.is_analyzing and self.source_mode == "camera":
                ret, frame = self.cap.read()
                if ret:
                    self.current_frame = frame
                    self.root.after(0, lambda f=frame: self.update_canvas(f))
            time.sleep(0.03)

    def start_analysis(self):
        """分析開始（非同期処理）"""
        if self.current_frame is None:
            messagebox.showwarning("エラー", "解析する画像がありません。カメラを起動するかファイルを選んでください。")
            return
            
        self.is_analyzing = True
        self.scan_btn.config(state=tk.DISABLED, text="AIが食材をスキャン中... 🤔", bg="#BDC3C7")
        self.recipe_area.delete("1.0", tk.END)
        self.recipe_area.insert(tk.END, "✨ 冷蔵庫の中身を分析して、最高のレシピを考えています...\n")
        
        threading.Thread(target=self.analyze_fridge, daemon=True).start()

    def analyze_fridge(self):
        """Gemini APIを呼び出して画像を分析"""
        try:
            # 画像をBase64文字列にエンコード
            _, buffer = cv2.imencode('.png', self.current_frame)
            base64_image = base64.b64encode(buffer).decode('utf-8')

            prompt = (
                "画像に写っている冷蔵庫の中身（食材）をすべて正確にリストアップしてください。"
                "そのあと、それらの食材（＋一般的な家庭にある基本調味料）だけを使って作れる、"
                "実用的で美味しいレシピを1つ提案してください。"
                "出力は以下の形式にしてください：\n"
                "1. 【認識した食材】（箇条書き）\n"
                "2. 【レシピ名】\n"
                "3. 【材料】\n"
                "4. 【作り方の手順】"
            )
            
            result = self.call_gemini_with_image(prompt, base64_image)
            self.root.after(0, lambda: self.finish_analysis(result))
            
        except Exception as e:
            self.root.after(0, lambda: self.finish_analysis(f"エラーが発生しました: {str(e)}"))

    def call_gemini_with_image(self, prompt, base64_data):
        """Gemini API呼び出し（リトライ処理付き）"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.MODEL_ID}:generateContent?key={self.API_KEY}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": "image/png", "data": base64_data}}
                ]
            }]
        }
        
        # 指数バックオフによるリトライ（最大5回）
        for i in range(5):
            try:
                response = requests.post(url, json=payload, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    return data['candidates'][0]['content']['parts'][0]['text']
            except:
                pass
            time.sleep(2**i)
            
        return "申し訳ありません。サーバーとの通信に失敗しました。時間をおいて再度お試しください。"

    def finish_analysis(self, result):
        """分析完了時の処理"""
        self.last_recipe = result
        self.recipe_area.delete("1.0", tk.END)
        self.recipe_area.insert(tk.END, result)
        
        self.scan_btn.config(state=tk.NORMAL, text="この中身でレシピ提案！ 🔍", bg=self.PRIMARY_COLOR)
        self.discord_btn.config(state=tk.NORMAL, bg=self.SUCCESS_COLOR)
        self.status_label.config(text="✨ レシピの生成が完了しました！", fg=self.SUCCESS_COLOR)
        self.is_analyzing = False

    def send_to_discord(self):
        """生成されたレシピをDiscordへ送信"""
        if not self.last_recipe: return
        
        # Discordの文字数制限（2000文字）に配慮
        content = f"🍳 **【AI提案】冷蔵庫の残り物レシピ**\n\n{self.last_recipe}"
        if len(content) > 1950:
            content = content[:1950] + "\n...(以下略)"

        payload = {"content": content}
        try:
            res = requests.post(self.DISCORD_WEBHOOK_URL, json=payload)
            if res.status_code == 204:
                messagebox.showinfo("送信完了", "Discordにレシピを送信しました！📱")
            else:
                messagebox.showerror("エラー", f"Discord送信に失敗しました (Code: {res.status_code})")
        except Exception as e:
            messagebox.showerror("送信エラー", f"接続に失敗しました: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    # Windows高DPI対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = FridgeRecipeApp(root)
    # 終了時にカメラを解放
    def on_closing():
        app.cap.release()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    root.mainloop()