# AI自動作曲システム (大画面・安定版) ✨
# インストール: pip install pyaudio numpy pillow
# 実行方法: python 19_ai_composer.py
# Select Interpreter: Python 3.11.9

import pyaudio
import numpy as np
import random
import time
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import sys

# --- 音声設定 (既存のシステム設定を継承) ---
RATE = 44100

NOTES = {
    'C3': 130.81, 'D3': 146.83, 'E3': 164.81, 'F3': 174.61, 'G3': 196.00, 'A3': 220.00, 'B3': 246.94,
    'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'F4': 349.23, 'G4': 392.00, 'A4': 440.00, 'B4': 493.88,
    'C5': 523.25, 'D5': 587.33, 'E5': 659.25, 'F5': 698.46, 'G5': 783.99, 'A5': 880.00, 'B5': 987.77,
    'C6': 1046.50
}

SCALES = {
    "Happy": {
        "notes": ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5', 'D5', 'E5'],
        "tempo": 0.15,
        "color": "#FFCC33" # イエロー
    },
    "Sad": {
        "notes": ['A3', 'B3', 'C4', 'D4', 'E4', 'F4', 'G4', 'A4'],
        "tempo": 0.4,
        "color": "#3498DB" # ブルー
    },
    "Cyber": {
        "notes": ['C4', 'E4', 'G4', 'A4', 'C5', 'E5', 'G5'],
        "tempo": 0.1,
        "color": "#2ECC71" # グリーン
    }
}

class Synthesizer:
    """音声生成・AI作曲エンジン"""
    def __init__(self):
        try:
            self.p = pyaudio.PyAudio()
            self.stream = self.p.open(format=pyaudio.paFloat32,
                                      channels=1,
                                      rate=RATE,
                                      output=True)
        except Exception as e:
            print(f"Audio Error: {e}")
            sys.exit(1)
            
        self.current_mode = "Happy"
        self.is_playing = True
        self.current_note_name = ""
        
    def generate_wave(self, freq, duration):
        t = np.linspace(0, duration, int(RATE * duration), False)
        wave = 0.6 * np.sin(2 * np.pi * freq * t) + \
               0.3 * np.sin(2 * np.pi * freq * 2 * t) + \
               0.1 * np.sin(2 * np.pi * freq * 3 * t)
        envelope = np.exp(-3 * t) 
        wave = wave * envelope
        return wave.astype(np.float32)

    def play_loop(self):
        last_note_index = 0
        while self.is_playing:
            mode_data = SCALES[self.current_mode]
            scale_notes = mode_data["notes"]
            base_tempo = mode_data["tempo"]
            
            if self.current_mode == "Sad":
                move = random.choice([-1, 0, 1])
            elif self.current_mode == "Happy":
                move = random.choice([-2, -1, 0, 1, 2, 3])
            else:
                move = random.choice([-5, -2, 2, 5])
            
            next_index = max(0, min(len(scale_notes) - 1, last_note_index + move))
            last_note_index = next_index
            
            note_name = scale_notes[next_index]
            freq = NOTES.get(note_name, 440)
            self.current_note_name = note_name
            
            duration = base_tempo
            if random.random() < 0.2: duration *= 2
            if random.random() < 0.1: duration /= 2

            try:
                wave_data = self.generate_wave(freq, duration)
                self.stream.write(wave_data.tobytes())
            except:
                break
            
            time.sleep(0.01)

    def stop(self):
        self.is_playing = False
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, 'p'):
            self.p.terminate()

class ComposerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI自動作曲システム (大画面・安定版) ✨")
        self.root.geometry("1500x900") # 横幅を少し拡大
        self.root.configure(bg="#FFFBEB")

        self.PRIMARY_COLOR = "#FF9F43"
        self.SECONDARY_COLOR = "#FFCC33"
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"

        self.synth = Synthesizer()
        self.setup_ui()
        
        self.music_thread = threading.Thread(target=self.synth.play_loop, daemon=True)
        self.music_thread.start()
        
        # 最初の描画を開始
        self.update_visualizer()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🎹 AI自動作曲システム", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 【重要】比率調整：左(操作)1, 右(表示)10 に設定し、画像を大きく表示
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=10)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：スリムな操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=250)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        mode_frame = tk.LabelFrame(self.left_panel, text=" 🎭 気分を選択 ", 
                                   font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        mode_frame.pack(fill=tk.X, pady=(0, 10))

        self.mode_buttons = {}
        modes = [("Happy", "楽しい"), ("Sad", "悲しい"), ("Cyber", "未来的")]
        for m_id, label in modes:
            btn = tk.Button(mode_frame, text=label, command=lambda m=m_id: self.change_mode(m),
                           bg="#F7F7F7", font=("Meiryo", 9, "bold"), pady=10, 
                           relief=tk.FLAT, cursor="hand2")
            btn.pack(fill=tk.X, padx=8, pady=4)
            self.mode_buttons[m_id] = btn

        self.update_button_highlight()

        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 ログ ", 
                                 font=("Meiryo", 9, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 8), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # --- 右側：最大化したビジュアライザー ---
        self.right_panel = tk.Frame(self.main_container, bg="#1A1A1A", relief=tk.RIDGE, bd=3)
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        # ダブルバッファリングを促進するため、highlightthickness=0 を設定
        self.canvas = tk.Canvas(self.right_panel, bg="#111111", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

    def write_log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def change_mode(self, mode):
        self.synth.current_mode = mode
        self.update_button_highlight()
        self.write_log(f"モード: {mode}")

    def update_button_highlight(self):
        for m_id, btn in self.mode_buttons.items():
            if m_id == self.synth.current_mode:
                btn.config(bg=self.PRIMARY_COLOR, fg="white")
            else:
                btn.config(bg="#F7F7F7", fg=self.TEXT_COLOR)

    def update_visualizer(self):
        """アニメーション更新（点滅対策版）"""
        # delete("all") を行いますが、update_idletasks() を呼ばないことで点滅を防ぎます
        self.canvas.delete("all")
        
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        
        if cw > 50 and ch > 50:
            note = self.synth.current_note_name
            mode = self.synth.current_mode
            color = SCALES[mode]["color"]
            
            # グリッド描画 (背景装飾)
            for i in range(1, 12):
                x_grid = cw * i / 12
                self.canvas.create_line(x_grid, 0, x_grid, ch, fill="#1D1D1D", width=1)
            
            if note:
                octave = int(note[-1])
                tone_idx = "CDEFGAB".index(note[0])
                
                # ダイナミックな座標計算
                x = (cw / 8) * (tone_idx + 1)
                y = ch - (octave - 2) * (ch / 4)
                
                # 光彩エフェクト
                self.canvas.create_oval(x-70, y-70, x+70, y+70, outline=color, width=1, stipple="gray25")
                self.canvas.create_oval(x-55, y-55, x+55, y+55, outline=color, width=2)
                self.canvas.create_oval(x-40, y-40, x+40, y+40, fill=color, outline="")
                self.canvas.create_text(x, y, text=note, font=("Impact", 28, "bold"), fill="black")

            # 情報表示
            self.canvas.create_text(40, 50, text=f"AI COMPOSER: {mode.upper()}", 
                                   font=("Meiryo", 28, "bold"), fill="white", anchor="w")
            self.canvas.create_text(40, ch-40, text="Real-time Neural Melody Generation...", 
                                   font=("Consolas", 11), fill="#444", anchor="w")

        # 描画が終わったあとにループを予約（update_idletasksは不要）
        if self.synth.is_playing:
            self.root.after(40, self.update_visualizer)

    def on_closing(self):
        self.synth.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = ComposerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()