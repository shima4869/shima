# AI作詞・作曲アシスタント ✨
# インストール: pip install requests numpy pyaudio pillow
# 実行方法: python 1_ai_songwriter.py
# Select Interpreter: Python 3.11.9

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import requests
import json
import numpy as np
import pyaudio
import threading
import time
import os
import re
from PIL import Image, ImageTk

# --- 音声設定 ---
RATE = 44100
# 音名と周波数の定義
NOTES = {
    'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'F4': 349.23, 'G4': 392.00, 'A4': 440.00, 'B4': 493.88,
    'C5': 523.25, 'D5': 587.33, 'E5': 659.25, 'F5': 698.46, 'G5': 783.99, 'A5': 880.00, 'B5': 987.77, 
    'C6': 1046.50, 'R': 0 # Rは休符
}

class SongGeneratorAI:
    """Gemini APIを使用して作詞・作曲データを作成するエンジン"""
    def __init__(self):
        # APIキーは実行環境から自動供給されます
        self.api_key = "AIzaSyBzOeROpVGYEC1miK2ukPVeOdE0vEChv8Y" 
        self.model_id = "gemini-2.5-flash-preview-09-2025"

    def generate_song(self, keyword):
        """キーワードから歌詞とメロディを生成する"""
        prompt = (
            f"「{keyword}」というテーマや感情に基づいて、短い歌の歌詞（4〜8行程度）と、それに合うメロディを作成してください。\n"
            "以下の厳密なJSON形式のみで回答してください。挨拶や説明文は一切含めないでください。\n\n"
            "{\n"
            '  "lyrics": "（ここに歌詞を記述。改行を含めてください）",\n'
            '  "melody": [\n'
            '    {"note": "C4", "duration": 0.5},\n'
            '    {"note": "E4", "duration": 0.5},\n'
            '    {"note": "G4", "duration": 1.0}\n'
            "  ]\n"
            "}\n\n"
            "※音名は C4, D4, E4, F4, G4, A4, B4, C5, D5, E5, F5, G5, A5, B5, C6 の中から選んでください。休符は R です。\n"
            "※duration（長さ）は 0.25, 0.5, 1.0 など秒単位で指定してください。メロディ全体で合計12〜20音程度にしてください。"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                res_json = response.json()
                res_text = res_json['candidates'][0]['content']['parts'][0]['text']
                
                # JSON部分を正規表現で抽出
                json_match = re.search(r'\{.*\}', res_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0)), None
                else:
                    return None, "AIの回答形式が不正です。"
            return None, f"APIエラーが発生しました (Code: {response.status_code})"
        except Exception as e:
            return None, str(e)

class LyricComposerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI作詞・作曲アシスタント ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.ACCENT_BLUE = "#3498DB"

        self.ai = SongGeneratorAI()
        self.p = pyaudio.PyAudio()
        self.is_playing = False
        self.current_melody = []
        
        self.setup_ui()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🎵 AI作詞・作曲アシスタント", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 全体比率：左1, 右3
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 1. 入力エリア
        input_frame = tk.LabelFrame(self.left_panel, text=" 🖊️ テーマ・感情を入力 ", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        input_frame.pack(fill=tk.X, pady=5)

        self.keyword_entry = tk.Entry(input_frame, font=("Meiryo", 12), relief=tk.SOLID, bd=1)
        self.keyword_entry.pack(fill=tk.X, padx=15, pady=15)
        self.keyword_entry.insert(0, "夏の海と秘密の約束")

        # 2. 生成・演奏ボタン
        self.gen_btn = tk.Button(self.left_panel, text="新しい曲を生成 🚀", 
                                command=self.start_generation,
                                bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                relief=tk.FLAT, cursor="hand2", pady=15)
        self.gen_btn.pack(fill=tk.X, pady=5)

        self.play_btn = tk.Button(self.left_panel, text="メロディを聴く 🎧", 
                                 command=self.play_melody_thread,
                                 bg=self.ACCENT_BLUE, fg="white", font=("Meiryo", 12, "bold"),
                                 relief=tk.FLAT, cursor="hand2", pady=15, state=tk.DISABLED)
        self.play_btn.pack(fill=tk.X, pady=5)

        self.status_label = tk.Label(self.left_panel, text="準備完了", bg="#FFFBEB", 
                                    font=("Meiryo", 10, "bold"), fg=self.TEXT_COLOR)
        self.status_label.pack(pady=10)

        # 3. 操作ガイドパネル
        guide_frame = tk.LabelFrame(self.left_panel, text=" 💡 創作のヒント ", 
                                   font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        guide_frame.pack(fill=tk.X, pady=5)
        
        guide_text = "・「切ない雨」「宇宙の旅」など\n　自由に言葉を入力してください。\n・AIが歌詞の情景に合わせた\n　音階を選んで作曲します。"
        guide_label = tk.Label(guide_frame, text=guide_text, bg=self.BG_WHITE, justify=tk.LEFT, 
                               font=("Meiryo", 9), fg=self.TEXT_COLOR, padx=10, pady=10)
        guide_label.pack(fill=tk.X)

        # --- 右側：プレビューエリア ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")
        
        # 歌詞とスコアを5:5の比率で固定するため grid を使用
        self.right_panel.rowconfigure(0, weight=1) # 歌詞エリア
        self.right_panel.rowconfigure(1, weight=1) # スコアエリア
        self.right_panel.columnconfigure(0, weight=1)

        # 1. 歌詞カード
        lyric_frame = tk.LabelFrame(self.right_panel, text=" 📜 AI生成された歌詞 ", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        lyric_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        self.lyric_area = scrolledtext.ScrolledText(lyric_frame, font=("Meiryo", 14), 
                                                   bg=self.BG_WHITE, relief=tk.FLAT,
                                                   fg=self.TEXT_COLOR, state=tk.DISABLED,
                                                   padx=30, pady=30)
        self.lyric_area.pack(fill=tk.BOTH, expand=True)

        # 2. ビジュアライザー
        viz_frame = tk.LabelFrame(self.right_panel, text=" 🎹 メロディ・スコア (ビジュアライザー) ", 
                                 font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        viz_frame.grid(row=1, column=0, sticky="nsew", pady=(5, 0))

        # Canvasの高さを固定せず、expand=Trueでフレームいっぱいに広げる
        self.canvas = tk.Canvas(viz_frame, bg="#2C3E50", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def start_generation(self):
        keyword = self.keyword_entry.get().strip()
        if not keyword:
            messagebox.showwarning("入力不足", "テーマを入力してください。")
            return
        
        self.gen_btn.config(state=tk.DISABLED, text="AIが創作中...")
        self.status_label.config(text="✨ AIが歌詞と音を紡いでいます...", fg=self.PRIMARY_COLOR)
        
        threading.Thread(target=self.run_logic, args=(keyword,), daemon=True).start()

    def run_logic(self, keyword):
        result, error = self.ai.generate_song(keyword)
        self.root.after(0, lambda: self.finish_generation(result, error))

    def finish_generation(self, result, error):
        self.gen_btn.config(state=tk.NORMAL, text="新しい曲を生成 🚀")
        if error:
            messagebox.showerror("生成失敗", f"エラー: {error}")
            self.status_label.config(text="❌ 失敗しました", fg="red")
            return

        # 歌詞の更新
        self.lyric_area.config(state=tk.NORMAL)
        self.lyric_area.delete("1.0", tk.END)
        self.lyric_area.insert(tk.END, result.get("lyrics", ""))
        self.lyric_area.config(state=tk.DISABLED)

        # メロディの保持
        self.current_melody = result.get("melody", [])
        self.play_btn.config(state=tk.NORMAL if self.current_melody else tk.DISABLED)
        self.status_label.config(text="✅ 完成！メロディを聴けます", fg="#2ECC71")
        
        self.draw_melody()

    def draw_melody(self):
        """メロディラインをキャンバスに描画"""
        self.canvas.delete("all")
        if not self.current_melody: return

        # キャンバスのサイズが確定してから描画計算を行う
        self.root.update_idletasks()
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        
        # 最小サイズチェック
        if cw < 100 or ch < 100:
            self.root.after(100, self.draw_melody)
            return

        margin = 40
        unit_w = (cw - margin*2) / max(len(self.current_melody), 1)
        
        # 音階リスト
        note_list = ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5", "D5", "E5", "F5", "G5", "A5", "B5", "C6"]
        
        # ガイドライン描画
        for i in range(len(note_list)):
            y_line = ch - margin - (i * (ch - margin*2) / (len(note_list)-1))
            self.canvas.create_line(margin, y_line, cw-margin, y_line, fill="#34495E", width=1)

        for i, item in enumerate(self.current_melody):
            note = item.get("note", "R")
            if note in note_list:
                h_idx = note_list.index(note)
                x = margin + i * unit_w
                y = ch - margin - (h_idx * (ch - margin*2) / (len(note_list)-1))
                
                # 音符バー
                self.canvas.create_rectangle(x + 4, y - 5, x + unit_w - 4, y + 5, 
                                           fill=self.PRIMARY_COLOR, outline="white", width=1)
                # 音名表示
                self.canvas.create_text(x + unit_w/2, y - 15, text=note, fill="white", font=("Arial", 8))
            elif note == "R":
                x = margin + i * unit_w
                self.canvas.create_line(x + 10, ch/2, x + unit_w - 10, ch/2, fill="#95A5A6", width=2)

    def generate_wave(self, freq, duration):
        """指定された周波数のサイン波を生成"""
        if freq == 0: # 休符
            return np.zeros(int(RATE * duration)).astype(np.float32)
        
        t = np.linspace(0, duration, int(RATE * duration), False)
        wave = 0.4 * np.sin(2 * np.pi * freq * t) + 0.1 * np.sin(2 * np.pi * (freq*2) * t)
        fade = np.linspace(1.0, 0.0, len(wave))
        return (wave * fade).astype(np.float32)

    def play_melody_thread(self):
        if self.is_playing: return
        threading.Thread(target=self.play_melody, daemon=True).start()

    def play_melody(self):
        self.is_playing = True
        self.play_btn.config(state=tk.DISABLED, text="演奏中...")
        
        try:
            stream = self.p.open(format=pyaudio.paFloat32, channels=1, rate=RATE, output=True)
            for item in self.current_melody:
                if not self.is_playing: break
                note = item.get("note", "R")
                duration = float(item.get("duration", 0.5))
                freq = NOTES.get(note, 0)
                
                wave = self.generate_wave(freq, duration)
                stream.write(wave.tobytes())
                time.sleep(0.01)
                
            stream.stop_stream()
            stream.close()
        except Exception as e:
            print(f"Audio Playback Error: {e}")
            
        self.is_playing = False
        self.root.after(0, lambda: self.play_btn.config(state=tk.NORMAL, text="メロディを聴く 🎧"))

    def on_closing(self):
        self.is_playing = False
        self.p.terminate()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = LyricComposerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()