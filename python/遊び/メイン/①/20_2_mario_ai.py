# スーパーマリオAI - 高難易度ギミック・トレーニング
# インストール: pip install pygame numpy
# 実行方法: python 20_2_mario_ai.py
# Select Interpreter: Python 3.11.9

import pygame
import random
import pickle
import os

# --- 設定 ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 450
DEFAULT_FPS = 60
MAX_FPS = 10000 

# カラーパレット
SKY_BLUE = (146, 144, 255)
MARIO_RED = (255, 0, 0)
MARIO_BLUE = (0, 0, 255)
MARIO_SKIN = (255, 204, 153)
GROUND_BROWN = (200, 76, 12)
PIPE_GREEN = (0, 168, 0)
GOOMBA_BROWN = (165, 42, 42)
KOOPA_GREEN = (50, 255, 50)
BULLET_BLACK = (30, 30, 30)
CLOUD_WHITE = (255, 255, 255)
TEXT_COLOR = (255, 255, 255)

# ゲーム定数 (滞空時間を短くするために重力とジャンプ力を調整)
PLAYER_X = 100
PLAYER_Y_GROUND = 340
PLAYER_SIZE = 40
JUMP_FORCE = 18  # 16 -> 18 (重力に合わせて少し強化)
GRAVITY = 1.5    # 0.9 -> 1.5 (重力を大幅に強化して滞空時間を短縮)

# 強化学習パラメータ
LEARNING_RATE = 0.1
DISCOUNT_FACTOR = 0.98
EPSILON_START = 0.2
EPSILON_MIN = 0.005
EPSILON_DECAY = 0.9997 
DATA_FILE = "mario_brain_v6_dynamic.pkl"

class MarioGameAI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("スーパーマリオAI - 難易度可変トレーニング (高速ジャンプ)")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(['msgothic', 'hiraginokakugothicpron', 'arial'], 18, bold=True)
        self.fps = DEFAULT_FPS
        self.rendering_enabled = True

        self.q_table = self.load_brain()
        self.epsilon = EPSILON_START
        self.episode = 0
        self.high_score = 0
        
        # ワールドレベル
        self.world_level = 1.0
        
        self.reset_game()

    def load_brain(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'rb') as f:
                    data = pickle.load(f)
                    self.episode = data.get('episode', 0)
                    return data.get('q_table', data)
            except: return {}
        return {}

    def save_brain(self):
        try:
            with open(DATA_FILE, 'wb') as f:
                save_data = {'q_table': self.q_table, 'episode': self.episode}
                pickle.dump(save_data, f)
        except: pass

    def reset_game(self):
        self.player_y = PLAYER_Y_GROUND
        self.player_vel_y = 0
        self.is_jumping = False
        self.score = 0
        self.game_over = False
        self.obstacles = []
        self.spawn_timer = 0
        
        self.world_level = 1.0 + (self.episode / 50.0)
        self.current_difficulty = self.world_level
        
        self.clouds = [{'x': random.randint(0, 800), 'y': random.randint(30, 100), 's': 0.5} for _ in range(5)]

    def get_state(self):
        closest_dist = 15
        obs_type = 0  
        obs_height = 0 
        
        for obs in self.obstacles:
            dist = obs['x'] - (PLAYER_X + PLAYER_SIZE)
            if -40 <= dist < 600:
                if dist < 120: closest_dist = int(dist / 12)
                else: closest_dist = 10 + int((dist - 120) / 60)
                closest_dist = max(0, min(closest_dist, 15))
                
                if obs['type'] == 'goomba' or obs['type'] == 'pipe': obs_type = 1
                elif obs['type'] == 'koopa': obs_type = 2
                elif obs['type'] == 'pit': obs_type = 3
                elif obs['type'] == 'bullet': obs_type = 4
                
                if obs['y'] < PLAYER_Y_GROUND - 40: obs_height = 2
                elif obs['y'] < PLAYER_Y_GROUND: obs_height = 1
                else: obs_height = 0
                break
        
        vel_state = 0
        if self.player_vel_y < -2: vel_state = 1
        elif self.player_vel_y > 2: vel_state = 2
        
        p_height = 0
        if self.player_y < PLAYER_Y_GROUND - 100: p_height = 2
        elif self.player_y < PLAYER_Y_GROUND - 10: p_height = 1
        
        return (closest_dist, obs_type, obs_height, p_height, vel_state)

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
        self.current_difficulty = self.world_level + (self.score / 10.0)
        
        nearest_danger_dist = 999
        danger_type = None
        for obs in self.obstacles:
            dist = obs['x'] - (PLAYER_X + PLAYER_SIZE)
            if dist > -20:
                if dist < nearest_danger_dist:
                    nearest_danger_dist = dist
                    danger_type = obs['type']

        if action == 1 and not self.is_jumping:
            self.player_vel_y = -JUMP_FORCE
            self.is_jumping = True
            if danger_type in ['goomba', 'pipe', 'pit', 'bullet'] and nearest_danger_dist < 200:
                reward = 10
            else:
                reward = -20 

        self.player_y += self.player_vel_y
        self.player_vel_y += GRAVITY
        
        if self.player_y >= PLAYER_Y_GROUND:
            is_over_pit = False
            for obs in self.obstacles:
                if obs['type'] == 'pit':
                    if obs['x'] - 10 < PLAYER_X + PLAYER_SIZE/2 < obs['x'] + obs['w'] + 10:
                        is_over_pit = True
                        break
            
            if is_over_pit:
                if self.player_y > PLAYER_Y_GROUND + 100:
                    self.game_over = True
                    reward = -1000 
            else:
                self.player_y = PLAYER_Y_GROUND
                self.is_jumping = False
                self.player_vel_y = 0

        self.spawn_timer += 1
        spawn_threshold = max(15, 60 - int(self.current_difficulty * 4))
        if self.spawn_timer > spawn_threshold:
            if random.random() < 0.08:
                types = ['goomba', 'pipe', 'koopa', 'pit', 'bullet']
                weights = [3, 2, 2, min(5, self.current_difficulty), min(4, self.current_difficulty)]
                otype = random.choices(types, weights=weights)[0]
                
                base_spd = 6.0 + (self.current_difficulty * 0.5)
                spd = min(15.0, base_spd) 
                
                if otype == 'goomba':
                    self.obstacles.append({'x': SCREEN_WIDTH, 'y': PLAYER_Y_GROUND + 10, 'w': 30, 'h': 30, 'type': 'goomba', 'speed': spd})
                elif otype == 'pipe':
                    self.obstacles.append({'x': SCREEN_WIDTH, 'y': PLAYER_Y_GROUND - 20, 'w': 40, 'h': 60, 'type': 'pipe', 'speed': spd})
                elif otype == 'koopa':
                    self.obstacles.append({'x': SCREEN_WIDTH, 'y': PLAYER_Y_GROUND - 70, 'w': 35, 'h': 35, 'type': 'koopa', 'speed': spd * 0.7})
                elif otype == 'pit':
                    self.obstacles.append({'x': SCREEN_WIDTH, 'y': PLAYER_Y_GROUND + 40, 'w': 90, 'h': 100, 'type': 'pit', 'speed': spd})
                elif otype == 'bullet':
                    self.obstacles.append({'x': SCREEN_WIDTH, 'y': PLAYER_Y_GROUND + 5, 'w': 45, 'h': 25, 'type': 'bullet', 'speed': spd * 1.6})
                
                self.spawn_timer = 0
        
        for obs in self.obstacles: obs['x'] -= obs['speed']
        for cloud in self.clouds: 
            cloud['x'] -= cloud['s']
            if cloud['x'] < -100: cloud['x'] = SCREEN_WIDTH

        player_rect = pygame.Rect(PLAYER_X + 10, self.player_y + 5, PLAYER_SIZE - 20, PLAYER_SIZE - 10)
        alive = not self.game_over
        
        for obs in self.obstacles:
            if obs['type'] == 'pit': continue
            obs_rect = pygame.Rect(obs['x'], obs['y'], obs['w'], obs['h'])
            if player_rect.colliderect(obs_rect):
                reward = -800 
                self.game_over = True
                alive = False
            
            if obs['x'] + obs['w'] < PLAYER_X and not obs.get('passed', False):
                reward = 300 if obs['type'] == 'pit' else 150 
                obs['passed'] = True
                self.score += 1

        if alive: reward += 1.5
        self.obstacles = [o for o in self.obstacles if o['x'] + o['w'] > -100]
        return reward

    def draw(self):
        if not self.rendering_enabled: return
        self.screen.fill(SKY_BLUE)
        
        for c in self.clouds:
            pygame.draw.ellipse(self.screen, CLOUD_WHITE, (c['x'], c['y'], 60, 30))

        # 地面と穴
        current_x = 0
        sorted_pits = sorted([o for o in self.obstacles if o['type'] == 'pit'], key=lambda x: x['x'])
        for pit in sorted_pits:
            if pit['x'] > current_x:
                pygame.draw.rect(self.screen, GROUND_BROWN, (current_x, PLAYER_Y_GROUND + PLAYER_SIZE, pit['x'] - current_x, SCREEN_HEIGHT))
            current_x = pit['x'] + pit['w']
        if current_x < SCREEN_WIDTH:
            pygame.draw.rect(self.screen, GROUND_BROWN, (current_x, PLAYER_Y_GROUND + PLAYER_SIZE, SCREEN_WIDTH - current_x, SCREEN_HEIGHT))

        pygame.draw.rect(self.screen, MARIO_BLUE, (PLAYER_X + 5, self.player_y + 15, PLAYER_SIZE - 10, 20)) 
        pygame.draw.rect(self.screen, MARIO_SKIN, (PLAYER_X + 10, self.player_y + 5, 20, 15)) 
        pygame.draw.rect(self.screen, MARIO_RED, (PLAYER_X + 5, self.player_y, 25, 8)) 
        
        for obs in self.obstacles:
            if obs['type'] == 'goomba':
                pygame.draw.rect(self.screen, GOOMBA_BROWN, (obs['x'], obs['y'], obs['w'], obs['h']), border_radius=5)
            elif obs['type'] == 'pipe':
                pygame.draw.rect(self.screen, PIPE_GREEN, (obs['x'], obs['y'], obs['w'], obs['h']))
            elif obs['type'] == 'koopa':
                pygame.draw.rect(self.screen, KOOPA_GREEN, (obs['x'], obs['y'], obs['w'], obs['h']), border_radius=10)
            elif obs['type'] == 'bullet':
                pygame.draw.rect(self.screen, BULLET_BLACK, (obs['x'], obs['y'], obs['w'], obs['h']), border_top_left_radius=10, border_bottom_left_radius=10)
            elif obs['type'] == 'pit':
                pygame.draw.rect(self.screen, SKY_BLUE, (obs['x'], PLAYER_Y_GROUND + PLAYER_SIZE, obs['w'], SCREEN_HEIGHT))

        # UI
        stats = [
            f"世代: {self.episode}",
            f"スコア: {self.score} (最高: {self.high_score})",
            f"ワールドレベル: {self.world_level:.2f}",
            f"現在難易度: {self.current_difficulty:.2f}",
            f"AI探索率: {self.epsilon:.4f}",
            f"速度: {self.fps if self.fps < MAX_FPS else '無制限'} [↑/↓]"
        ]
        for i, text in enumerate(stats):
            img = self.font.render(text, True, TEXT_COLOR)
            self.screen.blit(img, (20, 20 + i*25))
        pygame.display.flip()

    def draw_fast_msg(self):
        self.screen.fill((30, 30, 30))
        msg = self.font.render(f"超高速学習中... (世代: {self.episode} / Lv: {self.world_level:.2f})", True, (0, 255, 100))
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
                    if event.key == pygame.K_UP: self.fps = min(self.fps + 200, MAX_FPS)
                    if event.key == pygame.K_DOWN: self.fps = max(self.fps - 200, 30)
                    if event.key == pygame.K_v:
                        self.rendering_enabled = not self.rendering_enabled
                        if not self.rendering_enabled: self.draw_fast_msg()

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

            self.draw()
            if self.fps < MAX_FPS: self.clock.tick(self.fps)

        pygame.quit()

if __name__ == "__main__":
    ai = MarioGameAI()
    ai.run()