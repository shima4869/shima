import pyaudio
import numpy as np
import cv2
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import threading
import time
import sys

# --- 音声設定 (既存のシステムを継承) ---
CHUNK = 1024 * 2
RATE = 44100
FORMAT = pyaudio.paInt16

class VoiceChangerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ボイスチェンジャーAI ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"        # 緑

        # --- 既存システムの変数を初期化 ---
        self.p = pyaudio.PyAudio()
        self.mode = "normal"
        self.echo_buffer = np.zeros(CHUNK * 10, dtype=np.int16)
        self.echo_pos = 0
        self.phase = 0
        self.current_data_int = np.zeros(CHUNK, dtype=np.int16)
        
        # 音声ストリームの初期化
        try:
            self.stream_in = self.p.open(format=FORMAT, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)
            self.stream_out = self.p.open(format=FORMAT, channels=1, rate=RATE, output=True, frames_per_buffer=CHUNK)
        except Exception as e:
            messagebox.showerror("エラー", f"オーディオデバイスの初期化に失敗しました: {e}")
            sys.exit(1)

        # 状態管理
        self.is_running = True
        
        self.setup_ui()
        
        # 音声処理を別スレッドで開始
        self.audio_thread = threading.Thread(target=self.audio_loop, daemon=True)
        self.audio_thread.start()
        
        # UI更新ループ開始
        self.update_visualizer()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🎙️ ボイスチェンジャー AI", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：左1, 右4
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=4)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=350)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # モード選択
        mode_frame = tk.LabelFrame(self.left_panel, text=" 🎭 エフェクト選択 ", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        mode_frame.pack(fill=tk.X, pady=(0, 10))

        self.mode_buttons = {}
        modes = [
            ("normal", "通常 (Normal)"),
            ("robot", "ロボット (Robot)"),
            ("alien", "エイリアン (Alien)"),
            ("echo", "エコー (Echo)"),
            ("slow", "スロー (Slow)")
        ]
        for m_id, label in modes:
            btn = tk.Button(mode_frame, text=label, command=lambda m=m_id: self.change_mode(m),
                           bg="#F7F7F7", font=("Meiryo", 10, "bold"), pady=10, 
                           relief=tk.FLAT, cursor="hand2")
            btn.pack(fill=tk.X, padx=10, pady=5)
            self.mode_buttons[m_id] = btn

        self.update_button_highlight()

        # ステータス表示
        status_frame = tk.LabelFrame(self.left_panel, text=" 📊 状態 ", 
                                    font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, pady=10)
        
        self.status_label = tk.Label(status_frame, text="稼働中", bg=self.BG_WHITE, 
                                    font=("Meiryo", 12, "bold"), fg=self.SAFE_COLOR, pady=10)
        self.status_label.pack()

        # 重要警告
        warning_label = tk.Label(self.left_panel, text="⚠️ 重要:\nハウリング防止のため、\n必ずイヤホンを使用してください！", 
                                bg="#FFFBEB", fg="#E74C3C", font=("Meiryo", 9, "bold"), justify=tk.LEFT)
        warning_label.pack(side=tk.BOTTOM, pady=10)

        # --- 右側：波形モニターエリア ---
        self.right_panel = tk.Frame(self.main_container, bg=self.BG_WHITE, relief=tk.RIDGE, bd=2)
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🌊 リアルタイム波形モニター ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.FLAT)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="#1A1A1A", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def change_mode(self, new_mode):
        self.mode = new_mode
        self.update_button_highlight()

    def update_button_highlight(self):
        for m_id, btn in self.mode_buttons.items():
            if m_id == self.mode:
                btn.config(bg=self.PRIMARY_COLOR, fg="white")
            else:
                btn.config(bg="#F7F7F7", fg=self.TEXT_COLOR)

    # --- 既存のエフェクトシステム (変更なし) ---
    def effect_robot(self, data_float, freq=400):
        t = np.arange(len(data_float)) + self.phase
        carrier = np.sin(2 * np.pi * freq * t / RATE)
        self.phase += len(data_float)
        return data_float * carrier

    def effect_echo(self, data_int):
        decay = 0.6
        output = data_int.copy()
        indices = (np.arange(len(data_int)) + self.echo_pos) % len(self.echo_buffer)
        echo_sound = self.echo_buffer[indices] * decay
        mixed = output + echo_sound
        self.echo_buffer[indices] = output
        self.echo_pos = (self.echo_pos + len(data_int)) % len(self.echo_buffer)
        return mixed

    def audio_loop(self):
        """バックグラウンドでの音声処理ループ (既存システムを継承)"""
        while self.is_running:
            try:
                input_data = self.stream_in.read(CHUNK, exception_on_overflow=False)
                data_int = np.frombuffer(input_data, dtype=np.int16)
                self.current_data_int = data_int # 描画用に保持
                data_float = data_int.astype(np.float32)

                output_data = data_float

                if self.mode == "robot":
                    output_data = self.effect_robot(data_float, freq=500) * 1.5
                elif self.mode == "alien":
                    output_data = self.effect_robot(data_float, freq=2000) * 1.5
                elif self.mode == "echo":
                    output_data = self.effect_echo(data_int).astype(np.float32)
                elif self.mode == "slow":
                    output_data = self.effect_robot(data_float, freq=100) * 2.0

                output_data = np.clip(output_data, -32768, 32767)
                output_bytes = output_data.astype(np.int16).tobytes()
                self.stream_out.write(output_bytes)

            except Exception as e:
                print(f"Audio Error: {e}")
                break

    def update_visualizer(self):
        """波形を描画してCanvasを更新 (既存の描画ロジックを統合)"""
        self.root.update_idletasks()
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        
        if cw > 50 and ch > 50:
            # OpenCVイメージを作成 (ダーク背景)
            img = np.zeros((ch, cw, 3), dtype=np.uint8)
            img[:] = (26, 26, 26) 
            
            # 波形の描画
            step = 10
            h_mid = ch // 2
            data = self.current_data_int
            
            if len(data) > 0:
                for i in range(0, len(data) - step, step):
                    x1 = int(i / len(data) * cw)
                    y1 = int(h_mid + data[i] / 200) # 少し感度を上げた
                    x2 = int((i + step) / len(data) * cw)
                    y2 = int(h_mid + data[i+step] / 200)
                    cv2.line(img, (x1, y1), (x2, y2), (255, 159, 67), 2) # オレンジ色の波形

            # BGR -> RGB 変換して表示
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_img)
            self.tk_img = ImageTk.PhotoImage(pil_img)
            self.canvas.itemconfig(self.image_item, image=self.tk_img)
            self.canvas.coords(self.image_item, 0, 0)

        if self.is_running:
            self.root.after(30, self.update_visualizer)

    def on_closing(self):
        self.is_running = False
        try:
            self.stream_in.stop_stream()
            self.stream_in.close()
            self.stream_out.stop_stream()
            self.stream_out.close()
            self.p.terminate()
        except:
            pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    # Windows高DPI対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = VoiceChangerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()