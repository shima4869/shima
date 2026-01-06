# ポーズ・テトリス
# インストール: pip install mediapipe opencv-python Pillow numpy
# 実行方法: python 2_pose_tetris.py
# Select Interpreter: Python 3.11.9

import cv2
import mediapipe as mp
import numpy as np
import random
import time
from PIL import Image, ImageDraw, ImageFont
import os

# --- ゲーム定数 ---
GRID_WIDTH = 10
GRID_HEIGHT = 20
FPS = 30

# 落下スピード設定 (秒単位) - 両モード共通でHIGH設定
NORMAL_DROP_INTERVAL = 1.0  # 通常時
FAST_DROP_INTERVAL = 0.1    # 高速落下時 (前傾姿勢時)

# テトリミノのデータ定義
PIECE_DATA = [
    {"shape": [[1, 1, 1, 1]], "color": (255, 255, 50)}, # I: シアン
    {"shape": [[1, 1], [1, 1]], "color": (50, 255, 255)}, # O: イエロー
    {"shape": [[0, 1, 0], [1, 1, 1]], "color": (255, 50, 255)}, # T: パープル
    {"shape": [[0, 1, 1], [1, 1, 0]], "color": (50, 255, 50)},  # S: グリーン
    {"shape": [[1, 1, 0], [0, 1, 1]], "color": (50, 50, 255)},  # Z: レッド
    {"shape": [[1, 0, 0], [1, 1, 1]], "color": (255, 50, 50)},  # J: ブルー
    {"shape": [[0, 0, 1], [1, 1, 1]], "color": (50, 165, 255)} # L: オレンジ
]

FONT_PATHS = [
    "C:\\Windows\\Fonts\\msgothic.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
]

class TetrisLogic:
    def __init__(self):
        self.grid = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.score = 0
        self.game_over = False
        next_data = random.choice(PIECE_DATA)
        self.next_shape = next_data["shape"]
        self.next_color = next_data["color"]
        self.new_piece()

    def new_piece(self):
        self.current_shape = self.next_shape
        self.current_color = self.next_color
        next_data = random.choice(PIECE_DATA)
        self.next_shape = next_data["shape"]
        self.next_color = next_data["color"]
        self.piece_x = GRID_WIDTH // 2 - len(self.current_shape[0]) // 2
        self.piece_y = 0
        if self.check_collision(self.piece_x, self.piece_y, self.current_shape):
            self.game_over = True

    def check_collision(self, x, y, shape):
        for ry, row in enumerate(shape):
            for rx, cell in enumerate(row):
                if cell:
                    if (x + rx < 0 or x + rx >= GRID_WIDTH or
                        y + ry >= GRID_HEIGHT or
                        (y + ry >= 0 and self.grid[y + ry][x + rx])):
                        return True
        return False

    def rotate(self):
        new_shape = list(zip(*self.current_shape[::-1]))
        if not self.check_collision(self.piece_x, self.piece_y, new_shape):
            self.current_shape = new_shape

    def move(self, dx):
        if not self.check_collision(self.piece_x + dx, self.piece_y, self.current_shape):
            self.piece_x += dx

    def drop(self):
        if not self.check_collision(self.piece_x, self.piece_y + 1, self.current_shape):
            self.piece_y += 1
            return True
        else:
            self.lock_piece()
            return False

    def lock_piece(self):
        for ry, row in enumerate(self.current_shape):
            for rx, cell in enumerate(row):
                if cell:
                    if self.piece_y + ry >= 0:
                        self.grid[self.piece_y + ry][self.piece_x + rx] = self.current_color
        self.clear_lines()
        self.new_piece()

    def clear_lines(self):
        new_grid = [row for row in self.grid if any(cell is None for cell in row)]
        cleared = GRID_HEIGHT - len(new_grid)
        self.score += cleared * 100
        for _ in range(cleared):
            new_grid.insert(0, [None for _ in range(GRID_WIDTH)])
        self.grid = new_grid

class PoseTetris:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)
        self.game = TetrisLogic()
        self.last_drop_time = time.time()
        
        self.state = "START_MENU"
        self.is_seated_mode = False
        
        self.prev_move_dir = 0
        self.prev_rotate_state = False
        self.is_fast_drop = False

        self.mouse_pos = (0, 0)
        self.mouse_clicked = False
        
        # フォント初期化
        self.font_vsmall = None
        self.font_small = None
        self.font_mid = None
        self.font_large = None
        self.font_xl = None
        
        for path in FONT_PATHS:
            if os.path.exists(path):
                try:
                    self.font_vsmall = ImageFont.truetype(path, 16)
                    self.font_small = ImageFont.truetype(path, 18)
                    self.font_mid = ImageFont.truetype(path, 24)
                    self.font_large = ImageFont.truetype(path, 40)
                    self.font_xl = ImageFont.truetype(path, 64)
                    break
                except Exception:
                    continue

    def mouse_callback(self, event, x, y, flags, param):
        self.mouse_pos = (x, y)
        if event == cv2.EVENT_LBUTTONDOWN:
            self.mouse_clicked = True

    def get_pose_command(self, results):
        command = {"move": 0, "drop": False, "rotate": False}
        if not results or not results.pose_landmarks:
            return command
            
        lm = results.pose_landmarks.landmark
        l_sh = lm[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        r_sh = lm[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        l_wr = lm[self.mp_pose.PoseLandmark.LEFT_WRIST]
        r_wr = lm[self.mp_pose.PoseLandmark.RIGHT_WRIST]
        nose = lm[self.mp_pose.PoseLandmark.NOSE]
        
        sh_center_x = (l_sh.x + r_sh.x) / 2
        sh_y_avg = (l_sh.y + r_sh.y) / 2
        
        # 1. 左右移動判定 (肩の中心に対する鼻の位置)
        lean_threshold = 0.05 if self.is_seated_mode else 0.08
        if nose.x < sh_center_x - lean_threshold: command["move"] = -1
        elif nose.x > sh_center_x + lean_threshold: command["move"] = 1

        # 2. 高速落下判定 (お辞儀/前傾姿勢)
        if nose.y > sh_y_avg - 0.05:
            command["drop"] = True
            
        # 3. 回転判定 (片手を上げる)
        if not command["drop"]:
            h_threshold = 0.05 if self.is_seated_mode else 0.15
            is_l_up = l_wr.y < l_sh.y - h_threshold
            is_r_up = r_wr.y < r_sh.y - h_threshold
            if is_l_up != is_r_up:
                command["rotate"] = True
                
        return command

    def draw_start_menu(self, frame, results):
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil, "RGBA")
        w, h = img_pil.size
        draw.rectangle([0, 0, w, h], fill=(20, 25, 40, 180))
        
        if self.font_xl:
            draw.text((w//2 - 240, h//2 - 280), "ポーズ・テトリス", font=self.font_xl, fill=(0, 255, 255))
            draw.text((w//2 - 180, h//2 - 180), "あそぶモードをえらんでね！", font=self.font_mid, fill=(255, 255, 255))
            
            screen_left_up, screen_right_up = False, False
            if results and results.pose_landmarks:
                lm = results.pose_landmarks.landmark
                l_wr, r_wr = lm[self.mp_pose.PoseLandmark.LEFT_WRIST], lm[self.mp_pose.PoseLandmark.RIGHT_WRIST]
                l_sh, r_sh = lm[self.mp_pose.PoseLandmark.LEFT_SHOULDER], lm[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
                screen_left_up = r_wr.y < r_sh.y - 0.1
                screen_right_up = l_wr.y < l_sh.y - 0.1

            mx, my = self.mouse_pos
            full_box = [w//2 - 380, h//2 - 60, w//2 - 40, h//2 + 220]
            seated_box = [w//2 + 40, h//2 - 60, w//2 + 380, h//2 + 220]
            mouse_on_full = (full_box[0] <= mx <= full_box[2] and full_box[1] <= my <= full_box[3])
            mouse_on_seated = (seated_box[0] <= mx <= seated_box[2] and seated_box[1] <= my <= seated_box[3])

            f_active = screen_left_up or mouse_on_full
            f_color = (100, 255, 100, 200) if f_active else (50, 100, 50, 160)
            draw.rounded_rectangle(full_box, radius=30, fill=f_color, outline=(255,255,255) if f_active else (120,150,120), width=8 if f_active else 2)
            draw.text((full_box[0]+110, full_box[1]+40), "🚶", font=self.font_xl, fill=(255,255,255))
            draw.text((full_box[0]+95, full_box[1]+130), "全身モード", font=self.font_mid, fill=(255,255,255))
            
            s_active = screen_right_up or mouse_on_seated
            s_color = (100, 180, 255, 200) if s_active else (50, 70, 120, 160)
            draw.rounded_rectangle(seated_box, radius=30, fill=s_color, outline=(255,255,255) if s_active else (120,140,180), width=8 if s_active else 2)
            draw.text((seated_box[0]+110, seated_box[1]+40), "🪑", font=self.font_xl, fill=(255,255,255))
            draw.text((seated_box[0]+95, seated_box[1]+130), "着席モード", font=self.font_mid, fill=(255,255,255))

            if screen_left_up or (self.mouse_clicked and mouse_on_full):
                self.is_seated_mode, self.state, self.mouse_clicked = False, "PLAYING", False
                time.sleep(0.3)
            elif screen_right_up or (self.mouse_clicked and mouse_on_seated):
                self.is_seated_mode, self.state, self.mouse_clicked = True, "PLAYING", False
                time.sleep(0.3)
            if self.mouse_clicked: self.mouse_clicked = False
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    def draw_ui(self, frame, score, game_over):
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil, "RGBA")
        w, h = img_pil.size # 幅と高さを取得
        
        ui_box = [20, 20, 260, 410]
        draw.rectangle(ui_box, fill=(0, 0, 0, 180), outline=(255, 255, 255), width=2)

        if self.font_small:
            text_x = 35
            draw.text((text_x, 35), "全身テトリス", font=self.font_mid, fill=(0, 255, 255))
            mode_text = "MODE: SEATED" if self.is_seated_mode else "MODE: FULL"
            draw.text((text_x, 65), mode_text, font=self.font_vsmall, fill=(255, 255, 0))
            draw.text((text_x, 85), f"SCORE: {score}", font=self.font_small, fill=(255, 255, 255))
            speed_text = "SPEED: HIGH" if self.is_fast_drop else "SPEED: NORMAL"
            draw.text((text_x, 105), speed_text, font=self.font_small, fill=(255, 100, 100) if self.is_fast_drop else (100, 255, 100))
            draw.line([(text_x, 130), (245, 130)], fill=(100, 100, 100), width=1)
            draw.text((text_x, 140), "NEXT", font=self.font_mid, fill=(255, 200, 0))
            
            nx, ny, n_block_size = 75, 175, 22
            for ry, row in enumerate(self.game.next_shape):
                for rx, cell in enumerate(row):
                    if cell:
                        # PIECE_DATAの色はBGRなのでRGBへ変換してPILで使用
                        draw.rectangle([nx+rx*n_block_size, ny+ry*n_block_size, nx+rx*n_block_size+20, ny+ry*n_block_size+20], fill=self.game.next_color[::-1], outline=(255,255,255), width=1)
            
            draw.line([(text_x, 250), (245, 250)], fill=(100, 100, 100), width=1)
            draw.text((text_x, 260), "【操作ガイド】", font=self.font_small, fill=(200, 255, 200))
            draw.text((text_x, 285), "・傾ける: 左右移動", font=self.font_vsmall, fill=(255, 255, 255))
            draw.text((text_x, 305), "・お辞儀: 加速", font=self.font_vsmall, fill=(255, 255, 150))
            draw.text((text_x, 325), "・片手を上げる: 回転", font=self.font_vsmall, fill=(255, 255, 255))
            draw.text((text_x, 365), "Q: QUIT / R: RESET", font=self.font_vsmall, fill=(150, 150, 255))
            draw.text((text_x, 385), "M: MENU", font=self.font_vsmall, fill=(150, 150, 255))
        
        # ゲームオーバー表示
        if game_over:
            draw.rectangle([0, h//2-80, w, h//2+80], fill=(0,0,0,230))
            if self.font_large:
                draw.text((w//2-100, h//2-40), "GAME OVER", font=self.font_large, fill=(255, 50, 50))
                
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    def run(self):
        win_name = "Pose Tetris HD MAX"
        cv2.namedWindow(win_name)
        cv2.setMouseCallback(win_name, self.mouse_callback)
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("Error: カメラが見つかりません。")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            results = self.pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            if self.state == "START_MENU":
                display_frame = self.draw_start_menu(frame, results)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'): break
            else:
                command = self.get_pose_command(results)
                self.is_fast_drop = command["drop"]
                now = time.time()
                
                if not self.game.game_over:
                    if command["move"] != 0 and command["move"] != self.prev_move_dir: 
                        self.game.move(command["move"])
                    self.prev_move_dir = command["move"]
                    
                    if command["rotate"] and not self.prev_rotate_state: 
                        self.game.rotate()
                    self.prev_rotate_state = command["rotate"]
                    
                    drop_int = FAST_DROP_INTERVAL if self.is_fast_drop else NORMAL_DROP_INTERVAL
                    if now - self.last_drop_time > drop_int:
                        self.game.drop()
                        self.last_drop_time = now

                # 描画処理
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (w, h), (15, 15, 15), -1)
                frame = cv2.addWeighted(overlay, 0.4, frame, 0.6, 0)
                
                m_y = int(h * 0.05)
                b_s = (h - m_y * 2) // GRID_HEIGHT
                bw, bh = b_s * GRID_WIDTH, b_s * GRID_HEIGHT
                bx, by = w - bw - 50, m_y
                
                cv2.rectangle(frame, (bx-4, by-4), (bx+bw+4, by+bh+4), (255, 255, 255), 2)
                cv2.rectangle(frame, (bx, by), (bx+bw, by+bh), (0, 0, 0), -1)
                
                # グリッド線
                for x in range(1, GRID_WIDTH):
                    for y_dots in range(0, bh, 8): 
                        cv2.line(frame, (bx+x*b_s, by+y_dots), (bx+x*b_s, by+y_dots+4), (40, 40, 40), 1)
                for y in range(1, GRID_HEIGHT):
                    for x_dots in range(0, bw, 8): 
                        cv2.line(frame, (bx+x_dots, by+y*b_s), (bx+x_dots+4, by+y*b_s), (40, 40, 40), 1)

                def draw_rect(x, y, color, alpha=255):
                    px, py = bx+int(x*b_s), by+int(y*b_s)
                    if alpha < 255:
                        roi = frame[py+1:py+b_s-1, px+1:px+b_s-1]
                        if roi.size > 0:
                            frame[py+1:py+b_s-1, px+1:px+b_s-1] = cv2.addWeighted(roi, 0.7, np.full_like(roi, np.array(color, dtype=np.uint8)), 0.3, 0)
                    else:
                        cv2.rectangle(frame, (px+1, py+1), (px+b_s-1, py+b_s-1), color, -1)
                    cv2.rectangle(frame, (px+1, py+1), (px+b_s-1, py+b_s-1), (255, 255, 255) if alpha == 255 else color, 1)

                # ゴースト（落下地点）の描画
                if not self.game.game_over:
                    gy = self.game.piece_y
                    while not self.game.check_collision(self.game.piece_x, gy + 1, self.game.current_shape): 
                        gy += 1
                    for ry, row in enumerate(self.game.current_shape):
                        for rx, cell in enumerate(row):
                            if cell: draw_rect(self.game.piece_x+rx, gy+ry, self.game.current_color, 100)
                
                # 固定済みブロックの描画
                for gy, row in enumerate(self.game.grid):
                    for gx, col in enumerate(row):
                        if col: draw_rect(gx, gy, col)
                
                # 操作中ブロックの描画
                if not self.game.game_over:
                    for ry, row in enumerate(self.game.current_shape):
                        for rx, cell in enumerate(row):
                            if cell: draw_rect(self.game.piece_x+rx, self.game.piece_y+ry, self.game.current_color)
                
                if results.pose_landmarks: 
                    mp.solutions.drawing_utils.draw_landmarks(frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
                
                display_frame = self.draw_ui(frame, self.game.score, self.game.game_over)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'): break
                elif key == ord('r'): self.game = TetrisLogic()
                elif key == ord('m'): self.state = "START_MENU"
                
            cv2.imshow(win_name, display_frame)
            
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    app = PoseTetris()
    app.run()