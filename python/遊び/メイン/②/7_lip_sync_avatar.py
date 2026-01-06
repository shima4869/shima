# AI口パクアバター（表情強化版）
# インストール: pip install numpy pyaudio Pillow
# 実行方法: python 7_lip_sync_avatar.py
# Select Interpreter: Python 3.11.9

import tkinter as tk
from tkinter import messagebox
import numpy as np
import pyaudio
import threading
import time
import random
from PIL import Image, ImageDraw, ImageTk
import os

class AudioHandler:
    """マイク入力をリアルタイムで解析するクラス"""
    def __init__(self, callback):
        self.callback = callback
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.is_running = False

    def start(self):
        try:
            self.stream = self.p.open(format=self.FORMAT,
                                     channels=self.CHANNELS,
                                     rate=self.RATE,
                                     input=True,
                                     frames_per_buffer=self.CHUNK)
            self.is_running = True
            threading.Thread(target=self._listen, daemon=True).start()
        except Exception as e:
            raise Exception(f"マイクの初期化に失敗しました: {e}")

    def stop(self):
        self.is_running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()

    def _listen(self):
        while self.is_running:
            try:
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                y = np.frombuffer(data, dtype=np.int16) / 32768.0
                
                # 音量チェック
                volume = np.linalg.norm(y)
                if volume < 0.25: # 閾値（少し感度を上げました）
                    self.callback("n", volume)
                    continue

                # 周波数解析 (FFT)
                fft_data = np.abs(np.fft.rfft(y))
                freqs = np.fft.rfftfreq(len(y), 1.0/self.RATE)
                
                f1_range = (freqs > 200) & (freqs < 1000)
                f2_range = (freqs > 800) & (freqs < 3000)
                
                if not any(f1_range) or not any(f2_range):
                    self.callback("n", volume)
                    continue

                f1_peak = freqs[f1_range][np.argmax(fft_data[f1_range])]
                f2_peak = freqs[f2_range][np.argmax(fft_data[f2_range])]

                vowel = self._estimate_vowel(f1_peak, f2_peak)
                self.callback(vowel, volume)
                
            except Exception:
                break

    def _estimate_vowel(self, f1, f2):
        if f1 > 600:
            return "a"
        elif f2 > 1800:
            return "i" if f1 < 450 else "e"
        elif f2 < 1300:
            return "u" if f1 < 450 else "o"
        else:
            return "a"

class AvatarApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI口パクアバター（表情強化版） ✨")
        self.root.geometry("1000x850")
        self.root.configure(bg="#FDFCF0")

        # カラー設定
        self.BODY_COLOR = "#FFFFFF"
        self.EYE_COLOR = "#333333"
        self.CHEEK_COLOR = "#FFB7C5"
        self.LIMB_COLOR = "#FFD54F"
        self.TEXT_COLOR = "#5D4037"

        self.current_vowel = "n"
        self.current_volume = 0.0
        
        # 表情制御用
        self.blink_state = False
        self.last_blink_time = time.time()
        self.blink_duration = 0.15
        self.next_blink_interval = random.uniform(2, 5)
        
        self.setup_ui()
        self.audio = AudioHandler(self.update_vowel)
        
        try:
            self.audio.start()
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def setup_ui(self):
        tk.Label(self.root, text="🎙️ AI表情アバター", 
                 font=("Meiryo", 24, "bold"), bg="#FDFCF0", fg=self.TEXT_COLOR).pack(pady=20)

        self.main_container = tk.Frame(self.root, bg="#FDFCF0")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)

        self.left_panel = tk.Frame(self.main_container, bg="#FDFCF0", width=250)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        self.left_panel.pack_propagate(False)

        info_frame = tk.LabelFrame(self.left_panel, text=" 💡 状態 ", font=("Meiryo", 10, "bold"),
                                  bg="white", fg=self.TEXT_COLOR, relief=tk.RIDGE, bd=2)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        self.vowel_label = tk.Label(info_frame, text="判定: -", bg="white", 
                                   font=("Meiryo", 18, "bold"), fg=self.TEXT_COLOR, pady=20)
        self.vowel_label.pack()

        instructions = (
            "あ：大きく口を開ける\n"
            "い：横に広げる\n"
            "う：すぼめる\n"
            "え：驚いた目\n"
            "お：口を丸くする\n\n"
            "声の大きさに合わせて\n"
            "ほっぺが赤くなります！"
        )
        tk.Label(self.left_panel, text=instructions, bg="#FDFCF0", justify=tk.LEFT, 
                 font=("Meiryo", 10), fg=self.TEXT_COLOR).pack(pady=20)

        self.right_panel = tk.Frame(self.main_container, bg="white", relief=tk.RIDGE, bd=2)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.right_panel, bg="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.update_display()

    def update_vowel(self, vowel, volume):
        self.current_vowel = vowel
        self.current_volume = volume
        v_map = {"a":"あ", "i":"い", "u":"う", "e":"え", "o":"お", "n":"ん"}
        self.vowel_label.config(text=f"判定: {v_map.get(vowel, '-')}")

    def manage_blinking(self):
        """まばたきロジックの管理"""
        now = time.time()
        if not self.blink_state:
            if now - self.last_blink_time > self.next_blink_interval:
                self.blink_state = True
                self.last_blink_time = now
        else:
            if now - self.last_blink_time > self.blink_duration:
                self.blink_state = False
                self.last_blink_time = now
                self.next_blink_interval = random.uniform(2, 6)

    def draw_avatar(self, canvas_w, canvas_h):
        self.manage_blinking()
        img = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        # 音量に応じた揺れ（バウンス）
        bounce = min(int(self.current_volume * 15), 10) if self.current_vowel != "n" else 0
        cx, cy = canvas_w // 2, (canvas_h // 2) - bounce
        
        # 手足
        draw.ellipse([cx-80, cy+130, cx-30, cy+170], fill=self.LIMB_COLOR, outline="#4B4B4B", width=2)
        draw.ellipse([cx+30, cy+130, cx+80, cy+170], fill=self.LIMB_COLOR, outline="#4B4B4B", width=2)
        draw.ellipse([cx-170, cy+30, cx-120, cy+70], fill=self.LIMB_COLOR, outline="#4B4B4B", width=2)
        draw.ellipse([cx+120, cy+30, cx+170, cy+70], fill=self.LIMB_COLOR, outline="#4B4B4B", width=2)

        # 体
        draw.ellipse([cx-150, cy-150, cx+150, cy+150], fill=self.BODY_COLOR, outline="#4B4B4B", width=3)
        
        # 眉毛の描画
        eyebrow_y = cy - 60
        def draw_eyebrow(ex, ey, side="L"):
            # 母音によって角度を変える
            angle = 0
            if self.current_vowel == "a": angle = -15 if side=="L" else 15
            elif self.current_vowel == "i": angle = 10 if side=="L" else -10
            elif self.current_vowel == "e": angle = -20 if side=="L" else 20
            
            offset = 15 if side=="L" else -15
            draw.line([ex-20, ey+offset, ex+20, ey-offset], fill=self.EYE_COLOR, width=3)

        draw_eyebrow(cx-55, eyebrow_y, "L")
        draw_eyebrow(cx+55, eyebrow_y, "R")

        # 瞳の描画
        eye_y = cy - 20
        def draw_eye(ex, ey):
            if self.blink_state and self.current_vowel == "n":
                # まばたき（線）
                draw.line([ex-15, ey-10, ex+15, ey-10], fill=self.EYE_COLOR, width=3)
            else:
                # 母音による目の形
                width = 10
                height = 20
                if self.current_vowel == "a": height = 25; width = 12 # 開く
                elif self.current_vowel == "i": height = 12; width = 14 # 笑顔っぽく
                elif self.current_vowel == "e": height = 28; width = 13 # 驚き
                
                draw.ellipse([ex-width, ey-height, ex+width, ey+height], fill=self.EYE_COLOR)

        draw_eye(cx-55, eye_y)
        draw_eye(cx+55, eye_y)

        # ほっぺ（音量でサイズと色が変化）
        cheek_y = cy + 10
        vol_bonus = min(int(self.current_volume * 40), 20)
        c_size = 15 + vol_bonus
        draw.ellipse([cx-100-c_size, cheek_y-c_size, cx-100+c_size, cheek_y+c_size], fill=self.CHEEK_COLOR)
        draw.ellipse([cx+100-c_size, cheek_y-c_size, cx+100+c_size, cheek_y+c_size], fill=self.CHEEK_COLOR)
        
        # 口の描画
        m_top = cy + 25
        mouth_color = "#FF8A80"
        
        if self.current_vowel == "a": # あ
            draw.ellipse([cx-30, m_top, cx+30, m_top+60], fill=mouth_color, outline="#4B4B4B", width=2)
        elif self.current_vowel == "i": # い
            draw.chord([cx-45, m_top, cx+45, m_top+25], 0, 180, fill=mouth_color, outline="#4B4B4B", width=2)
        elif self.current_vowel == "u": # う
            draw.ellipse([cx-12, m_top+5, cx+12, m_top+35], fill=mouth_color, outline="#4B4B4B", width=2)
        elif self.current_vowel == "e": # え
            draw.ellipse([cx-40, m_top, cx+40, m_top+40], fill=mouth_color, outline="#4B4B4B", width=2)
        elif self.current_vowel == "o": # お
            draw.ellipse([cx-25, m_top, cx+25, m_top+75], fill=mouth_color, outline="#4B4B4B", width=2)
        else: # ん
            draw.arc([cx-15, m_top, cx, m_top+15], 0, 180, fill="#4B4B4B", width=3)
            draw.arc([cx, m_top, cx+15, m_top+15], 0, 180, fill="#4B4B4B", width=3)
            
        return ImageTk.PhotoImage(img)

    def update_display(self):
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        
        if cw > 10 and ch > 10:
            self.tk_img = self.draw_avatar(cw, ch)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
            
        self.root.after(30, self.update_display)

    def on_closing(self):
        self.audio.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = AvatarApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()