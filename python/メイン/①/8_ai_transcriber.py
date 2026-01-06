# AI議事録作成ツール
# インストール: pip install SpeechRecognition tkinter pillow
# 実行方法: python 8_ai_transcriber.py
# Select Interpreter: Python 3.11.9

import speech_recognition as sr
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk
import datetime
import os
import sys
import threading
import time

class AITranscriberApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI議事録作成ツール ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.SAFE_COLOR = "#2ECC71"        # 緑
        self.ALERT_COLOR = "#E74C3C"       # 赤
        self.TEXT_COLOR = "#4B4B4B"
        self.BG_WHITE = "#FFFFFF"

        # --- 既存システムの継承設定 ---
        self.language = 'ja-JP' 
        self.energy_threshold = 300 
        self.dynamic_energy_threshold = True
        self.save_dir = "minutes_log"
        os.makedirs(self.save_dir, exist_ok=True)
        
        # ファイル名の準備
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filename = os.path.join(self.save_dir, f"議事録_{timestamp}.txt")

        # 音声認識器の初期化
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = self.energy_threshold
        self.recognizer.dynamic_energy_threshold = self.dynamic_energy_threshold
        
        # 状態管理
        self.is_recording = False
        self.stop_listening = None # 背景リスニング停止用関数
        self.mic = None
        
        # マイクの初期チェック
        try:
            self.mic = sr.Microphone()
        except Exception as e:
            messagebox.showerror("マイクエラー", f"マイクの初期化に失敗しました: {e}\nPyAudioがインストールされているか確認してください。")

        self.setup_ui()
        self._write_to_file(f"【会議議事録】開始時刻: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🎙️ AI議事録作成ツール", 
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

        # 録音開始/停止ボタン
        self.toggle_btn = tk.Button(self.left_panel, text="録音を開始する ▶", 
                                   command=self.toggle_recording,
                                   bg=self.SAFE_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                   relief=tk.FLAT, cursor="hand2", pady=15)
        self.toggle_btn.pack(fill=tk.X, pady=(0, 10))

        # ステータス表示
        status_frame = tk.LabelFrame(self.left_panel, text=" 📊 システム状態 ", 
                                    font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, pady=10)
        
        self.status_label = tk.Label(status_frame, text="待機中", bg=self.BG_WHITE, 
                                    font=("Meiryo", 14, "bold"), fg=self.TEXT_COLOR, pady=10)
        self.status_label.pack()

        # 保存情報
        info_frame = tk.LabelFrame(self.left_panel, text=" 📂 保存先情報 ", 
                                  font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                  fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        info_frame.pack(fill=tk.X, pady=10)
        
        file_info = f"保存フォルダ:\n{self.save_dir}\n\n現在のファイル:\n{os.path.basename(self.filename)}"
        tk.Label(info_frame, text=file_info, bg=self.BG_WHITE, justify=tk.LEFT, 
                 font=("Meiryo", 9), padx=10, pady=10, wraplength=280).pack(anchor="w")

        # ガイド
        hint_label = tk.Label(self.left_panel, text="ヒント:\n話し終わると自動的に\nテキスト化されます。\n静かな環境が理想的です。", 
                             bg="#FFFBEB", fg="#95A5A6", font=("Meiryo", 9), justify=tk.LEFT)
        hint_label.pack(side=tk.BOTTOM, pady=10)

        # --- 右側：議事録表示エリア ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        log_frame = tk.LabelFrame(self.right_panel, text=" 📜 リアルタイム議事録 ", 
                                 font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.transcript_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 11), 
                                                        bg=self.BG_WHITE, relief=tk.FLAT,
                                                        fg=self.TEXT_COLOR, state=tk.DISABLED,
                                                        padx=15, pady=15)
        self.transcript_area.pack(fill=tk.BOTH, expand=True)

    def _write_to_file(self, text):
        """既存のファイル追記ロジック"""
        try:
            with open(self.filename, "a", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            print(f"File Error: {e}")

    def update_transcript(self, text):
        """画面にテキストを追記"""
        self.transcript_area.config(state=tk.NORMAL)
        self.transcript_area.insert(tk.END, text + "\n")
        self.transcript_area.see(tk.END)
        self.transcript_area.config(state=tk.DISABLED)

    def toggle_recording(self):
        """録音の開始/停止を切り替え"""
        if not self.mic:
            messagebox.showerror("エラー", "マイクが利用できません。")
            return

        if not self.is_recording:
            # 録音開始
            self.is_recording = True
            self.toggle_btn.config(text="録音を停止する ⏹", bg=self.ALERT_COLOR)
            self.status_label.config(text="🎤 録音中...", fg=self.ALERT_COLOR)
            
            # 環境音調整を別スレッドで実行
            threading.Thread(target=self.start_background_listening, daemon=True).start()
        else:
            # 録音停止
            self.is_recording = False
            if self.stop_listening:
                self.stop_listening(wait_for_stop=False)
            self.toggle_btn.config(text="録音を開始する ▶", bg=self.SAFE_COLOR)
            self.status_label.config(text="待機中", fg=self.TEXT_COLOR)

    def start_background_listening(self):
        """既存のバックグラウンドリスニングのセットアップ"""
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        
        # コールバック関数を指定して開始
        self.stop_listening = self.recognizer.listen_in_background(self.mic, self._callback)

    def _callback(self, recognizer, audio):
        """既存の音声認識コールバックロジック"""
        try:
            # 音声認識の実行
            text = recognizer.recognize_google(audio, language=self.language)
            
            timestamp_str = datetime.datetime.now().strftime("[%H:%M:%S]")
            log_text = f"{timestamp_str} {text}"
            
            # UI更新 (Tkinterのメインスレッドで実行)
            self.root.after(0, lambda: self.update_transcript(log_text))
            
            # ファイル保存
            self._write_to_file(log_text + "\n")

        except sr.UnknownValueError:
            pass # 認識不能時は無視
        except Exception as e:
            error_msg = f"【エラー】: {e}"
            self.root.after(0, lambda: self.update_transcript(error_msg))

    def on_closing(self):
        """終了時の処理"""
        if self.is_recording and self.stop_listening:
            self.stop_listening(wait_for_stop=False)
        self._write_to_file(f"\n【終了時刻】: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    # Windows高DPI対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = AITranscriberApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()