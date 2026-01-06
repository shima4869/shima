# AI野鳥・昆虫判定機 ✨
# インストール: pip install tkinter requests pillow pyaudio
# 実行方法: python 12_wildlife_identifier_ai.py
# Select Interpreter: Python 3.11.9

import tkinter as tk
from tkinter import messagebox, filedialog, scrolledtext, ttk
import requests
import json
import base64
import threading
import time
import os
import io
import pyaudio
import numpy as np
from PIL import Image, ImageTk
import wave

# --- 音声設定 ---
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 5

class WildlifeAI:
    """Gemini APIを使用して画像・音声から種を特定し、Wikipedia情報を取得するエンジン"""
    def __init__(self):
        # APIキーは実行環境から自動供給
        self.api_key = "AIzaSyBzOeROpVGYEC1miK2ukPVeOdE0vEChv8Y" 
        self.model_id = "gemini-2.5-flash-preview-09-2025"

    def identify_from_image(self, base64_image):
        """画像から種を特定する"""
        prompt = (
            "この画像に写っている野鳥、または昆虫を特定してください。 "
            "回答は以下のJSON形式のみで返してください。余計な解説は不要です。\n\n"
            "{\n"
            '  "species_name": "正確な和名",\n'
            '  "scientific_name": "学名",\n'
            '  "category": "野鳥 または 昆虫",\n'
            '  "short_description": "特徴の短い要約"\n'
            "}"
        )
        return self._call_gemini(prompt, base64_image, "image/png")

    def identify_from_audio(self, audio_bytes):
        """音声（鳴き声）データから種を特定する"""
        base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
        
        prompt = (
            "提供された音声は生き物の鳴き声です。この鳴き声の主である野鳥、または昆虫を特定してください。 "
            "回答は以下のJSON形式のみで返してください。\n\n"
            "{\n"
            '  "species_name": "正確な和名",\n'
            '  "scientific_name": "学名",\n'
            '  "category": "野鳥 または 昆虫",\n'
            '  "short_description": "鳴き声の特徴と生き物の解説"\n'
            "}"
        )
        return self._call_gemini(prompt, base64_audio, "audio/wav")

    def _call_gemini(self, prompt, base64_data, mime_type):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": mime_type, "data": base64_data}}
                ]
            }],
            "generationConfig": {"responseMimeType": "application/json"}
        }

        for i in range(3): # 指数バックオフ
            try:
                res = requests.post(url, json=payload, timeout=60)
                if res.status_code == 200:
                    data = res.json()
                    return json.loads(data['candidates'][0]['content']['parts'][0]['text']), None
                time.sleep(2 ** i)
            except Exception as e:
                if i == 2: return None, str(e)
        return None, "AIサーバーとの通信に失敗しました。"

    def get_wikipedia_info(self, title):
        """Wikipedia APIを直接叩いて情報を取得 (専用ライブラリ不要版)"""
        try:
            # 日本語WikipediaのAPIエンドポイント
            api_url = "https://ja.wikipedia.org/w/api.php"
            
            # 1. まずは指定されたタイトルで検索・要約取得
            params = {
                "action": "query",
                "format": "json",
                "prop": "extracts|info",
                "exintro": True,
                "explaintext": True,
                "titles": title,
                "inprop": "url",
                "redirects": 1
            }
            
            res = requests.get(api_url, params=params, timeout=10)
            data = res.json()
            
            pages = data.get("query", {}).get("pages", {})
            page_id = next(iter(pages))
            
            if page_id == "-1":
                return "詳細なWikipedia記事が見つかりませんでした。", ""
            
            page_data = pages[page_id]
            summary = page_data.get("extract", "要約が見つかりませんでした。")
            full_url = page_data.get("fullurl", f"https://ja.wikipedia.org/wiki/{title}")
            
            return summary[:1000] + "...", full_url
            
        except Exception as e:
            return f"Wikipedia情報の取得に失敗しました: {e}", ""

class WildlifeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI野鳥・昆虫判定機 ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"
        self.SECONDARY_COLOR = "#FFCC33"
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.ACCENT_GREEN = "#2ECC71"

        self.ai = WildlifeAI()
        self.p = pyaudio.PyAudio()
        self.current_image_path = None
        self.is_recording = False
        
        self.setup_ui()

    def setup_ui(self):
        # メインタイトル
        header = tk.Frame(self.root, bg="#FFFBEB")
        header.pack(pady=20)
        tk.Label(header, text="🔭 AI野鳥・昆虫判定機", 
                 font=("Meiryo", 28, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR).pack()
        tk.Label(header, text="〜 カメラとマイクで、身近な自然を解き明かす 〜", 
                 font=("Meiryo", 10), bg="#FFFBEB", fg="#95A5A6").pack()

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=40, pady=10)
        
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=2)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=400)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        img_frame = tk.LabelFrame(self.left_panel, text=" 📸 写真で判定 ", font=("Meiryo", 10, "bold"),
                                 bg=self.BG_WHITE, fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        img_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.btn_upload = tk.Button(img_frame, text="画像をアップロード 📁", command=self.load_image,
                                   bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 11, "bold"),
                                   relief=tk.FLAT, cursor="hand2", pady=12)
        self.btn_upload.pack(fill=tk.X, padx=15, pady=15)

        voice_frame = tk.LabelFrame(self.left_panel, text=" 🎙️ 鳴き声で判定 ", font=("Meiryo", 10, "bold"),
                                   bg=self.BG_WHITE, fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        voice_frame.pack(fill=tk.X, pady=10)
        
        self.btn_record = tk.Button(voice_frame, text="鳴き声を録音する (5秒) 🎤", command=self.start_recording,
                                   bg=self.ACCENT_GREEN, fg="white", font=("Meiryo", 11, "bold"),
                                   relief=tk.FLAT, cursor="hand2", pady=12)
        self.btn_record.pack(fill=tk.X, padx=15, pady=15)

        self.status_label = tk.Label(self.left_panel, text="準備完了", bg="#FFFBEB", 
                                    font=("Meiryo", 10, "bold"), fg=self.TEXT_COLOR)
        self.status_label.pack(pady=20)

        guide = "【ヒント】\n・ライブラリ不要で直接通信するよう修正しました。\n・ネットワークに接続した状態で使用してください。"
        tk.Label(self.left_panel, text=guide, bg="#FFFBEB", justify=tk.LEFT, 
                 font=("Meiryo", 9), fg="#95A5A6").pack(side=tk.BOTTOM, pady=20)

        # --- 右側：結果表示パネル ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        self.preview_canvas = tk.Canvas(self.right_panel, height=300, bg="#F0F0F0", highlightthickness=0)
        self.preview_canvas.pack(fill=tk.X, pady=(0, 15))
        self.img_item = self.preview_canvas.create_image(0, 0, anchor=tk.NW)

        wiki_frame = tk.LabelFrame(self.right_panel, text=" 📜 Wikipedia 調査報告 ", font=("Meiryo", 11, "bold"),
                                  bg=self.BG_WHITE, fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        wiki_frame.pack(fill=tk.BOTH, expand=True)

        self.wiki_area = scrolledtext.ScrolledText(wiki_frame, font=("Meiryo", 11), 
                                                  bg=self.BG_WHITE, relief=tk.FLAT,
                                                  fg=self.TEXT_COLOR, state=tk.DISABLED,
                                                  padx=20, pady=20)
        self.wiki_area.pack(fill=tk.BOTH, expand=True)

    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")])
        if path:
            self.current_image_path = path
            img = Image.open(path)
            self._update_preview(img)
            self._start_analysis_thread("image")

    def start_recording(self):
        if self.is_recording: return
        self.is_recording = True
        self.btn_record.config(state=tk.DISABLED, text="録音中... 🔴")
        self.status_label.config(text="✨ 周囲の鳴き声を聴き取っています...", fg=self.ACCENT_GREEN)
        threading.Thread(target=self._recording_logic, daemon=True).start()

    def _recording_logic(self):
        try:
            stream = self.p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
            frames = []
            for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                data = stream.read(CHUNK)
                frames.append(data)
            stream.stop_stream()
            stream.close()

            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(self.p.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
            
            audio_data = buffer.getvalue()
            self.root.after(0, lambda: self._start_analysis_thread("audio", audio_data))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("録音エラー", str(e)))
        finally:
            self.root.after(0, lambda: self.btn_record.config(state=tk.NORMAL, text="鳴き声を録音する (5秒) 🎤"))

    def _start_analysis_thread(self, mode, data=None):
        self.status_label.config(text="🧠 AIが種類を特定しています...", fg=self.PRIMARY_COLOR)
        if mode == "image":
            with open(self.current_image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            threading.Thread(target=self._run_logic, args=("image", b64), daemon=True).start()
        else:
            threading.Thread(target=self._run_logic, args=("audio", data), daemon=True).start()

    def _run_logic(self, mode, data):
        if mode == "image":
            result, err = self.ai.identify_from_image(data)
        else:
            result, err = self.ai.identify_from_audio(data)
        
        if err:
            self.root.after(0, lambda: self._show_error(err))
            return

        wiki_text, wiki_url = self.ai.get_wikipedia_info(result['species_name'])
        self.root.after(0, lambda: self._display_result(result, wiki_text, wiki_url))

    def _display_result(self, result, wiki_text, wiki_url):
        self.wiki_area.config(state=tk.NORMAL)
        self.wiki_area.delete("1.0", tk.END)
        
        res_header = (
            f"【判定結果】\n"
            f"種名: {result['species_name']}\n"
            f"学名: {result['scientific_name']}\n"
            f"分類: {result['category']}\n"
            f"AI要約: {result['short_description']}\n\n"
            f"----------------------------------------\n\n"
            f"【Wikipedia 詳細情報】\n{wiki_text}\n\n"
            f"詳細URL: {wiki_url if wiki_url else 'なし'}"
        )
        self.wiki_area.insert(tk.END, res_header)
        self.wiki_area.config(state=tk.DISABLED)
        self.status_label.config(text="✅ 特定が完了しました！", fg=self.ACCENT_GREEN)

    def _update_preview(self, pil_img):
        self.root.update_idletasks()
        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()
        if cw < 50: cw = 800 # 初期化前のフォールバック
        ratio = min(cw / pil_img.width, ch / pil_img.height)
        new_size = (int(pil_img.width * ratio), int(pil_img.height * ratio))
        disp_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
        self.tk_img = ImageTk.PhotoImage(disp_img)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(cw//2, ch//2, anchor=tk.CENTER, image=self.tk_img)

    def _show_error(self, msg):
        messagebox.showerror("解析エラー", f"失敗しました: {msg}")
        self.status_label.config(text="❌ エラー発生", fg="red")

    def on_closing(self):
        self.p.terminate()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    app = WildlifeApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()