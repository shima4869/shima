# AI学習型ヘビゲーム
# インストール: pip install pygame numpy
# 実行方法: python 21_snake_ai_learning.py
# Select Interpreter: Python 3.11.9

import pygame
import random
import numpy as np
import time

# --- ゲームの設定 ---
BLOCK_SIZE = 20
SPEED = 20           # 初期の表示速度（学習が進まないときはここを大きくすると高速化）
GRID_W, GRID_H = 20, 20 # グリッドの数（盤面を小さくして学習しやすくする）
SCREEN_WIDTH = GRID_W * BLOCK_SIZE
SCREEN_HEIGHT = GRID_H * BLOCK_SIZE

# 色の定義
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
GRAY = (100, 100, 100)

# 行動の定義
# 0:上, 1:右, 2:下, 3:左
ACTIONS = [0, 1, 2, 3]

class SnakeGameAI:
    def __init__(self):
        pygame.init()
        self.display = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption('Snake AI Learning')
        self.clock = pygame.time.Clock()
        self.reset()
        
        # --- Q学習の設定 ---
        # Qテーブル: 経験を記録する辞書 {状態: [上, 右, 下, 左の評価値]}
        self.q_table = {}
        self.learning_rate = 0.1  # 学習率（新しい情報をどれくらい重視するか）
        self.discount_factor = 0.9 # 割引率（将来の報酬をどれくらい重視するか）
        self.epsilon = 1.0        # 探索率（最初は100%ランダムに行動する）
        self.epsilon_decay = 0.995 # 徐々にランダム行動を減らす
        self.epsilon_min = 0.01

        self.episode = 0
        self.high_score = 0

    def reset(self):
        # ゲーム状態のリセット
        self.direction = 1 # 最初は右向き
        self.head = [GRID_W//2, GRID_H//2] # 真ん中からスタート
        self.snake = [self.head[:], [self.head[0]-1, self.head[1]], [self.head[0]-2, self.head[1]]]
        self.score = 0
        self.place_food()
        self.frame_iteration = 0

    def place_food(self):
        # 餌をランダムに配置
        while True:
            self.food = [random.randint(0, GRID_W-1), random.randint(0, GRID_H-1)]
            if self.food not in self.snake:
                break

    def get_state(self):
        # 現在の状況（State）をAIが理解できる形にする
        # ここでは「餌がどの方向にあるか」と「身の回りの危険」を情報として渡す
        head_x, head_y = self.head
        
        # 危険の検知（壁または自分の体があるか）
        # [上, 右, 下, 左] の順
        danger = [False, False, False, False]
        
        # 上が危険か？
        if head_y - 1 < 0 or [head_x, head_y - 1] in self.snake:
            danger[0] = True
        # 右が危険か？
        if head_x + 1 >= GRID_W or [head_x + 1, head_y] in self.snake:
            danger[1] = True
        # 下が危険か？
        if head_y + 1 >= GRID_H or [head_x, head_y + 1] in self.snake:
            danger[2] = True
        # 左が危険か？
        if head_x - 1 < 0 or [head_x - 1, head_y] in self.snake:
            danger[3] = True

        # 餌の方向
        food_dir = [False, False, False, False] # 上, 右, 下, 左
        if self.food[1] < head_y: food_dir[0] = True # 餌は上にある
        if self.food[0] > head_x: food_dir[1] = True # 餌は右にある
        if self.food[1] > head_y: food_dir[2] = True # 餌は下にある
        if self.food[0] < head_x: food_dir[3] = True # 餌は左にある

        # 状態をタプル（変更不可リスト）にして返す
        # 例: (危険[F,T,F,F], 餌[T,F,F,F]) -> 右が壁で、餌は上にある状態
        state = (tuple(danger), tuple(food_dir))
        return state

    def get_action(self, state):
        # 状態に対する行動を決める
        # まだ経験したことのない状態なら、Qテーブルに追加
        if state not in self.q_table:
            self.q_table[state] = [0, 0, 0, 0]

        # Epsilon-Greedy法
        # 最初はランダムに動いて試行錯誤し、徐々に学習した結果を使うようにする
        if random.random() < self.epsilon:
            return random.randint(0, 3) # ランダム行動
        else:
            return np.argmax(self.q_table[state]) # 一番評価の高い行動を選ぶ

    def step(self, action):
        # 1ステップ進める
        self.frame_iteration += 1
        
        # 行動の実行（方向転換）
        # ただし、逆方向（右に進んでいるときに左など）には行けない
        clock_wise = [0, 1, 2, 3] # 上, 右, 下, 左
        
        # 現在の向きと逆向きの入力は無視するロジックを入れると学習が早いが
        # 今回はAIに「逆に行くと死ぬ」ことも学ばせるため、そのまま入力を受け付ける
        self.direction = action

        # 頭を移動
        x, y = self.head
        if self.direction == 0: y -= 1
        elif self.direction == 1: x += 1
        elif self.direction == 2: y += 1
        elif self.direction == 3: x -= 1
        self.head = [x, y]

        # 報酬の設定
        reward = 0
        game_over = False

        # 衝突判定（壁または自分の体）
        if (x < 0 or x >= GRID_W or y < 0 or y >= GRID_H or self.head in self.snake):
            game_over = True
            reward = -10 # 罰
            return reward, game_over, self.score

        # 移動
        self.snake.insert(0, self.head)

        # 餌を食べたか
        if self.head == self.food:
            self.score += 1
            reward = 10 # 報酬
            self.place_food()
        else:
            self.snake.pop()
            # 餌を食べずにただ移動しただけ
            # 長い間うろうろするのを防ぐため、少しだけ罰を与えるか、餌に近づいたら報酬を与える
            # ここではシンプルにするため、何もしない（0）か、わずかな罰（-0.1）を与える
            reward = -0.1 

        # 無限ループ防止（あまりに長く餌を食べられない場合強制終了）
        if self.frame_iteration > 100 * len(self.snake):
            game_over = True
            reward = -10

        return reward, game_over, self.score

    def train(self):
        # メインループ
        while True:
            # 現在の状態を取得
            state_old = self.get_state()
            
            # 行動を決定
            action = self.get_action(state_old)
            
            # 行動を実行し、結果（報酬と次の状態）を受け取る
            reward, done, score = self.step(action)
            state_new = self.get_state()

            # Q学習の数式（ベルマン方程式）でテーブルを更新
            # 新しいQ値 = 古いQ値 + 学習率 * (報酬 + 割引率 * 次の状態の最大Q値 - 古いQ値)
            
            if state_new not in self.q_table:
                self.q_table[state_new] = [0, 0, 0, 0]
                
            old_value = self.q_table[state_old][action]
            next_max = np.max(self.q_table[state_new])
            
            new_value = (1 - self.learning_rate) * old_value + self.learning_rate * (reward + self.discount_factor * next_max)
            self.q_table[state_old][action] = new_value

            # 描画
            self.draw()

            # ゲームオーバー時の処理
            if done:
                self.reset()
                self.episode += 1
                # ランダム率を少し下げる（賢くなっていく）
                if self.epsilon > self.epsilon_min:
                    self.epsilon *= self.epsilon_decay
                
                print(f"Game: {self.episode}, Score: {score}, High Score: {self.high_score}, Epsilon: {self.epsilon:.2f}")
                if score > self.high_score:
                    self.high_score = score

            # イベント処理（終了ボタンなど）
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()
                # キー操作で速度変更
                if event.type == pygame.KEYDOWN:
                    global SPEED
                    if event.key == pygame.K_UP:
                        SPEED += 10000
                    elif event.key == pygame.K_DOWN:
                        SPEED = max(1, SPEED - 10000)

    def draw(self):
        self.display.fill(BLACK)
        
        # 餌の描画
        pygame.draw.rect(self.display, RED, pygame.Rect(self.food[0]*BLOCK_SIZE, self.food[1]*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))
        
        # ヘビの描画
        for pt in self.snake:
            pygame.draw.rect(self.display, GREEN, pygame.Rect(pt[0]*BLOCK_SIZE, pt[1]*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))
            # 枠線
            pygame.draw.rect(self.display, BLUE, pygame.Rect(pt[0]*BLOCK_SIZE, pt[1]*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 1)

        # 情報表示
        font = pygame.font.SysFont('arial', 20)
        text = font.render(f"Score: {self.score}  Game: {self.episode}  Speed: {SPEED}", True, WHITE)
        self.display.blit(text, [0, 0])
        
        pygame.display.flip()
        self.clock.tick(SPEED)

if __name__ == '__main__':
    game = SnakeGameAI()
    game.train()