# AI進化論：Flappy Bird (完全版) ✨
# インストール: pip install tkinter pillow numpy pygame
# 実行方法: python flappy_ai.py
# Select Interpreter: Python 3.11.9

import pygame
import random
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import time
import os
import sys
import math

# --- ゲーム設定 ---
GAME_WIDTH = 400
GAME_HEIGHT = 600
BIRD_X = 60
GRAVITY = 0.5
JUMP_STRENGTH = -8
PIPE_SPEED = 3.5
PIPE_GAP = 160          
PIPE_SPAWN_INTERVAL = 70 # 出現間隔を短縮 (約1.2秒)

# 遺伝的アルゴリズムの設定
POPULATION_SIZE = 20    # 個体数を増やして「当たり」を引きやすくする
DEFAULT_MUTATION = 0.1

# --- AI・ゲームロジック ---

class NeuralNetwork:
    """鳥の脳みそ（シンプルなパーセプトロン）"""
    def __init__(self, weights=None):
        if weights is not None:
            self.weights = weights.copy()
        else:
            # 入力: [鳥のY, 土管との距離, 上の土管の端, 下の土管の端, 鳥の速度]
            self.weights = np.random.rand(5) * 2 - 1

    def decide(self, inputs):
        sum_val = np.dot(inputs, self.weights)
        return 1 if sum_val > 0 else 0

    def mutate(self, rate):
        """重みをランダムに変化させる"""
        mutation = (np.random.rand(5) * 2 - 1) * rate
        self.weights += mutation

class Bird:
    def __init__(self, brain=None):
        self.y = GAME_HEIGHT // 2
        self.velocity = 0
        self.width = 34
        self.height = 24
        self.alive = True
        self.score = 0
        self.fitness = 0 # 生き残った時間
        
        if brain:
            self.brain = NeuralNetwork(weights=brain.weights)
        else:
            self.brain = NeuralNetwork()

        # 個体ごとに少し違う黄色を割り当てる
        self.color = (255, random.randint(180, 255), 0)

    def update(self):
        if not self.alive: return
        self.velocity += GRAVITY
        self.y += self.velocity
        self.score += 1
        self.fitness += 1

        # 地面または天井にぶつかったら死亡
        if self.y < 0 or self.y + self.height > GAME_HEIGHT - 50:
            self.alive = False

    def jump(self):
        self.velocity = JUMP_STRENGTH

    def think(self, pipes):
        if not self.alive: return
        closest_pipe = None
        closest_dist = float('inf')
        
        for pipe in pipes:
            dist = (pipe.x + pipe.width) - BIRD_X
            if 0 < dist < closest_dist:
                closest_pipe = pipe
                closest_dist = dist
        
        if closest_pipe:
            # 入力データの正規化
            inputs = [
                self.y / GAME_HEIGHT,
                closest_dist / GAME_WIDTH,
                closest_pipe.gap_y / GAME_HEIGHT,
                (closest_pipe.gap_y + PIPE_GAP) / GAME_HEIGHT,
                self.velocity / 15.0
            ]
            if self.brain.decide(inputs) == 1:
                self.jump()

    def draw(self, surf):
        if not self.alive: return
        # 体
        pygame.draw.ellipse(surf, self.color, (BIRD_X, self.y, self.width, self.height))
        pygame.draw.ellipse(surf, (0, 0, 0), (BIRD_X, self.y, self.width, self.height), 2)
        # 目
        pygame.draw.circle(surf, (255, 255, 255), (BIRD_X + 25, self.y + 8), 6)
        pygame.draw.circle(surf, (0, 0, 0), (BIRD_X + 27, self.y + 8), 2)
        # クチバシ
        pygame.draw.polygon(surf, (255, 100, 0), [(BIRD_X + 30, self.y + 12), (BIRD_X + 40, self.y + 15), (BIRD_X + 30, self.y + 18)])

class Pipe:
    def __init__(self):
        self.x = GAME_WIDTH
        self.width = 70
        self.gap_y = random.randint(100, GAME_HEIGHT - 150 - PIPE_GAP)
        self.color = (115, 190, 45)
        self.passed = False

    def update(self):
        self.x -= PIPE_SPEED

    def draw(self, surf):
        # 上の土管
        pygame.draw.rect(surf, self.color, (self.x, 0, self.width, self.gap_y))
        pygame.draw.rect(surf, (0, 0, 0), (self.x, 0, self.width, self.gap_y), 2)
        pygame.draw.rect(surf, self.color, (self.x - 5, self.gap_y - 20, self.width + 10, 20))
        pygame.draw.rect(surf, (0, 0, 0), (self.x - 5, self.gap_y - 20, self.width + 10, 20), 2)
        
        # 下の土管
        pygame.draw.rect(surf, self.color, (self.x, self.gap_y + PIPE_GAP, self.width, GAME_HEIGHT))
        pygame.draw.rect(surf, (0, 0, 0), (self.x, self.gap_y + PIPE_GAP, self.width, GAME_HEIGHT), 2)
        pygame.draw.rect(surf, self.color, (self.x - 5, self.gap_y + PIPE_GAP, self.width + 10, 20))
        pygame.draw.rect(surf, (0, 0, 0), (self.x - 5, self.gap_y + PIPE_GAP, self.width + 10, 20), 2)

# --- メインアプリケーションクラス ---

class FlappyAIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI進化論：Flappy Bird (完全版) ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        self.PRIMARY_COLOR = "#FF9F43"
        self.SECONDARY_COLOR = "#FFCC33"
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"

        pygame.init()
        self.game_surf = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
        
        # 状態管理
        self.generation = 1
        self.birds = [Bird() for _ in range(POPULATION_SIZE)]
        self.pipes = []
        self.pipe_step_counter = 40 # 最初の土管を早めに出すために下駄を履かせる
        self.best_score_all_time = 0
        self.current_max_score = 0
        self.best_brain = None
        self.sim_speed = 1.0
        self.mutation_rate = DEFAULT_MUTATION
        self.is_running = True
        self.ground_offset = 0

        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        header = tk.Frame(self.root, bg="#FFFBEB")
        header.pack(pady=20)
        tk.Label(header, text="🕊️ AI進化シミュレーター：Flappy Bird", 
                 font=("Meiryo", 28, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR).pack()

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=40, pady=5)
        
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=2)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=400)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        data_frame = tk.LabelFrame(self.left_panel, text=" 📊 進化統計データ ", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        data_frame.pack(fill=tk.X, pady=5)

        self.lbl_gen = tk.Label(data_frame, text="第 1 世代", bg=self.BG_WHITE, 
                               font=("Meiryo", 18, "bold"), fg=self.TEXT_COLOR, pady=10)
        self.lbl_gen.pack()

        # リアルタイムのスコア表示
        self.lbl_now = tk.Label(data_frame, text="現在のスコア: 0", bg=self.BG_WHITE, 
                                font=("Meiryo", 14, "bold"), fg=self.TEXT_COLOR)
        self.lbl_now.pack(pady=5)

        self.lbl_best = tk.Label(data_frame, text="歴代最高: 0", bg=self.BG_WHITE, 
                                font=("Impact", 24), fg=self.PRIMARY_COLOR, pady=10)
        self.lbl_best.pack()

        self.lbl_alive = tk.Label(data_frame, text=f"生存数: {POPULATION_SIZE} / {POPULATION_SIZE}", bg=self.BG_WHITE, 
                                 font=("Meiryo", 10), fg=self.TEXT_COLOR)
        self.lbl_alive.pack(pady=5)

        settings_frame = tk.LabelFrame(self.left_panel, text=" ⚙️ 学習パラメータ設定 ", 
                                      font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                      fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        settings_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(settings_frame, text="演算スピード (1x 〜 5x):", bg=self.BG_WHITE, font=("Meiryo", 9)).pack(pady=(10, 0))
        self.speed_slider = tk.Scale(settings_frame, from_=1, to=5, resolution=0.1, orient=tk.HORIZONTAL,
                                    bg=self.BG_WHITE, highlightthickness=0, command=self.update_sim_speed)
        self.speed_slider.set(1.0)
        self.speed_slider.pack(fill=tk.X, padx=20, pady=5)

        tk.Label(settings_frame, text="突然変異率 (学習の勢い):", bg=self.BG_WHITE, font=("Meiryo", 9)).pack()
        self.mutation_slider = tk.Scale(settings_frame, from_=0.01, to=0.8, resolution=0.01, orient=tk.HORIZONTAL,
                                       bg=self.BG_WHITE, highlightthickness=0, command=self.update_mutation_rate)
        self.mutation_slider.set(0.1)
        self.mutation_slider.pack(fill=tk.X, padx=20, pady=5)

        guide_frame = tk.LabelFrame(self.left_panel, text=" 💡 進化のヒント ", 
                                   font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        guide_frame.pack(fill=tk.X, pady=5)
        
        guide_text = "・リアルタイムのスコアはこのパネルで確認\n　できます。右側のモニターはAIの動きに\n　集中できるよう、表示をスッキリさせました。"
        tk.Label(guide_frame, text=guide_text, bg=self.BG_WHITE, justify=tk.LEFT, 
                 font=("Meiryo", 9), fg=self.TEXT_COLOR, padx=10, pady=10).pack(fill=tk.X)

        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 学習ログ ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- 右側：ゲーム画面 ---
        self.right_panel = tk.Frame(self.main_container, bg="#87CEEB", relief=tk.RIDGE, bd=4)
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        self.canvas = tk.Canvas(self.right_panel, bg="#87CEEB", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.image_item = self.canvas.create_image(0, 0, anchor=tk.NW)

    def write_log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def update_sim_speed(self, val):
        self.sim_speed = float(val)

    def update_mutation_rate(self, val):
        self.mutation_rate = float(val)

    def next_generation(self):
        # 最も優秀な個体を探す
        best_bird = max(self.birds, key=lambda b: b.fitness)
        
        if best_bird.score > self.best_score_all_time:
            self.best_score_all_time = best_bird.score
            self.best_brain = best_bird.brain
            self.write_log(f"第 {self.generation} 世代終了。最高記録更新: {best_bird.score}")
        
        # エリートをベースに次世代を生成
        parent_brain = self.best_brain if self.best_brain else best_bird.brain
        
        new_birds = []
        new_birds.append(Bird(brain=parent_brain))
        for _ in range(POPULATION_SIZE - 1):
            child = Bird(brain=parent_brain)
            child.brain.mutate(self.mutation_rate)
            new_birds.append(child)
            
        self.birds = new_birds
        self.pipes = []
        self.pipe_step_counter = 40 
        self.current_max_score = 0
        self.generation += 1
        self.lbl_gen.config(text=f"第 {self.generation} 世代")

    def draw_background(self):
        self.game_surf.fill((113, 197, 207))
        pygame.draw.circle(self.game_surf, (255,255,255,100), (100, 100), 30)
        pygame.draw.circle(self.game_surf, (255,255,255,100), (280, 150), 35)
        
        self.ground_offset = (self.ground_offset + PIPE_SPEED) % 40
        pygame.draw.rect(self.game_surf, (222, 216, 149), (0, GAME_HEIGHT - 50, GAME_WIDTH, 50))
        pygame.draw.line(self.game_surf, (85, 128, 34), (0, GAME_HEIGHT - 50), (GAME_WIDTH, GAME_HEIGHT - 50), 3)
        for x in range(int(-self.ground_offset), GAME_WIDTH + 40, 40):
            pygame.draw.line(self.game_surf, (155, 150, 100), (x, GAME_HEIGHT - 50), (x - 20, GAME_HEIGHT), 2)

    def update_loop(self):
        if not self.is_running: return

        loop_count = int(self.sim_speed) if self.sim_speed >= 1 else 1
        for _ in range(loop_count):
            self.pipe_step_counter += 1
            if self.pipe_step_counter >= PIPE_SPAWN_INTERVAL:
                self.pipes.append(Pipe())
                self.pipe_step_counter = 0

            for pipe in self.pipes:
                pipe.update()
            self.pipes = [p for p in self.pipes if p.x + p.width > -10]

            alive_count = 0
            temp_max_score = 0
            for bird in self.birds:
                if bird.alive:
                    alive_count += 1
                    bird.think(self.pipes)
                    bird.update()
                    
                    if bird.score > temp_max_score:
                        temp_max_score = bird.score
                    
                    # 当たり判定
                    for pipe in self.pipes:
                        if pipe.x < BIRD_X + bird.width and BIRD_X < pipe.x + pipe.width:
                            if bird.y < pipe.gap_y or bird.y + bird.height > pipe.gap_y + PIPE_GAP:
                                bird.alive = False

            # 左パネルのリアルタイムスコアを更新
            self.current_max_score = temp_max_score
            self.lbl_alive.config(text=f"生存数: {alive_count} / {POPULATION_SIZE}")
            self.lbl_now.config(text=f"現在のスコア: {self.current_max_score}")

            if alive_count == 0:
                self.next_generation()
                break

        self.lbl_best.config(text=f"歴代最高: {self.best_score_all_time}")

        # --- 描画 ---
        self.draw_background()
        for pipe in self.pipes:
            pipe.draw(self.game_surf)
        for bird in self.birds:
            bird.draw(self.game_surf)

        # Pygame -> Tkinter
        img_data = pygame.image.tostring(self.game_surf, "RGB")
        pil_img = Image.frombytes("RGB", (GAME_WIDTH, GAME_HEIGHT), img_data)
        
        self.root.update_idletasks()
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw > 50 and ch > 50:
            ratio = min(cw / GAME_WIDTH, ch / GAME_HEIGHT)
            new_size = (int(GAME_WIDTH * ratio), int(GAME_HEIGHT * ratio))
            pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
            self.tk_img = ImageTk.PhotoImage(pil_img)
            self.canvas.itemconfig(self.image_item, image=self.tk_img)
            self.canvas.coords(self.image_item, (cw - new_size[0]) // 2, (ch - new_size[1]) // 2)

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
    app = FlappyAIApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()