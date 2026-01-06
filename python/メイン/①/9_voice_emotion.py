# 声の感情分析・可視化システム AI
# インストール: pip install pyaudio numpy matplotlib pillow
# 実行方法: python 9_voice_emotion.py
# Select Interpreter: Python 3.11.9

import pyaudio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import sys
import threading
import time
import os

# --- 音声設定 (既存システムを継承) ---
CHUNK = 1024
RATE = 44100

class VoiceEmotionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("声の感情分析・可視化システム ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数 (シリーズ統一デザイン)
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        
        # 感情の定義と色 (グラフ用)
        self.emotions = ['Neutral', 'Happy', 'Angry', 'Sad']
        self.emotion_colors = ['#BDC3C7', '#FFCC33', '#E74C3C', '#3498DB']
        self.current_scores = [0.0, 0.0, 0.0, 0.0]

        # 状態管理
        self.is_running = True
        
        # PyAudio初期化
        try:
            self.p = pyaudio.PyAudio()
            if self.p.get_device_count() == 0:
                raise IOError("マイクが見つかりません。")
            self.stream = self.p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
        except Exception as e:
            messagebox.showerror("エラー", f"マイクの初期化に失敗しました: {e}")
            self.is_running = False
            sys.exit(1)

        self.setup_ui()
        
        # グラフのアニメーション開始
        self.ani = FuncAnimation(self.fig, self.update_frame, interval=50, blit=False)

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🎙️ 声の感情分析・可視化システム", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：ステータスパネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        status_frame = tk.LabelFrame(self.left_panel, text=" 👁️ 現在の感情傾向 ", 
                                    font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        self.dominant_emotion_label = tk.Label(status_frame, text="分析中...", bg=self.BG_WHITE, 
                                              font=("Meiryo", 20, "bold"), fg=self.TEXT_COLOR, pady=25)
        self.dominant_emotion_label.pack()

        hint_frame = tk.LabelFrame(self.left_panel, text=" 💡 解析のヒント ", 
                                  font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                  fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        hint_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        guide_text = (
            "・Happy: 高いピッチ & 元気な声\n"
            "・Angry: 強い音圧 (怒鳴り声)\n"
            "・Sad: 低いピッチ & 小さな声\n"
            "・Neutral: 通常の会話トーン\n\n"
            "※周囲の雑音によって判定が\n  変動する場合があります。"
        )
        tk.Label(hint_frame, text=guide_text, bg=self.BG_WHITE, justify=tk.LEFT, 
                 font=("Meiryo", 10), padx=15, pady=20).pack(anchor="nw")

        exit_label = tk.Label(self.left_panel, text="終了するには右上の[×]ボタンを\n押してください。", 
                             bg="#FFFBEB", fg="#95A5A6", font=("Meiryo", 9), justify=tk.LEFT)
        exit_label.pack(side=tk.BOTTOM, pady=10)

        # --- 右側：グラフ表示エリア ---
        self.right_panel = tk.Frame(self.main_container, bg=self.BG_WHITE, relief=tk.RIDGE, bd=2)
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        # MatplotlibのFigure作成
        self.fig, self.ax = plt.subplots(figsize=(8, 6), dpi=100)
        self.fig.patch.set_facecolor('white')
        self.bars = self.ax.bar(self.emotions, [0]*4, color=self.emotion_colors)
        self.ax.set_ylim(0, 100)
        self.ax.set_title("Real-time Voice Emotion Intensity", fontname="Meiryo", fontsize=14, pad=20)
        self.ax.set_ylabel("Intensity Score (%)", fontname="Meiryo")
        
        self.canvas_graph = FigureCanvasTkAgg(self.fig, master=self.right_panel)
        self.canvas_widget = self.canvas_graph.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def get_audio_features(self, data):
        """音声特徴量抽出ロジック"""
        audio_data = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        volume = np.sqrt(np.mean(audio_data**2))
        windowed_data = audio_data * np.hamming(len(audio_data))
        spectrum = np.abs(np.fft.rfft(windowed_data))
        freqs = np.fft.rfftfreq(len(windowed_data), d=1.0/RATE)
        
        target_indices = np.where((freqs > 80) & (freqs < 1000))[0]
        if len(target_indices) > 0 and np.max(spectrum[target_indices]) > 0:
            peak_idx = target_indices[np.argmax(spectrum[target_indices])]
            pitch = freqs[peak_idx]
        else:
            pitch = 0
        return volume, pitch

    def analyze_emotion(self, volume, pitch):
        """感情分析ロジック"""
        scores = {'Neutral': 80, 'Happy': 0, 'Angry': 0, 'Sad': 0}
        if volume < 200: return [100, 0, 0, 0]

        if volume > 1500:
            if pitch > 300:
                scores['Happy'] += min(100, (volume / 50) + (pitch / 10))
                scores['Neutral'] = 10
            else:
                scores['Angry'] += min(100, (volume / 40))
                scores['Neutral'] = 10
        elif 200 < volume < 800:
            if 0 < pitch < 150:
                scores['Sad'] += min(100, (1000 - volume) / 10 + (200 - pitch))
                scores['Neutral'] = 20
            else:
                scores['Neutral'] = 80
        else:
            scores['Neutral'] = 60
            if pitch > 250: scores['Happy'] += 30

        return [scores[e] for e in self.emotions]

    def update_frame(self, frame_count):
        """グラフとUIの更新処理 (閉じたあとの衝突を防止)"""
        if not self.is_running: return self.bars

        try:
            if hasattr(self, 'stream') and self.stream.is_active():
                data = self.stream.read(CHUNK, exception_on_overflow=False)
                volume, pitch = self.get_audio_features(data)
                new_scores = self.analyze_emotion(volume, pitch)
                
                # スムージング
                alpha = 0.2
                self.current_scores = [self.current_scores[i] * (1 - alpha) + new_scores[i] * alpha for i in range(4)]

                # グラフ更新
                max_score, max_idx = -1, 0
                for i, (bar, score) in enumerate(zip(self.bars, self.current_scores)):
                    bar.set_height(score)
                    if score > max_score: max_score, max_idx = score, i

                dominant = self.emotions[max_idx]
                jap_map = {'Neutral': '穏やか・平穏', 'Happy': '喜び・興奮 ✨', 'Angry': '怒り・緊張 💢', 'Sad': '悲しみ・静寂 💧'}
                
                # ウィンドウ生存チェックを行ってからラベル更新
                if self.root.winfo_exists():
                    self.root.after(0, lambda: self.safe_update_label(jap_map[dominant], self.emotion_colors[max_idx]))

        except Exception:
            pass
        return self.bars

    def safe_update_label(self, text, color):
        """ウィンドウが閉じられたあとの描画を防止する安全な更新メソッド"""
        try:
            if self.is_running and self.root.winfo_exists():
                self.dominant_emotion_label.config(text=text, fg=color)
        except (tk.TclError, AttributeError):
            pass

    def on_closing(self):
        """終了時のリソース解放と強制終了処理"""
        self.is_running = False
        try:
            # アニメーション停止
            if hasattr(self, 'ani'): self.ani.event_source.stop()
            # 音声停止
            if hasattr(self, 'stream'):
                self.stream.stop_stream()
                self.stream.close()
            if hasattr(self, 'p'):
                self.p.terminate()
            plt.close('all') # グラフの破棄
        except:
            pass
        
        self.root.destroy()
        sys.exit(0) # プロセスを完全に終了させる

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = VoiceEmotionApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # 起動時の不必要なMatplotlibのログを抑制
    import logging
    logging.getLogger('matplotlib').setLevel(logging.ERROR)
    
    root.mainloop()