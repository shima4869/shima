# AI嘘発見器 ✨
# インストール: pip install tkinter mediapipe pyaudio numpy opencv-python pillow
# 実行方法: python 17_lie_detector_ai.py
# Select Interpreter: Python 3.11.9

import cv2
import mediapipe as mp
import numpy as np
import pyaudio
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import threading
import time
import sys
import collections

# --- 音声設定 ---
CHUNK = 1024
RATE = 22050

class LieDetectorEngine:
    """画像と音声から嘘の兆候を分析するエンジン"""
    def __init__(self):
        # MediaPipe Face Mesh (目線・まばたき用)
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # 音声解析用
        self.p = pyaudio.PyAudio()
        self.audio_stream = None
        self.pitch_history = collections.deque(maxlen=30)
        
        # 状態データ
        self.blink_count = 0
        self.eye_closed = False
        self.gaze_shifty_score = 0
        self.voice_tremble_score = 0
        self.last_iris_pos = None

    def start_audio(self):
        try:
            self.audio_stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=RATE,
                                            input=True, frames_per_buffer=CHUNK)
            return True
        except:
            return False

    def get_voice_jitter(self):
        """声の周波数の安定性を解析 (震えの算出)"""
        if self.audio_stream is None: return 0
        try:
            data = self.audio_stream.read(CHUNK, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16).astype(np.float32)
            
            # 自己相関法による簡易ピッチ(周波数)推定
            fft = np.fft.rfft(audio_data)
            freqs = np.fft.rfftfreq(len(audio_data), 1.0/RATE)
            peak_freq = freqs[np.argmax(np.abs(fft))]
            
            if np.max(np.abs(audio_data)) > 500: # 一定以上の音量がある時のみ
                self.pitch_history.append(peak_freq)
                
            if len(self.pitch_history) > 10:
                # 周波数の標準偏差を「震え」として定義
                jitter = np.std(self.pitch_history)
                return min(100, jitter * 2) # スコア化
            return 0
        except:
            return 0

    def analyze_face(self, landmarks, w, h):
        """目線とまばたきを解析"""
        # まばたき判定 (159:上まぶた, 145:下まぶた)
        p_up = landmarks[159]
        p_down = landmarks[145]
        dist = np.sqrt((p_up.x - p_down.x)**2 + (p_up.y - p_down.y)**2)
        
        if dist < 0.012: # 目が閉じている
            if not self.eye_closed:
                self.blink_count += 1
                self.eye_closed = True
        else:
            self.eye_closed = False

        # 視線の動き判定 (468:右虹彩中心)
        iris = landmarks[468]
        current_pos = np.array([iris.x, iris.y])
        shifty = 0
        if self.last_iris_pos is not None:
            move_dist = np.linalg.norm(current_pos - self.last_iris_pos)
            if move_dist > 0.005: # 急激な視線移動
                shifty = move_dist * 5000
        self.last_iris_pos = current_pos
        
        return shifty

class LieDetectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI嘘発見器 ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"
        self.ALERT_COLOR = "#E74C3C"
        self.SAFE_COLOR = "#2ECC71"
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"

        self.engine = LieDetectorEngine()
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.is_measuring = False
        self.start_time = 0
        
        # 最終スコア
        self.total_suspicion = 0
        
        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # タイトル
        header = tk.Label(self.root, text="🕵️ AI嘘発見器 (Simplified Version)", 
                         font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        header.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：解析結果パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 総合怪しさレベル
        score_frame = tk.LabelFrame(self.left_panel, text=" 👁️ 総合怪しさレベル ", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        score_frame.pack(fill=tk.X, pady=(0, 10))

        self.lbl_score = tk.Label(score_frame, text="0 %", bg=self.BG_WHITE, 
                                 font=("Impact", 48), fg=self.TEXT_COLOR)
        self.lbl_score.pack(pady=10)

        # リアルタイム・インジケーター
        stats_frame = tk.LabelFrame(self.left_panel, text=" 📝 兆候分析データ ", 
                                   font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        stats_frame.pack(fill=tk.X, pady=10)
        
        self.lbl_blink = tk.Label(stats_frame, text="まばたき: 0 回", bg=self.BG_WHITE, font=("Meiryo", 10))
        self.lbl_blink.pack(anchor="w", padx=15, pady=5)
        
        self.bar_gaze = ttk.Progressbar(stats_frame, length=200, mode='determinate')
        tk.Label(stats_frame, text="視線の揺れ:", bg=self.BG_WHITE, font=("Meiryo", 9)).pack(anchor="w", padx=15)
        self.bar_gaze.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        self.bar_voice = ttk.Progressbar(stats_frame, length=200, mode='determinate')
        tk.Label(stats_frame, text="声の震え:", bg=self.BG_WHITE, font=("Meiryo", 9)).pack(anchor="w", padx=15)
        self.bar_voice.pack(fill=tk.X, padx=15, pady=(0, 10))

        # 操作ボタン
        self.run_btn = tk.Button(self.left_panel, text="計測を開始する ▶", 
                                command=self.toggle_measure,
                                bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                relief=tk.FLAT, cursor="hand2", pady=15)
        self.run_btn.pack(fill=tk.X, pady=10)

        # 判定メッセージ
        self.lbl_msg = tk.Label(self.left_panel, text="質問を開始してください。", 
                               bg="#FFFBEB", font=("Meiryo", 11, "bold"), fg="#95A5A6", wraplength=300)
        self.lbl_msg.pack(pady=20)

        # --- 右側：モニターパネル ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ バイオメトリクス・モニター (目線・声紋トラッキング) ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def toggle_measure(self):
        if not self.is_measuring:
            if self.engine.start_audio():
                self.is_measuring = True
                self.start_time = time.time()
                self.engine.blink_count = 0
                self.run_btn.config(text="計測を終了して判定 ⏹", bg=self.ALERT_COLOR)
                self.lbl_msg.config(text="分析中... 相手をじっくり観察しています。", fg=self.PRIMARY_COLOR)
            else:
                messagebox.showerror("エラー", "マイクの起動に失敗しました。")
        else:
            self.is_measuring = False
            if self.engine.audio_stream:
                self.engine.audio_stream.stop_stream()
                self.engine.audio_stream.close()
            self.run_btn.config(text="計測を開始する ▶", bg=self.PRIMARY_COLOR)
            self.evaluate_result()

    def evaluate_result(self):
        """蓄積されたデータから最終結果を出す"""
        if self.total_suspicion > 70:
            msg = "🚨 【判定】 非常に怪しい！\n複数の嘘の兆候が検出されました。"
            color = self.ALERT_COLOR
        elif self.total_suspicion > 40:
            msg = "⚠️ 【判定】 やや疑わしい\n少し動揺している可能性があります。"
            color = "#F39C12"
        else:
            msg = "✅ 【判定】 真実の可能性高\n生体反応は極めて安定しています。"
            color = self.SAFE_COLOR
        
        self.lbl_msg.config(text=msg, fg=color)

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1) # 鏡表示
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.engine.face_mesh.process(rgb_frame)
            
            hud_color = (0, 159, 255) # オレンジ (BGR)
            
            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0]
                # 顔の解析
                shifty_score = self.engine.analyze_face(landmarks.landmark, w, h)
                
                # 音声の解析
                tremble_score = self.engine.get_voice_jitter()
                
                if self.is_measuring:
                    # 統計のリアルタイム更新
                    self.lbl_blink.config(text=f"まばたき: {self.engine.blink_count} 回")
                    self.bar_gaze["value"] = min(100, shifty_score)
                    self.bar_voice["value"] = tremble_score
                    
                    # 総合スコアの動的計算 (まばたき頻度、視線の揺れ、声の震え)
                    # 10秒あたり3回以上のまばたきをストレス過多とみなす等
                    duration = max(1, time.time() - self.start_time)
                    blink_rate_score = min(40, (self.engine.blink_count / duration) * 100)
                    
                    self.total_suspicion = int(blink_rate_score + (tremble_score * 0.3) + (min(100, shifty_score) * 0.3))
                    self.lbl_score.config(text=f"{self.total_suspicion} %")
                    
                    if self.total_suspicion > 60: self.lbl_score.config(fg=self.ALERT_COLOR)
                    else: self.lbl_score.config(fg=self.TEXT_COLOR)
                    
                    hud_color = (60, 76, 231) if self.total_suspicion > 60 else (46, 204, 113)

                # ビジュアルフィードバック (HUD描画)
                # 虹彩の描画
                for idx in [468, 473]:
                    pt = landmarks.landmark[idx]
                    cv2.circle(frame, (int(pt.x * w), int(pt.y * h)), 4, hud_color, -1)
                
                # 解析エリアの強調
                for idx in [33, 133, 362, 263]: # 目角
                    pt = landmarks.landmark[idx]
                    cv2.circle(frame, (int(pt.x * w), int(pt.y * h)), 2, (255, 255, 255), -1)

            # Canvas更新
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 50 and ch > 50:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
                ratio = min(cw/w, ch/h)
                new_size = (int(w*ratio), int(h*ratio))
                pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
                
                self.tk_img = ImageTk.PhotoImage(pil_img)
                self.canvas.itemconfig(self.image_item, image=self.tk_img)
                self.canvas.coords(self.image_item, (cw-new_size[0])//2, (ch-new_size[1])//2)

        if self.is_running:
            self.root.after(30, self.update_loop)

    def on_closing(self):
        self.is_running = False
        self.cap.release()
        if self.engine.audio_stream:
            self.engine.audio_stream.stop_stream()
            self.engine.audio_stream.close()
        self.engine.p.terminate()
        self.root.destroy()
        sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = LieDetectorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()