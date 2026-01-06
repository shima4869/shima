# AI会議の雰囲気可視化ツール ✨
# インストール: pip install tkinter pyaudio numpy matplotlib pillow
# 実行方法: python 6_meeting_visualizer.py
# Select Interpreter: Python 3.11.9

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import pyaudio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import threading
import time
import collections
import sys # 終了処理のために追加

# --- 音声設定 ---
CHUNK = 1024
RATE = 44100
FORMAT = pyaudio.paInt16

class VibeEngine:
    """音声データを解析して会議の雰囲気を判定するクラス"""
    def __init__(self):
        try:
            self.p = pyaudio.PyAudio()
        except:
            print("オーディオデバイスの初期化に失敗しました。")
            
        self.stream = None
        self.is_running = False
        
        # 解析用データ
        self.history_size = 60  
        self.volume_history = collections.deque(maxlen=self.history_size)
        self.speech_duration_history = [] 
        
        # 内部状態
        self.is_speaking = False
        self.speech_start_time = 0
        self.silence_start_time = time.time()
        self.turn_count = 0 
        
        # 定数
        self.SILENCE_THRESHOLD = 500 

    def start(self):
        try:
            self.stream = self.p.open(format=FORMAT, channels=1, rate=RATE,
                                     input=True, frames_per_buffer=CHUNK)
            self.is_running = True
            return True
        except:
            return False

    def stop(self):
        """エンジンとリソースを停止"""
        self.is_running = False
        time.sleep(0.1) # スレッドがループを抜けるのを待つ
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if hasattr(self, 'p'):
                self.p.terminate()
        except:
            pass

    def get_rms(self, data):
        """音圧レベル（RMS）を計算"""
        decoded = np.frombuffer(data, dtype=np.int16)
        return np.sqrt(np.mean(decoded.astype(np.float32)**2))

    def analyze_vibe(self):
        """現在の統計データから雰囲気を判定"""
        if not self.volume_history:
            return "待機中...", "#95A5A6"

        silence_count = sum(1 for v in self.volume_history if v < self.SILENCE_THRESHOLD)
        silence_ratio = silence_count / len(self.volume_history)

        current_speech_len = 0
        if self.is_speaking:
            current_speech_len = time.time() - self.speech_start_time

        if silence_ratio > 0.8:
            return "沈黙が多い (静かすぎるかも？)", "#34495E"
        
        if current_speech_len > 15: 
            return "誰か一人が喋りすぎ (独演会状態)", "#E74C3C"

        if self.turn_count >= 5: 
            return "活発な議論 (盛り上がっています！)", "#2ECC71"

        if silence_ratio < 0.3:
            return "安定した会話中", "#F39C12"

        return "穏やかな雰囲気", "#FF9F43"

class MeetingVibeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI会議の雰囲気可視化ツール ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"

        self.engine = VibeEngine()
        self.setup_ui()
        
        # グラフ描画用
        self.update_graph_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="📊 会議の雰囲気可視化 AI", 
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

        vibe_frame = tk.LabelFrame(self.left_panel, text=" 👁️ 今の会議の雰囲気 ", 
                                  font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                  fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        vibe_frame.pack(fill=tk.X, pady=(0, 10))

        self.lbl_vibe = tk.Label(vibe_frame, text="開始ボタンを押してね", bg=self.BG_WHITE, 
                                font=("Meiryo", 14, "bold"), fg=self.TEXT_COLOR, pady=30, wraplength=300)
        self.lbl_vibe.pack()

        self.run_btn = tk.Button(self.left_panel, text="解析を開始する ▶", 
                                command=self.toggle_engine,
                                bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                relief=tk.FLAT, cursor="hand2", pady=15)
        self.run_btn.pack(fill=tk.X, pady=10)

        info_frame = tk.LabelFrame(self.left_panel, text=" 📝 リアルタイム統計 ", 
                                  font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                  fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        info_frame.pack(fill=tk.X, pady=10)
        
        self.lbl_turns = tk.Label(info_frame, text="会話の活発さ: 0回", bg=self.BG_WHITE, font=("Meiryo", 10))
        self.lbl_turns.pack(anchor="w", padx=15, pady=5)
        
        self.lbl_status = tk.Label(info_frame, text="状態: 待機中", bg=self.BG_WHITE, font=("Meiryo", 10))
        self.lbl_status.pack(anchor="w", padx=15, pady=5)

        guide_text = "【終了方法】\n右上の[×]ボタンでプログラムを\n完全に終了できます。"
        tk.Label(self.left_panel, text=guide_text, bg="#FFFBEB", justify=tk.LEFT, 
                 font=("Meiryo", 9, "bold"), fg="#95A5A6").pack(side=tk.BOTTOM, pady=20)

        # --- 右側：グラフ表示パネル ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        graph_frame = tk.LabelFrame(self.right_panel, text=" 📈 音声エネルギー・タイムライン ", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        graph_frame.pack(fill=tk.BOTH, expand=True)

        self.fig, self.ax = plt.subplots(figsize=(8, 4), dpi=100)
        self.fig.patch.set_facecolor('#FFFFFF')
        self.ax.set_ylim(0, 3000)
        self.ax.set_axis_off() 
        self.line, = self.ax.plot([], [], color=self.PRIMARY_COLOR, lw=2)

        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas_plot.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def toggle_engine(self):
        if not self.engine.is_running:
            if self.engine.start():
                self.run_btn.config(text="解析を停止する ⏹", bg="#E74C3C")
                self.write_log("解析を開始しました。")
                threading.Thread(target=self.audio_loop, daemon=True).start()
            else:
                messagebox.showerror("エラー", "マイクデバイスが見つかりません。")
        else:
            self.engine.is_running = False
            self.run_btn.config(text="解析を開始する ▶", bg=self.PRIMARY_COLOR)
            self.write_log("解析を停止しました。")

    def audio_loop(self):
        turn_timer = time.time()
        while self.engine.is_running:
            try:
                data = self.engine.stream.read(CHUNK, exception_on_overflow=False)
                if not self.engine.is_running: break
                
                rms = self.engine.get_rms(data)
                self.engine.volume_history.append(rms)

                if rms > self.engine.SILENCE_THRESHOLD:
                    if not self.engine.is_speaking:
                        self.engine.is_speaking = True
                        self.engine.speech_start_time = time.time()
                        self.engine.turn_count += 1
                        if time.time() - turn_timer > 30:
                            self.engine.turn_count = 1
                            turn_timer = time.time()
                else:
                    if self.engine.is_speaking:
                        self.engine.is_speaking = False
            except:
                break
            time.sleep(0.01)

    def write_log(self, msg):
        self.lbl_status.config(text=f"状態: {msg}")

    def update_graph_loop(self):
        if not hasattr(self.root, 'winfo_exists') or not self.root.winfo_exists():
            return

        vibe_text, vibe_color = self.engine.analyze_vibe()
        self.lbl_vibe.config(text=vibe_text, fg=vibe_color)
        self.lbl_turns.config(text=f"直近の会話の活発さ: {self.engine.turn_count} ターン/30s")

        if self.engine.volume_history:
            y = list(self.engine.volume_history)
            x = range(len(y))
            self.ax.clear()
            self.ax.set_ylim(0, 5000)
            self.ax.set_axis_off()
            self.ax.fill_between(x, y, color=self.PRIMARY_COLOR, alpha=0.3)
            self.ax.plot(x, y, color=self.PRIMARY_COLOR, lw=2)
            self.ax.axhline(self.engine.SILENCE_THRESHOLD, color='#CCC', linestyle='--', lw=1)
            self.canvas_plot.draw()

        if self.engine.is_running or not self.engine.is_running: # 常に更新予約
            self.root.after(500, self.update_graph_loop)

    def on_closing(self):
        """【重要】リソースを完全に解放して終了"""
        try:
            self.engine.stop()    # 音声停止
            plt.close('all')      # グラフ破棄
            self.root.destroy()   # ウィンドウ破棄
        except:
            pass
        sys.exit(0) # プロセスを強制終了

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = MeetingVibeApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()