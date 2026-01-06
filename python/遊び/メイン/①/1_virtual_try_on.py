# バーチャル試着室 AI
# インストール: pip install opencv-python mediapipe pillow numpy
# 実行方法: python 1_virtual_try_on.py
# Select Interpreter: Python 3.11.9

import cv2
import sys

# 必要なライブラリのインポートチェック
try:
    import mediapipe as mp
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont, ImageTk
except ImportError as e:
    print(f"【エラー】必要なライブラリが見つかりません: {e}")
    print("以下のコマンドを実行してください:")
    print("pip install opencv-python mediapipe pillow numpy")
    sys.exit()

import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
import os
import time

class VirtualTryOnApp:
    def __init__(self, root):
        self.root = root
        self.root.title("バーチャル試着室 ✨")
        self.root.geometry("1500x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"
        self.SECONDARY_COLOR = "#FFCC33"
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"

        # MediaPipe Face Meshの初期化
        try:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.7
            )
        except Exception as e:
            messagebox.showerror("AIエラー", f"MediaPipeの初期化に失敗しました: {e}")
            sys.exit()

        # カメラ設定
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(1)

        # 状態管理
        self.is_running = True
        self.active_items = {"glasses": False, "hat": False, "earrings": False}
        self.item_styles = {"glasses": 0, "hat": 0, "earrings": 0}

        self.setup_ui()
        
        if not self.cap.isOpened():
            self.write_log("【警告】カメラが見つかりません。")
            messagebox.showwarning("カメラ警告", "カメラが認識されませんでした。")
        
        self.update_loop()

    def setup_ui(self):
        title_label = tk.Label(self.root, text="🕶️ バーチャル試着室 AI", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=5)
        self.main_container.rowconfigure(0, weight=1)

        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=300)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        items_frame = tk.LabelFrame(self.left_panel, text=" 🛍️ アイテムを選ぶ ", 
                                   font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        items_frame.pack(fill=tk.X, pady=(0, 10))

        self.create_item_ctrl(items_frame, "glasses", "メガネ")
        self.create_item_ctrl(items_frame, "hat", "帽子")
        self.create_item_ctrl(items_frame, "earrings", "イヤリング")

        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 試着ログ ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.write_log("システム準備完了。")

        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 🖼️ 試着プレビュー ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def create_item_ctrl(self, parent, key, label):
        frame = tk.Frame(parent, bg=self.BG_WHITE)
        frame.pack(fill=tk.X, padx=10, pady=5)

        btn = tk.Button(frame, text=f"{label}: OFF", 
                        command=lambda k=key: self.toggle_item(k),
                        bg="#F7F7F7", font=("Meiryo", 9, "bold"), pady=8, 
                        relief=tk.FLAT, cursor="hand2")
        btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        style_btn = tk.Button(frame, text="🎨", 
                             command=lambda k=key: self.change_style(k),
                             bg="#FFFBEB", font=("Meiryo", 9), width=3, cursor="hand2")
        style_btn.pack(side=tk.RIGHT, padx=(5, 0))

        if key == "glasses": self.glasses_btn = btn
        elif key == "hat": self.hat_btn = btn
        elif key == "earrings": self.earrings_btn = btn

    def write_log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def toggle_item(self, item_key):
        self.active_items[item_key] = not self.active_items[item_key]
        status = "ON" if self.active_items[item_key] else "OFF"
        btns = {"glasses": (self.glasses_btn, "メガネ"), "hat": (self.hat_btn, "帽子"), "earrings": (self.earrings_btn, "イヤリング")}
        btn, label = btns[item_key]
        btn.config(text=f"{label}: {status}", bg=self.PRIMARY_COLOR if status == "ON" else "#F7F7F7", fg="white" if status == "ON" else self.TEXT_COLOR)
        self.write_log(f"{label} を {status} にしました。")

    def change_style(self, item_key):
        self.item_styles[item_key] = (self.item_styles[item_key] + 1) % 2
        names = {"glasses": ["ブラック", "レッド"], "hat": ["クラシックレッド", "ミッドナイトブルー"], "earrings": ["パール", "クリスタル"]}
        label = {"glasses": "メガネ", "hat": "帽子", "earrings": "イヤリング"}[item_key]
        self.write_log(f"{label} を {names[item_key][self.item_styles[item_key]]} に変更。")

    def draw_accessories(self, pil_img, landmarks, w, h):
        draw = ImageDraw.Draw(pil_img, "RGBA")
        
        # 主要なランドマーク
        p_nose = landmarks[1]
        p_left_eye = landmarks[33]
        p_right_eye = landmarks[263]
        p_bridge = landmarks[168]
        p_forehead = landmarks[10]
        p_left_cheek = landmarks[234]
        p_right_cheek = landmarks[454]
        
        # 1. メガネ
        if self.active_items["glasses"]:
            eye_dist = np.sqrt((p_right_eye.x - p_left_eye.x)**2 + (p_right_eye.y - p_left_eye.y)**2) * w
            angle = np.degrees(np.arctan2(p_right_eye.y - p_left_eye.y, p_right_eye.x - p_left_eye.x))
            g_w, g_h = eye_dist * 1.8, eye_dist * 0.7
            frame_color = (20, 20, 20, 255) if self.item_styles["glasses"] == 0 else (180, 20, 20, 255)
            overlay = Image.new("RGBA", (int(g_w * 2), int(g_h * 3)), (0, 0, 0, 0))
            d = ImageDraw.Draw(overlay)
            ox, oy = g_w, g_h * 1.5
            d.ellipse([ox - g_w*0.45, oy - g_h*0.45, ox - g_w*0.05, oy + g_h*0.45], outline=frame_color, width=6)
            d.ellipse([ox + g_w*0.05, oy - g_h*0.45, ox + g_w*0.45, oy + g_h*0.45], outline=frame_color, width=6)
            d.line([ox - g_w*0.05, oy, ox + g_w*0.05, oy], fill=frame_color, width=5)
            rotated = overlay.rotate(-angle, expand=True, resample=Image.BICUBIC)
            pil_img.paste(rotated, (int(p_bridge.x*w - rotated.width/2), int(p_bridge.y*h - rotated.height/2)), rotated)

        # 2. 帽子
        if self.active_items["hat"]:
            face_width = np.sqrt((p_right_cheek.x - p_left_cheek.x)**2 + (p_right_cheek.y - p_left_cheek.y)**2) * w
            angle = np.degrees(np.arctan2(p_right_cheek.y - p_left_cheek.y, p_right_cheek.x - p_left_cheek.x))
            hat_w, hat_h = int(face_width * 1.5), int(face_width * 0.9)
            offset_dist = int(face_width * 0.5)
            rad_offset = np.radians(angle - 90)
            center_x = int(p_forehead.x * w + offset_dist * np.cos(rad_offset))
            center_y = int(p_forehead.y * h + offset_dist * np.sin(rad_offset))
            
            canvas_size = int(hat_w * 1.5)
            overlay = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
            d = ImageDraw.Draw(overlay)
            cx, cy = canvas_size // 2, canvas_size // 2
            hat_color = (140, 40, 40, 255) if self.item_styles["hat"] == 0 else (40, 40, 140, 255)
            ribbon_color = (20, 20, 20, 255)
            
            pts_crown = [(cx - int(hat_w * 0.25), cy + int(hat_h * 0.4)), (cx + int(hat_w * 0.25), cy + int(hat_h * 0.4)), (cx + int(hat_w * 0.20), cy - int(hat_h * 0.4)), (cx - int(hat_w * 0.20), cy - int(hat_h * 0.4))]
            d.polygon(pts_crown, fill=hat_color)
            base_rect = [cx - int(hat_w * 0.5), cy + int(hat_h * 0.3), cx + int(hat_w * 0.5), cy + int(hat_h * 0.5)]
            d.ellipse(base_rect, fill=hat_color)
            pts_ribbon = [(cx - int(hat_w * 0.25), cy + int(hat_h * 0.4)), (cx + int(hat_w * 0.25), cy + int(hat_h * 0.4)), (cx + int(hat_w * 0.24), cy + int(hat_h * 0.25)), (cx - int(hat_w * 0.24), cy + int(hat_h * 0.25))]
            d.polygon(pts_ribbon, fill=ribbon_color)
            
            rotated_hat = overlay.rotate(-angle, expand=True, resample=Image.BICUBIC)
            pil_img.paste(rotated_hat, (int(center_x - rotated_hat.width/2), int(center_y - rotated_hat.height/2)), rotated_hat)

        # 3. イヤリング (修正版: 耳の高さに正確に調整)
        if self.active_items["earrings"]:
            # 顔のスケールを取得
            face_scale = np.sqrt((p_right_cheek.x - p_left_cheek.x)**2 + (p_right_cheek.y - p_left_cheek.y)**2) * w
            size = int(face_scale * 0.08)
            
            # アンカーポイント (127: 左耳境界, 356: 右耳境界)
            # 顔の輪郭線上にあるポイントを使用することで、耳の高さを正確に捉えます
            anchors = [
                (landmarks[127], -1), # 左耳
                (landmarks[356], 1)   # 右耳
            ]
            
            for landmark, side_dir in anchors:
                # 髪や輪郭に重なるよう、わずかに外側へオフセット
                offset_x = side_dir * (face_scale * 0.02)
                # 高さをランドマーク(耳の付け根)に正確に一致させる
                ex = landmark.x * w + offset_x
                ey = landmark.y * h
                
                if self.item_styles["earrings"] == 0: # パール
                    # 耳から吊り下がっているように描画位置を調整
                    draw.ellipse([ex - size*0.5, ey, ex + size*0.5, ey + size*1.0], fill=(245, 245, 240, 255), outline=(180, 180, 170, 255))
                    draw.ellipse([ex - size*0.3, ey + size*0.1, ex - size*0.1, ey + size*0.4], fill=(255, 255, 255, 255))
                else: # クリスタル
                    color = (135, 206, 250, 180)
                    # クリスタルの先端を耳の高さに合わせる
                    points = [(ex, ey), (ex - size*0.6, ey + size*0.8), (ex, ey + size*2.2), (ex + size*0.6, ey + size*0.8)]
                    draw.polygon(points, fill=color, outline=(255, 255, 255, 255), width=1)
                    draw.line([ex, ey, ex, ey + size*2.2], fill=(255, 255, 255, 150), width=1)

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb_frame)
            pil_img = Image.fromarray(rgb_frame)
            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    self.draw_accessories(pil_img, face_landmarks.landmark, w, h)
            
            self.root.update_idletasks()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 50 and ch > 50:
                fw, fh = pil_img.size
                ratio = min(cw/fw, ch/fh)
                new_size = (int(fw*ratio), int(fh*ratio))
                display_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
                self.tk_img = ImageTk.PhotoImage(display_img)
                self.canvas.delete("all")
                self.canvas.create_image(cw//2, ch//2, anchor=tk.CENTER, image=self.tk_img)

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
    app = VirtualTryOnApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()