# スーパーマリオAI学習プログラム - ジャンプ挙動修正版
# インストール: pip install pygame numpy
# 実行方法: python 20_1_mario_ai.py
# Select Interpreter: Python 3.11.9

import pygame
import random
import pickle
import os

# --- 設定 ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 450
DEFAULT_FPS = 60
MAX_FPS = 10000 # 描画OFF時はCPUの限界まで加速

# カラーパレット
SKY_BLUE = (146, 144, 255)
MARIO_RED = (255, 0, 0)
MARIO_BLUE = (0, 0, 255)
MARIO_SKIN = (255, 204, 153)
GROUND_BROWN = (200, 76, 12)
PIPE_GREEN = (0, 168, 0)
PIPE_DARK_GREEN = (0, 100, 0)
GOOMBA_BROWN = (165, 42, 42)
CLOUD_WHITE = (255, 255, 255)
BUSH_GREEN = (50, 200, 50)
TEXT_COLOR = (255, 255, 255)

# ゲーム定数 (ジャンプ挙動の調整)
PLAYER_X = 100
PLAYER_Y_GROUND = 340
PLAYER_SIZE = 40
JUMP_FORCE = 20  # 重力に合わせて少し強化
GRAVITY = 1.5     # 重力を強くして滞空時間を短縮

# 強化学習パラメータ (Q-Learning)
LEARNING_RATE = 0.1
DISCOUNT_FACTOR = 0.98
EPSILON_START = 0.15
EPSILON_MIN = 0.005
EPSILON_DECAY = 0.9995 
DATA_FILE = "mario_brain_v4.pkl"

class MarioGameAI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("スーパーマリオAI学習 - ジャンプ挙動修正版")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(['msgothic', 'hiraginokakugothicpron', 'arial'], 20, bold=True)
        self.fps = DEFAULT_FPS
        self.rendering_enabled = True # 描画フラグ

        # 学習データのロード
        self.q_table = self.load_brain()
        self.epsilon = EPSILON_START
        self.episode = 0
        self.high_score = 0
        
        self.reset_game()

    def load_brain(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'rb') as f:
                    return pickle.load(f)
            except: return {}
        return {}

    def save_brain(self):
        try:
            with open(DATA_FILE, 'wb') as f:
                pickle.dump(self.q_table, f)
        except: pass

    def reset_game(self):
        self.player_y = PLAYER_Y_GROUND
        self.player_vel_y = 0
        self.is_jumping = False
        self.score = 0
        self.game_over = False
        self.obstacles = []
        self.spawn_timer = 0
        self.clouds = [{'x': random.randint(0, 800), 'y': random.randint(30, 120), 's': 0.5} for _ in range(5)]
        self.bushes = [{'x': random.randint(0, 800), 'y': PLAYER_Y_GROUND + 15, 's': 2} for _ in range(3)]

    def get_state(self):
        closest_dist = 20
        obs_type = 0       
        for obs in self.obstacles:
            dist = obs['x'] - (PLAYER_X + PLAYER_SIZE)
            if 0 <= dist < 800:
                if dist < 120: closest_dist = int(dist / 15)
                else: closest_dist = 8 + int((dist - 120) / 60)
                closest_dist = min(closest_dist, 20)
                obs_type = 1 if obs['type'] == 'goomba' else 2
                break
        vel_state = 0
        if self.player_vel_y < -1: vel_state = 1
        elif self.player_vel_y > 1: vel_state = 2
        player_in_air = 1 if self.is_jumping else 0
        return (closest_dist, obs_type, player_in_air, vel_state)

    def get_action(self, state):
        if state not in self.q_table:
            self.q_table[state] = [0.0, 0.0]
        if random.random() < self.epsilon:
            return random.randint(0, 1)
        else:
            return 0 if self.q_table[state][0] >= self.q_table[state][1] else 1

    def update_q_table(self, state, action, reward, next_state):
        if state not in self.q_table: self.q_table[state] = [0.0, 0.0]
        if next_state not in self.q_table: self.q_table[next_state] = [0.0, 0.0]
        old_value = self.q_table[state][action]
        next_max = max(self.q_table[next_state])
        new_value = (1 - LEARNING_RATE) * old_value + LEARNING_RATE * (reward + DISCOUNT_FACTOR * next_max)
        self.q_table[state][action] = new_value

    def step(self, action):
        reward = 0
        nearest_obs_dist = 999
        for obs in self.obstacles:
            dist = obs['x'] - (PLAYER_X + PLAYER_SIZE)
            if dist > 0: nearest_obs_dist = min(nearest_obs_dist, dist)

        if action == 1 and not self.is_jumping:
            self.player_vel_y = -JUMP_FORCE
            self.is_jumping = True
            reward = -15 if nearest_obs_dist > 250 else -2

        self.player_y += self.player_vel_y
        self.player_vel_y += GRAVITY
        if self.player_y >= PLAYER_Y_GROUND:
            self.player_y = PLAYER_Y_GROUND
            self.is_jumping = False
            self.player_vel_y = 0

        self.spawn_timer += 1
        if self.spawn_timer > 45:
            if random.random() < 0.05:
                otype = random.choice(['goomba', 'pipe'])
                spd = 7.0 
                if otype == 'goomba':
                    self.obstacles.append({'x': SCREEN_WIDTH, 'y': PLAYER_Y_GROUND + 10, 'w': 30, 'h': 30, 'type': 'goomba', 'speed': spd})
                else:
                    self.obstacles.append({'x': SCREEN_WIDTH, 'y': PLAYER_Y_GROUND - 20, 'w': 45, 'h': 60, 'type': 'pipe', 'speed': spd})
                self.spawn_timer = 0
        
        for cloud in self.clouds: cloud['x'] -= cloud['s']
        for bush in self.bushes: bush['x'] -= bush['s']
        for obs in self.obstacles: obs['x'] -= obs['speed']
        for item in self.clouds + self.bushes:
            if item['x'] < -100: item['x'] = SCREEN_WIDTH

        player_rect = pygame.Rect(PLAYER_X + 10, self.player_y + 5, PLAYER_SIZE - 20, PLAYER_SIZE - 5)
        alive = True
        for obs in self.obstacles:
            obs_rect = pygame.Rect(obs['x'], obs['y'], obs['w'], obs['h'])
            if player_rect.colliderect(obs_rect):
                reward = -500 
                self.game_over = True
                alive = False
            if obs['x'] + obs['w'] < PLAYER_X and not obs.get('passed', False):
                reward = 150 
                obs['passed'] = True
                self.score += 1
        if alive: reward += 1 + (self.score * 0.01)
        self.obstacles = [o for o in self.obstacles if o['x'] + o['w'] > 0]
        return reward

    def draw(self):
        self.screen.fill(SKY_BLUE)
        for c in self.clouds:
            pygame.draw.ellipse(self.screen, CLOUD_WHITE, (c['x'], c['y'], 60, 30))
        for b in self.bushes:
            pygame.draw.circle(self.screen, BUSH_GREEN, (int(b['x']), int(b['y'])), 20)
        pygame.draw.rect(self.screen, GROUND_BROWN, (0, PLAYER_Y_GROUND + PLAYER_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT))

        # マリオ
        pygame.draw.rect(self.screen, MARIO_BLUE, (PLAYER_X + 5, self.player_y + 15, PLAYER_SIZE - 10, 20)) 
        pygame.draw.rect(self.screen, MARIO_SKIN, (PLAYER_X + 10, self.player_y + 5, 20, 15)) 
        pygame.draw.rect(self.screen, MARIO_RED, (PLAYER_X + 5, self.player_y, 25, 8)) 
        
        for obs in self.obstacles:
            if obs['type'] == 'goomba':
                pygame.draw.rect(self.screen, GOOMBA_BROWN, (obs['x'], obs['y'], obs['w'], obs['h']), border_radius=8)
            else:
                pygame.draw.rect(self.screen, PIPE_GREEN, (obs['x'], obs['y'], obs['w'], obs['h']))
                pygame.draw.rect(self.screen, PIPE_DARK_GREEN, (obs['x']-4, obs['y'], obs['w']+8, 15))

        # UI表示
        stats = [
            f"学習世代: {self.episode}",
            f"スコア: {self.score} (最高: {self.high_score})",
            f"AI探索率: {self.epsilon:.4f}",
            f"速度: {self.fps if self.fps < MAX_FPS else 'UNLIMITED'} FPS [↑/↓]",
            f"描画モード: {'ON' if self.rendering_enabled else 'OFF (高速)'} [Vキー]"
        ]
        for i, text in enumerate(stats):
            img = self.font.render(text, True, TEXT_COLOR)
            self.screen.blit(img, (20, 20 + i*30))
        pygame.display.flip()

    def draw_fast_msg(self):
        self.screen.fill((20, 20, 20))
        msg = self.font.render(f"高速学習中... (世代: {self.episode})  [Vキーで描画ON]", True, (0, 255, 0))
        self.screen.blit(msg, (SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2))
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.save_brain()
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        self.fps = min(self.fps + 200, MAX_FPS)
                    if event.key == pygame.K_DOWN:
                        self.fps = max(self.fps - 200, 30)
                    if event.key == pygame.K_v: 
                        self.rendering_enabled = not self.rendering_enabled
                        if not self.rendering_enabled:
                            self.draw_fast_msg()

            state = self.get_state()
            action = self.get_action(state)
            reward = self.step(action)
            next_state = self.get_state()
            
            self.update_q_table(state, action, reward, next_state)

            if self.game_over:
                self.episode += 1
                if self.score > self.high_score: self.high_score = self.score
                if self.epsilon > EPSILON_MIN: self.epsilon *= EPSILON_DECAY
                if self.episode % 100 == 0: self.save_brain()
                self.reset_game()

            if self.rendering_enabled:
                self.draw()
            
            if self.fps < MAX_FPS:
                self.clock.tick(self.fps)

        pygame.quit()

if __name__ == "__main__":
    ai = MarioGameAI()
    ai.run()