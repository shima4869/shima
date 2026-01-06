# AI手話・音声翻訳機 ✨
# インストール: pip install tkinter requests pillow mediapipe pyaudio numpy opencv-python
# 実行方法: python 13_sign_language_voice_ai.py
# Select Interpreter: Python 3.11.9

import cv2
import mediapipe as mp
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import requests
import json
import threading
import time
import pyaudio
import base64
import os
import sys

class SignVoiceEngine:
    """手話のジェスチャー認識と音声合成(TTS)を行うエンジン"""
    def __init__(self, log_callback):
        self.log_callback = log_callback
        self.api_key = "AIzaSyBzOeROpVGYEC1miK2ukPVeOdE0vEChv8Y" # GUIから取得
        self.tts_model = "gemini-2.5-flash-preview-tts"
        
        # MediaPipe Hands初期化
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        
        # 音声再生設定
        self.p = pyaudio.PyAudio()
        self.voice_name = "Kore" # 日本語ボイス
        
        # 翻訳辞書
        self.GESTURES = {
            "GREETING": "こんにちは",
            "THANKS": "ありがとう",
            "OK": "了解しました",
            "PEACE": "平和",
            "LOVE": "愛しています",
            "PROMISE": "約束"
        }
        
        # 状態管理
        self.last_spoken_text = ""
        self.gesture_stable_frames = 0
        self.required_frames = 15 # 約0.5秒安定したら発話
        self.last_speech_time = 0
        self.speech_cooldown = 2.5 # 連続発話防止

    def _is_finger_up(self, landmarks, finger_idx):
        """指の状態判定（親指〜小指）"""
        tips = [4, 8, 12, 16, 20]
        mcps = [2, 5, 9, 13, 17]
        tip = landmarks[tips[finger_idx]]
        mcp = landmarks[mcps[finger_idx]]
        
        if finger_idx == 0: # 親指
            return abs(tip.x - mcp.x) > 0.05
        return tip.y < mcp.y

    def analyze_gesture(self, hand_landmarks):
        """手の形状から意味を特定"""
        landmarks = hand_landmarks.landmark
        fingers = [self._is_finger_up(landmarks, i) for i in range(5)]
        
        # 判定ロジック
        if all(fingers): return "GREETING"
        if fingers[0] and not any(fingers[1:]): return "THANKS"
        if fingers[1] and fingers[2] and not any([fingers[3], fingers[4]]): return "PEACE"
        if fingers[4] and not any(fingers[0:4]): return "PROMISE"
        
        # OK (親指と人差し指が近い)
        dist_ok = np.sqrt((landmarks[4].x - landmarks[8].x)**2 + (landmarks[4].y - landmarks[8].y)**2)
        if dist_ok < 0.04 and all(fingers[2:]): return "OK"
        
        # I Love You (親指、人差し指、小指)
        if fingers[0] and fingers[1] and fingers[4] and not (fingers[2] or fingers[3]): return "LOVE"
        
        return None

    def speak(self, text, force=False):
        """Gemini TTSを使用して音声を再生"""
        if not self.api_key:
            self.log_callback("⚠️ APIキーが設定されていないため、音声出力できません。")
            return

        now = time.time()
        if not force:
            if text == self.last_spoken_text and (now - self.last_speech_time) < self.speech_cooldown:
                return
            
        self.last_spoken_text = text
        self.last_speech_time = now
        self.log_callback(f"🔊 音声変換中: 「{text}」")
        
        threading.Thread(target=self._tts_request_task, args=(text,), daemon=True).start()

    def _tts_request_task(self, text):
        """APIリクエストと再生を実行するスレッドタスク"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.tts_model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": f"Say: {text}"}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": { "voiceName": self.voice_name }
                    }
                }
            }
        }
        
        try:
            res = requests.post(url, json=payload, timeout=15)
            if res.status_code == 200:
                data = res.json()
                audio_base64 = data['candidates'][0]['content']['parts'][0]['inlineData']['data']
                audio_data = base64.b64decode(audio_base64)
                self._play_audio(audio_data)
                self.log_callback(f"✅ 音声を出力しました: 「{text}」")
            else:
                self.log_callback(f"❌ TTSエラー: {res.status_code} {res.text[:50]}")
        except Exception as e:
            self.log_callback(f"❌ 通信エラー: {str(e)}")

    def _play_audio(self, pcm_data):
        """PCMデータを再生（24000Hz, 1ch, 16bit）"""
        try:
            stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=24000, output=True)
            stream.write(pcm_data)
            stream.stop_stream()
            stream.close()
        except Exception as e:
            self.log_callback(f"❌ 再生デバイスエラー: {e}")

class SignToVoiceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI手話・音声翻訳機 ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"
        self.SECONDARY_COLOR = "#FFCC33"
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"

        self.engine = SignVoiceEngine(self.write_log)
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        
        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        title_label = tk.Label(self.root, text="✋ AI手話・音声翻訳機 (TTS版)", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：翻訳・設定パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 1. APIキー設定
        key_frame = tk.LabelFrame(self.left_panel, text=" 🔑 API設定 (Google AI Studio) ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        key_frame.pack(fill=tk.X, pady=(0, 10))

        self.key_entry = tk.Entry(key_frame, font=("Consolas", 10), show="*", relief=tk.FLAT)
        self.key_entry.pack(fill=tk.X, padx=10, pady=10)
        self.key_entry.bind("<KeyRelease>", self.update_api_key)

        # 2. 翻訳ステータス
        status_frame = tk.LabelFrame(self.left_panel, text=" 👁️ リアルタイム翻訳 ", 
                                    font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, pady=5)

        self.lbl_result = tk.Label(status_frame, text="待機中", bg=self.BG_WHITE, 
                                  font=("Meiryo", 22, "bold"), fg=self.TEXT_COLOR, pady=20)
        self.lbl_result.pack()

        # 3. テストボタン
        self.test_btn = tk.Button(self.left_panel, text="スピーカーテスト 🔊", 
                                 command=lambda: self.engine.speak("テスト再生です", force=True),
                                 bg=self.SECONDARY_COLOR, font=("Meiryo", 10, "bold"), pady=8, relief=tk.FLAT)
        self.test_btn.pack(fill=tk.X, pady=10)

        # 4. ログ
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 システムログ ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.write_log("システムを起動しました。APIキーを入力してください。")

        # --- 右側：カメラプレビュー ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ 解析モニター ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def update_api_key(self, event=None):
        self.engine.api_key = self.key_entry.get().strip()

    def write_log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.engine.hands.process(rgb_frame)
            
            current_gesture_key = None
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp.solutions.drawing_utils.draw_landmarks(
                        frame, hand_landmarks, mp.solutions.hands.HAND_CONNECTIONS)
                    current_gesture_key = self.engine.analyze_gesture(hand_landmarks)

            if current_gesture_key:
                text = self.engine.GESTURES[current_gesture_key]
                self.lbl_result.config(text=text, fg=self.SAFE_COLOR)
                self.engine.gesture_stable_frames += 1
                if self.engine.gesture_stable_frames >= self.engine.required_frames:
                    self.engine.speak(text)
                    self.engine.gesture_stable_frames = 0
            else:
                self.lbl_result.config(text="待機中", fg=self.TEXT_COLOR)
                self.engine.gesture_stable_frames = 0

            # Tkinter表示
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
        self.engine.p.terminate()
        self.root.destroy()
        sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    app = SignToVoiceApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()