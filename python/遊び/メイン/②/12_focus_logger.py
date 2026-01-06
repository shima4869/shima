# AI集中力モニター ✨
# インストール: pip install opencv-python mediapipe pillow numpy
# 実行方法: python 12_focus_logger.py
# Select Interpreter: Python 3.11.9

import cv2
import mediapipe as mp
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import threading
import time
import datetime
import os
import sys

class FocusLoggerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI集中力モニター ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数 (シリーズ統一)
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"        # 緑
        self.ALERT_COLOR = "#E74C3C"       # 赤

        # --- MediaPipe Face Meshの初期化 ---
        try:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=False, 
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        except Exception as e:
            error_msg = str(e)
            advice = ""
            if "parse" in error_msg.lower() or "calculator" in error_msg.lower():
                advice = "\n\n【原因の可能性】\nプログラムの保存場所に「日本語」が含まれていると起動できません。\n「C:\\dev\\」のような半角英数字のみのフォルダに移動して試してください。"
            
            messagebox.showerror("AI初期化エラー", f"MediaPipeの起動に失敗しました。\n\n詳細: {e}{advice}")
            sys.exit(1)

        # カメラ初期化
        self.cap = cv2.VideoCapture(0)
        self.is_running = True
        self.is_monitoring = False
        
        # 統計データ
        self.total_seconds = 0
        self.focused_seconds = 0
        self.blink_count = 0
        self.score = 100
        
        # 解析用一時変数
        self.eye_closed = False
        self.last_update_time = time.time()
        
        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="👁️ AI集中力モニター (Focus Logger)", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=4)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：統計・操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 1. 集中度スコア
        score_frame = tk.LabelFrame(self.left_panel, text=" 📊 現在の集中度 ", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        score_frame.pack(fill=tk.X, pady=5)

        self.score_label = tk.Label(score_frame, text="100 点", bg=self.BG_WHITE, 
                                   font=("Meiryo", 48, "bold"), fg=self.SAFE_COLOR)
        self.score_label.pack(pady=10)

        # 2. 解析ログ
        stats_frame = tk.LabelFrame(self.left_panel, text=" 📝 解析ログ ", 
                                   font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        stats_frame.pack(fill=tk.X, pady=5)
        
        self.lbl_blink = tk.Label(stats_frame, text="まばたき: 0 回", bg=self.BG_WHITE, font=("Meiryo", 11), fg=self.TEXT_COLOR)
        self.lbl_blink.pack(anchor="w", padx=15, pady=5)

        self.lbl_time = tk.Label(stats_frame, text="経過時間: 00:00", bg=self.BG_WHITE, font=("Meiryo", 11), fg=self.TEXT_COLOR)
        self.lbl_time.pack(anchor="w", padx=15, pady=5)

        self.lbl_status = tk.Label(stats_frame, text="状態: 待機中", bg=self.BG_WHITE, font=("Meiryo", 11, "bold"), fg="#95A5A6")
        self.lbl_status.pack(anchor="w", padx=15, pady=5)

        # 3. 操作ガイドパネル (修正箇所: LabelからLabelFrameへ変更し配置を固定)
        guide_frame = tk.LabelFrame(self.left_panel, text=" 💡 操作ガイド ", 
                                   font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        guide_frame.pack(fill=tk.X, pady=5)
        
        guide_text = "・起動できない場合は、日本語を含まない\n　フォルダへ移動させてください。\n・正面を向いている時間をAIが計測します。"
        guide_label = tk.Label(guide_frame, text=guide_text, bg=self.BG_WHITE, justify=tk.LEFT, 
                               font=("Meiryo", 9), fg=self.TEXT_COLOR, padx=10, pady=10)
        guide_label.pack(fill=tk.X)

        # 4. 操作ボタン
        self.ctrl_btn = tk.Button(self.left_panel, text="計測を開始する ▶", 
                                 command=self.toggle_monitoring,
                                 bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                 relief=tk.FLAT, cursor="hand2", pady=15)
        self.ctrl_btn.pack(fill=tk.X, pady=(10, 5))

        self.reset_btn = tk.Button(self.left_panel, text="リセット 🔄", 
                                  command=self.reset_stats,
                                  bg="#BDC3C7", fg="white", font=("Meiryo", 10),
                                  relief=tk.FLAT, cursor="hand2", pady=8)
        self.reset_btn.pack(fill=tk.X, pady=5)

        # --- 右側：カメラプレビュー ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ 集中トラッキング画面 ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def toggle_monitoring(self):
        if not self.is_monitoring:
            self.is_monitoring = True
            self.ctrl_btn.config(text="計測を停止する ⏹", bg=self.ALERT_COLOR)
            self.lbl_status.config(text="状態: 計測中...", fg=self.SAFE_COLOR)
        else:
            self.is_monitoring = False
            self.ctrl_btn.config(text="計測を開始する ▶", bg=self.PRIMARY_COLOR)
            self.lbl_status.config(text="状態: 停止中", fg="#95A5A6")

    def reset_stats(self):
        self.total_seconds = 0
        self.focused_seconds = 0
        self.blink_count = 0
        self.score = 100
        self.update_ui_stats()

    def get_ear(self, landmarks, eye_indices):
        """目のアスペクト比(EAR)を計算"""
        p = landmarks
        v1 = np.linalg.norm(np.array([p[eye_indices[1]].x - p[eye_indices[5]].x, p[eye_indices[1]].y - p[eye_indices[5]].y]))
        v2 = np.linalg.norm(np.array([p[eye_indices[2]].x - p[eye_indices[4]].x, p[eye_indices[2]].y - p[eye_indices[4]].y]))
        h = np.linalg.norm(np.array([p[eye_indices[0]].x - p[eye_indices[3]].x, p[eye_indices[0]].y - p[eye_indices[3]].y]))
        return (v1 + v2) / (2.0 * h + 1e-6)

    def analyze_focus(self, face_landmarks):
        """集中状態の解析"""
        left_eye = [362, 385, 387, 263, 373, 380]
        right_eye = [33, 160, 158, 133, 153, 144]
        
        ear_l = self.get_ear(face_landmarks.landmark, left_eye)
        ear_r = self.get_ear(face_landmarks.landmark, right_eye)
        ear = (ear_l + ear_r) / 2.0

        if ear < 0.18:
            if not self.eye_closed:
                self.blink_count += 1
                self.eye_closed = True
        else:
            self.eye_closed = False

        nose = face_landmarks.landmark[1]
        is_looking = 0.35 < nose.x < 0.65 # 正面判定
        
        return is_looking

    def update_ui_stats(self):
        self.score_label.config(text=f"{int(self.score)} 点")
        if self.score > 80: self.score_label.config(fg=self.SAFE_COLOR)
        elif self.score > 40: self.score_label.config(fg="#F39C12")
        else: self.score_label.config(fg=self.ALERT_COLOR)

        self.lbl_blink.config(text=f"まばたき: {self.blink_count} 回")
        mins, secs = divmod(int(self.total_seconds), 60)
        self.lbl_time.config(text=f"経過時間: {mins:02d}:{secs:02d}")

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb_frame)
            
            status_text = "NO FACE"
            status_color = (127, 127, 127)

            if results.multi_face_landmarks:
                face_landmarks = results.multi_face_landmarks[0]
                is_looking = self.analyze_focus(face_landmarks)
                
                if is_looking:
                    status_text = "FOCUSING"
                    status_color = (46, 204, 113) 
                else:
                    status_text = "LOOKING AWAY"
                    status_color = (231, 76, 60) 

                if self.is_monitoring:
                    current_time = time.time()
                    elapsed = current_time - self.last_update_time
                    self.total_seconds += elapsed
                    if is_looking: self.focused_seconds += elapsed
                    if self.total_seconds > 0:
                        self.score = (self.focused_seconds / self.total_seconds) * 100
                    self.update_ui_stats()
                
                for idx in [1, 33, 133, 362, 263]: 
                    pt = face_landmarks.landmark[idx]
                    cv2.circle(frame, (int(pt.x * w), int(pt.y * h)), 3, status_color, -1)

            cv2.rectangle(frame, (0, 0), (250, 60), (0,0,0), -1)
            cv2.putText(frame, status_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
            
            self.last_update_time = time.time()

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
        if self.cap.isOpened(): self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    app = FocusLoggerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()