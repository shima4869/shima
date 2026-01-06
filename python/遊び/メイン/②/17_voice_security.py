# AI声紋認証セキュリティシステム ✨
# インストール: pip install tkinter pyaudio numpy librosa speechrecognition scipy pillow
# 実行方法: python 17_voice_security.py
# Select Interpreter: Python 3.11.9

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import pyaudio
import numpy as np
import librosa
import speech_recognition as sr
from scipy.spatial.distance import euclidean
from PIL import Image, ImageDraw, ImageTk
import threading
import time
import os
import datetime

# --- 音声設定 ---
FORMAT = pyaudio.paFloat32
CHANNELS = 1
RATE = 22050
CHUNK = 1024

class VoiceAuthEngine:
    """声紋の登録と照合を行うAIエンジン"""
    def __init__(self):
        self.master_mfcc = None
        self.target_phrase = "開けゴマ"
        self.threshold = 15.0 # 距離のしきい値（小さいほど厳格）

    def get_mfcc(self, audio_data):
        """音声データから声紋特徴量(MFCC)を抽出"""
        # MFCCの計算
        mfccs = librosa.feature.mfcc(y=audio_data, sr=RATE, n_mfcc=13)
        # 時間軸で平均化して、その人特有の「声の形」をベクトル化
        return np.mean(mfccs.T, axis=0)

    def register_master(self, audio_data):
        """本人の声をマスターとして登録"""
        self.master_mfcc = self.get_mfcc(audio_data)
        return True

    def verify_speaker(self, audio_data):
        """入力された声が登録者本人か判定"""
        if self.master_mfcc is None:
            return False, 0
        
        current_mfcc = self.get_mfcc(audio_data)
        # ユークリッド距離で「声の近さ」を算出
        dist = euclidean(self.master_mfcc, current_mfcc)
        
        is_owner = dist < self.threshold
        # スコア化 (0-100)
        confidence = max(0, min(100, 100 - (dist * 2.5)))
        return is_owner, confidence

class VoiceSecurityApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI声紋認証セキュリティ ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数 (シリーズ統一デザイン)
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"        # 緑
        self.ALERT_COLOR = "#E74C3C"       # 赤

        # エンジン初期化
        self.auth = VoiceAuthEngine()
        self.recognizer = sr.Recognizer()
        
        # 状態管理
        self.is_running = True
        self.is_recording = False
        self.door_open = False
        self.door_anim_val = 0 # 0(閉) ～ 100(開)
        self.audio_level = 0
        
        # PyAudio初期化
        self.p = pyaudio.PyAudio()
        
        self.setup_ui()
        
        # 波形とアニメーションの更新ループ
        self.update_graphics_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🔒 AI声紋認証・セキュリティシステム", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：左(操作)1, 右(表示)3
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 1. ユーザー登録
        reg_frame = tk.LabelFrame(self.left_panel, text=" 👤 STEP 1: 管理者登録 ", 
                                 font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        reg_frame.pack(fill=tk.X, pady=(0, 10))

        self.reg_btn = tk.Button(reg_frame, text="本人の声を学習させる 🎤", 
                                command=self.start_registration,
                                bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 11, "bold"),
                                relief=tk.FLAT, cursor="hand2", pady=10)
        self.reg_btn.pack(fill=tk.X, padx=15, pady=15)

        # 2. 認証実行
        auth_frame = tk.LabelFrame(self.left_panel, text=" 🔑 STEP 2: ドア解錠認証 ", 
                                  font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                  fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        auth_frame.pack(fill=tk.X, pady=10)

        self.auth_btn = tk.Button(auth_frame, text="認証を開始 🔓", 
                                 command=self.start_authentication,
                                 bg=self.SAFE_COLOR, fg="white", font=("Meiryo", 14, "bold"),
                                 relief=tk.FLAT, cursor="hand2", pady=15)
        self.auth_btn.pack(fill=tk.X, padx=15, pady=15)

        # ステータス
        self.status_label = tk.Label(self.left_panel, text="状態: 待機中", bg="#FFFBEB", 
                                    font=("Meiryo", 10, "bold"), fg=self.TEXT_COLOR)
        self.status_label.pack(pady=10)

        # ログ
        self.log_area = scrolledtext.ScrolledText(self.left_panel, height=10, font=("Meiryo", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT)
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=10)
        self.write_log("システムを起動しました。")

        # --- 右側：ビジュアルパネル ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        # 映像・シミュレーター
        sim_frame = tk.LabelFrame(self.right_panel, text=" 🚪 バーチャル・セキュリティドア ", 
                                 font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        sim_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(sim_frame, bg="#2C3E50", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def write_log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def record_audio(self, seconds=3):
        """指定秒数音声を録音し、numpy配列を返す"""
        stream = self.p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        frames = []
        for _ in range(0, int(RATE / CHUNK * seconds)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(np.frombuffer(data, dtype=np.float32))
        stream.stop_stream()
        stream.close()
        return np.concatenate(frames)

    def start_registration(self):
        """管理者（本人）の声を登録するスレッドを開始"""
        if self.is_recording: return
        self.is_recording = True
        self.reg_btn.config(state=tk.DISABLED, bg="#BDC3C7", text="録音中...")
        self.status_label.config(text="🎤 「開けゴマ」と3回言ってください...", fg=self.PRIMARY_COLOR)
        
        def _task():
            audio = self.record_audio(seconds=4)
            if self.auth.register_master(audio):
                self.root.after(0, lambda: self.write_log("管理者の声紋登録が完了しました ✅"))
                self.root.after(0, lambda: self.status_label.config(text="状態: 登録済み", fg=self.SAFE_COLOR))
            
            self.is_recording = False
            self.root.after(0, lambda: self.reg_btn.config(state=tk.NORMAL, bg=self.PRIMARY_COLOR, text="本人の声を学習させる 🎤"))

        threading.Thread(target=_task, daemon=True).start()

    def start_authentication(self):
        """認証プロセス（合言葉＋声紋）のスレッドを開始"""
        if self.is_recording: return
        if self.auth.master_mfcc is None:
            messagebox.showwarning("警告", "先に管理者の声を登録してください。")
            return

        self.is_recording = True
        self.auth_btn.config(state=tk.DISABLED, bg="#BDC3C7", text="聞き取り中...")
        self.status_label.config(text="🔐 合言葉をどうぞ...", fg=self.PRIMARY_COLOR)
        
        def _task():
            # 音声収集
            raw_audio = self.record_audio(seconds=3)
            
            # 1. 音声認識 (内容チェック)
            self.write_log("AIが音声を解析中...")
            try:
                # 録音データをSpeechRecognition形式に変換（簡易的にGoogle APIを使用）
                # ここではエラー回避のため、SpeechRecognitionライブラリのlisten機能を利用
                with sr.Microphone() as source:
                    audio_sr = self.recognizer.listen(source, timeout=3, phrase_time_limit=3)
                recognized_text = self.recognizer.recognize_google(audio_sr, language="ja-JP")
                self.write_log(f"聞き取った言葉: 「{recognized_text}」")
            except Exception as e:
                recognized_text = ""
                self.write_log("言葉をうまく聞き取れませんでした。")

            # 2. 認証ロジック
            is_phrase_ok = "開け" in recognized_text and "ゴマ" in recognized_text
            is_owner, confidence = self.auth.verify_speaker(raw_audio)
            
            if is_phrase_ok and is_owner:
                self.root.after(0, self.unlock_door)
                self.write_log(f"本人確認成功 (スコア: {confidence:.1f}%) 🔓")
            else:
                reason = "合言葉が違います" if not is_phrase_ok else f"他人の声です (スコア: {confidence:.1f}%)"
                self.root.after(0, lambda: self.write_log(f"アクセス拒否: {reason} ❌"))
                self.root.after(0, lambda: self.status_label.config(text="状態: アクセス拒否", fg=self.ALERT_COLOR))

            self.is_recording = False
            self.root.after(0, lambda: self.auth_btn.config(state=tk.NORMAL, bg=self.SAFE_COLOR, text="認証を開始 🔓"))

        threading.Thread(target=_task, daemon=True).start()

    def unlock_door(self):
        """解錠処理（アニメーションとサーボ制御の模倣）"""
        self.door_open = True
        self.status_label.config(text="🔓 ウェルカム！ドアを開けます", fg=self.SAFE_COLOR)
        self.write_log("【ハードウェア信号】サーボモータを90度回転(解錠)します。")
        
        # 5秒後に自動で閉める
        self.root.after(5000, self.lock_door)

    def lock_door(self):
        self.door_open = False
        self.write_log("【ハードウェア信号】サーボモータを0度に戻します(施錠)。")
        self.status_label.config(text="状態: 施錠完了", fg=self.TEXT_COLOR)

    def draw_door(self, canvas_w, canvas_h):
        """ドアのビジュアルを描画"""
        self.canvas.delete("all")
        
        # 背景（壁）
        self.canvas.create_rectangle(0, 0, canvas_w, canvas_h, fill="#34495E")
        
        # ドアの枠
        door_w, door_h = 250, 450
        x1, y1 = (canvas_w - door_w)//2, (canvas_h - door_h)//2
        x2, y2 = x1 + door_w, y1 + door_h
        
        # ドアの奥（開いたときに見える中身）
        self.canvas.create_rectangle(x1, y1, x2, y2, fill="#1A252F", outline="")
        if self.door_open:
            self.canvas.create_text(canvas_w//2, canvas_h//2, text="WELCOME!", fill="white", font=("Arial", 20, "bold"))

        # ドア本体（アニメーション）
        # 開く角度に合わせて幅を縮めることで「開いている」ように見せる
        swing_w = door_w * (1 - (self.door_anim_val / 100))
        door_color = self.PRIMARY_COLOR if not self.door_open else self.SECONDARY_COLOR
        
        self.canvas.create_rectangle(x1, y1, x1 + swing_w, y2, fill=door_color, outline="#2C3E50", width=3)
        
        # ドアノブ
        if swing_w > 30:
            knob_x = x1 + swing_w - 30
            knob_y = y1 + door_h//2
            self.canvas.create_oval(knob_x-10, knob_y-10, knob_x+10, knob_y+10, fill="#7F8C8D")

        # セキュリティステータス表示
        status_text = "SYSTEM: LOCKED" if not self.door_open else "SYSTEM: UNLOCKED"
        status_color = "red" if not self.door_open else "#2ECC71"
        self.canvas.create_text(canvas_w//2, y1 - 40, text=status_text, fill=status_color, font=("Consolas", 18, "bold"))

    def update_graphics_loop(self):
        """描画・アニメーションのループ"""
        # ドアのアニメーション
        target_val = 90 if self.door_open else 0
        if self.door_anim_val < target_val: self.door_anim_val += 5
        elif self.door_anim_val > target_val: self.door_anim_val -= 5

        self.root.update_idletasks()
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw > 50:
            self.draw_door(cw, ch)

        if self.is_running:
            self.root.after(30, self.update_graphics_loop)

    def on_closing(self):
        self.is_running = False
        self.p.terminate()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    # Windows高DPI対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = VoiceSecurityApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()