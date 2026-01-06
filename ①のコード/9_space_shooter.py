# AIスペースシューター・プロ ✨
# インストール: pip install tkinter pygame pillow
# 実行方法: python space_shooter.py
# Select Interpreter: Python 3.11.9

import pygame
import random
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import time
import os
import sys

# --- ゲーム設定 ---
GAME_WIDTH = 800
GAME_HEIGHT = 650
PLAYER_SIZE = 50
ENEMY_SIZE = 60    # 【変更】40から60へサイズアップ
BULLET_SIZE = 5

# 基本速度（これに倍率が乗ります）
BASE_PLAYER_SPEED = 7
BASE_ENEMY_SPEED_MIN = 3
BASE_ENEMY_SPEED_MAX = 6
BASE_BULLET_SPEED = 12

# --- クラス定義 ---

class Player(pygame.sprite.Sprite):
    """プレイヤーの宇宙船"""
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface([PLAYER_SIZE, PLAYER_SIZE], pygame.SRCALPHA)
        # 機体デザイン
        pygame.draw.polygon(self.image, (231, 76, 60), [(25, 0), (0, 50), (50, 50)]) 
        pygame.draw.rect(self.image, (236, 240, 241), [20, 25, 10, 15]) 
        
        self.rect = self.image.get_rect()
        self.rect.centerx = GAME_WIDTH // 2
        self.rect.bottom = GAME_HEIGHT - 20

    def update(self, key_states, speed_scale):
        """倍率を考慮して移動"""
        move_val = BASE_PLAYER_SPEED * speed_scale
        if key_states.get("Left"):
            self.rect.x -= move_val
        if key_states.get("Right"):
            self.rect.x += move_val
        
        if self.rect.left < 0: self.rect.left = 0
        if self.rect.right > GAME_WIDTH: self.rect.right = GAME_WIDTH

    def shoot(self):
        return Bullet(self.rect.centerx, self.rect.top)

class Enemy(pygame.sprite.Sprite):
    """敵キャラ"""
    def __init__(self, speed_scale=1.0):
        super().__init__()
        # サイズアップに合わせた描画
        self.image = pygame.Surface([ENEMY_SIZE, ENEMY_SIZE], pygame.SRCALPHA)
        # UFO型のデザインをサイズに合わせてスケーリング
        pygame.draw.ellipse(self.image, (241, 196, 15), [0, 15, ENEMY_SIZE, 30])
        pygame.draw.circle(self.image, (52, 152, 219), (ENEMY_SIZE//2, 22), 12)
        
        self.rect = self.image.get_rect()
        self.rect.x = random.randrange(0, GAME_WIDTH - ENEMY_SIZE)
        self.rect.y = random.randrange(-150, -60)
        
        # 基本の降下速度をランダムに決定
        self.base_speedy = random.uniform(BASE_ENEMY_SPEED_MIN, BASE_ENEMY_SPEED_MAX)

    def update(self, speed_scale):
        self.rect.y += self.base_speedy * speed_scale
        # 画面下まで行ったらリセット
        if self.rect.top > GAME_HEIGHT + 10:
            self.rect.x = random.randrange(0, GAME_WIDTH - ENEMY_SIZE)
            self.rect.y = random.randrange(-150, -60)
            self.base_speedy = random.uniform(BASE_ENEMY_SPEED_MIN, BASE_ENEMY_SPEED_MAX)

class Bullet(pygame.sprite.Sprite):
    """弾"""
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface([BULLET_SIZE, BULLET_SIZE * 3])
        self.image.fill((255, 255, 255))
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.bottom = y

    def update(self, speed_scale):
        self.rect.y -= BASE_BULLET_SPEED * speed_scale
        if self.rect.bottom < 0:
            self.kill()

# --- メインアプリケーション ---

class SpaceShooterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIスペースシューター・プロ ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"
        self.SECONDARY_COLOR = "#FFCC33"
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.ALERT_COLOR = "#E74C3C"

        # Pygame初期化
        pygame.init()
        self.game_surf = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
        
        # 状態管理
        self.is_running = True
        self.game_over = False
        self.score = 0
        self.high_score = 0
        self.speed_scale = 1.0 # 速度倍率
        self.stars = [[random.randint(0, GAME_WIDTH), random.randint(0, GAME_HEIGHT), random.randint(1, 3)] for _ in range(50)]
        self.key_states = {"Left": False, "Right": False}
        
        self.setup_ui()
        self.reset_game()
        self.bind_keys()
        
        self.update_loop()

    def setup_ui(self):
        # タイトル
        header = tk.Frame(self.root, bg="#FFFBEB")
        header.pack(pady=20)
        tk.Label(header, text="🚀 AIスペースシューター Pro", 
                 font=("Meiryo", 28, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR).pack()

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=40, pady=10)
        
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作・設定パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 1. スコア
        score_frame = tk.LabelFrame(self.left_panel, text=" 📊 統計 ", 
                                   font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        score_frame.pack(fill=tk.X, pady=(0, 10))

        self.lbl_score = tk.Label(score_frame, text="0", bg=self.BG_WHITE, 
                                 font=("Impact", 48), fg=self.TEXT_COLOR)
        self.lbl_score.pack()
        self.lbl_high = tk.Label(score_frame, text="HIGH SCORE: 0", bg=self.BG_WHITE, 
                                font=("Meiryo", 10, "bold"), fg=self.SECONDARY_COLOR, pady=5)
        self.lbl_high.pack()

        # 2. ゲーム設定 (速度調整)
        settings_frame = tk.LabelFrame(self.left_panel, text=" ⚙️ ゲーム設定 ", 
                                      font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                      fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        settings_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(settings_frame, text="ゲーム速度 (倍率):", bg=self.BG_WHITE, font=("Meiryo", 9)).pack(pady=(10, 0))
        self.speed_slider = tk.Scale(settings_frame, from_=0.5, to=2.5, resolution=0.1, orient=tk.HORIZONTAL,
                                    bg=self.BG_WHITE, highlightthickness=0, command=self.update_speed_scale)
        self.speed_slider.set(1.0)
        self.speed_slider.pack(fill=tk.X, padx=20, pady=(0, 15))

        # 3. ログ
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 ログ ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 操作説明
        guide_text = "【キーボード操作】\n・← → キー : 移動\n・SPACE キー : 攻撃\n・R キー : リスタート"
        tk.Label(self.left_panel, text=guide_text, bg="#FFFBEB", justify=tk.LEFT, 
                 font=("Meiryo", 9, "bold"), fg="#95A5A6").pack(side=tk.BOTTOM, pady=10)

        # --- 右側：ゲーム画面エリア ---
        self.right_panel = tk.Frame(self.main_container, bg="#222", relief=tk.RIDGE, bd=4)
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        self.canvas = tk.Canvas(self.right_panel, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def update_speed_scale(self, val):
        self.speed_scale = float(val)

    def bind_keys(self):
        self.root.bind("<KeyPress-Left>", lambda e: self.set_key("Left", True))
        self.root.bind("<KeyRelease-Left>", lambda e: self.set_key("Left", False))
        self.root.bind("<KeyPress-Right>", lambda e: self.set_key("Right", True))
        self.root.bind("<KeyRelease-Right>", lambda e: self.set_key("Right", False))
        self.root.bind("<KeyPress-space>", lambda e: self.handle_shoot())
        self.root.bind("<KeyPress-r>", lambda e: self.handle_restart())

    def set_key(self, key, state):
        self.key_states[key] = state

    def handle_shoot(self):
        if not self.game_over:
            b = self.player.shoot()
            self.all_sprites.add(b)
            self.bullets.add(b)

    def handle_restart(self):
        if self.game_over:
            self.reset_game()

    def write_log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def reset_game(self):
        self.all_sprites = pygame.sprite.Group()
        self.mobs = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.player = Player()
        self.all_sprites.add(self.player)
        for i in range(8):
            m = Enemy()
            self.all_sprites.add(m)
            self.mobs.add(m)
        self.score = 0
        self.game_over = False
        self.write_log("ミッション開始：巨大敵機を撃破せよ！")

    def draw_starfield(self):
        self.game_surf.fill((10, 10, 30))
        for star in self.stars:
            # 星の流れる速度にも倍率を適用
            pygame.draw.circle(self.game_surf, (255, 255, 255), (star[0], star[1]), 1)
            star[1] += star[2] * self.speed_scale
            if star[1] > GAME_HEIGHT:
                star[1] = 0
                star[0] = random.randint(0, GAME_WIDTH)

    def update_loop(self):
        if not self.is_running: return

        if not self.game_over:
            # 各要素にスピード倍率を渡して更新
            self.player.update(self.key_states, self.speed_scale)
            for sprite in self.mobs:
                sprite.update(self.speed_scale)
            for sprite in self.bullets:
                sprite.update(self.speed_scale)
            
            # 衝突判定
            hits = pygame.sprite.groupcollide(self.mobs, self.bullets, True, True)
            for hit in hits:
                self.score += 10
                self.write_log(f"敵機撃破! スコア:{self.score}")
                m = Enemy()
                self.all_sprites.add(m)
                self.mobs.add(m)
                
            if pygame.sprite.spritecollide(self.player, self.mobs, False):
                self.game_over = True
                self.write_log("GAME OVER...")
                if self.score > self.high_score:
                    self.high_score = self.score
                    self.write_log(f"🔥 ハイスコア更新: {self.high_score}")

        # 描画
        self.draw_starfield()
        self.all_sprites.draw(self.game_surf)
        
        if self.game_over:
            overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.game_surf.blit(overlay, (0, 0))
            font = pygame.font.SysFont('impact', 72)
            text = font.render("MISSION FAILED", True, (231, 76, 60))
            self.game_surf.blit(text, (GAME_WIDTH//2 - 200, GAME_HEIGHT//2 - 60))
            font_s = pygame.font.SysFont('arial', 24, bold=True)
            text_s = font_s.render("Press 'R' to Restart", True, (255, 255, 255))
            self.game_surf.blit(text_s, (GAME_WIDTH//2 - 110, GAME_HEIGHT//2 + 40))

        # UI更新
        self.lbl_score.config(text=str(self.score))
        self.lbl_high.config(text=f"HIGH SCORE: {self.high_score}")
        
        # 画面転送
        img_data = pygame.image.tostring(self.game_surf, "RGB")
        pil_img = Image.frombytes("RGB", (GAME_WIDTH, GAME_HEIGHT), img_data)
        
        self.root.update_idletasks()
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw > 50 and ch > 50:
            ratio = min(cw/GAME_WIDTH, ch/GAME_HEIGHT)
            new_size = (int(GAME_WIDTH*ratio), int(GAME_HEIGHT*ratio))
            pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
            self.tk_img = ImageTk.PhotoImage(pil_img)
            self.canvas.itemconfig(self.image_item, image=self.tk_img)
            self.canvas.coords(self.image_item, (cw-new_size[0])//2, (ch-new_size[1])//2)

        # 約60FPSを維持するためのインターバル
        self.root.after(16, self.update_loop)

    def on_closing(self):
        self.is_running = False
        pygame.quit()
        self.root.destroy()
        sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = SpaceShooterApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()