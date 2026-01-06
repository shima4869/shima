# AI倒立振子・自動制御シミュレーター ✨
# インストール: pip install tkinter numpy pillow
# 実行方法: python 19_self_balancing_robot_ai.py
# Select Interpreter: Python 3.11.9

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import numpy as np
import random
import time
import threading
import os
import sys
import math
from PIL import Image, ImageTk

# --- 物理定数 ---
GRAVITY = 9.8       # 重力加速度
L = 1.0             # 棒の長さ
M = 1.0             # 棒の質量
DT = 0.05           # 1ステップの時間

class QLearningAgent:
    """Q-learningアルゴリズムによる強化学習エージェント"""
    def __init__(self):
        # 状態の離散化分割数 (角度, 角速度)
        self.bins = [12, 12]
        # Qテーブル: [角度, 角速度, アクション]
        self.q_table = np.zeros((self.bins[0], self.bins[1], 3))
        
        self.learning_rate = 0.2    # 学習率 (α)
        self.discount_factor = 0.95 # 割引率 (γ)
        self.epsilon = 0.3          # 探索率 (ε)

    def get_state_index(self, angle, angular_velocity):
        """連続的な値をデジタル（インデックス）に変換"""
        a_idx = int(np.clip((angle + 0.5) * self.bins[0], 0, self.bins[0] - 1))
        v_idx = int(np.clip((angular_velocity + 3.0) / 6.0 * self.bins[1], 0, self.bins[1] - 1))
        return a_idx, v_idx

    def decide_action(self, state_idx):
        """ε-greedy法による行動選択"""
        if random.random() < self.epsilon:
            return random.randint(0, 2)
        return np.argmax(self.q_table[state_idx])

    def update(self, state, action, reward, next_state):
        """Q値の更新 (Q-Learning公式適用)"""
        best_next_action = np.argmax(self.q_table[next_state])
        td_target = reward + self.discount_factor * self.q_table[next_state][best_next_action]
        td_error = td_target - self.q_table[state][action]
        # リアルタイムに変更される self.learning_rate を使用
        self.q_table[state][action] += self.learning_rate * td_error

class RobotEnv:
    """ロボットの物理シミュレーション環境"""
    def __init__(self):
        self.reset()

    def reset(self):
        self.angle = random.uniform(-0.1, 0.1) 
        self.angular_velocity = 0.0          
        self.pos_x = 0.0                      
        self.steps = 0
        return self.angle, self.angular_velocity

    def step(self, action):
        self.steps += 1
        force = (action - 1) * 15.0 
        angular_accel = (GRAVITY * math.sin(self.angle) + force * math.cos(self.angle)) / L
        
        self.angular_velocity += angular_accel * DT
        self.angle += self.angular_velocity * DT
        self.pos_x += (action - 1) * 0.1
        
        is_failed = abs(self.angle) > 0.6 
        reward = 1.0 - abs(self.angle) if not is_failed else -10.0
        
        return self.angle, self.angular_velocity, reward, is_failed

class RobotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI姿勢制御シミュレーター ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"
        self.SECONDARY_COLOR = "#FFCC33"
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"
        self.ALERT_COLOR = "#E74C3C"

        # AIと環境の初期化
        self.env = RobotEnv()
        self.agent = QLearningAgent()
        
        # 状態管理
        self.is_running = True
        self.is_training = False
        self.sim_speed = 0.01 # デフォルトの待ち時間
        self.episode_count = 0
        self.best_steps = 0
        
        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # メインタイトル
        header = tk.Frame(self.root, bg="#FFFBEB")
        header.pack(pady=15)
        tk.Label(header, text="🤖 AI倒立振子・自動制御シミュレーター", 
                 font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR).pack()

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=5)
        
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作・設定パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 1. AI・シミュレーション設定 (新設)
        config_frame = tk.LabelFrame(self.left_panel, text=" ⚙️ パラメータ設定 ", 
                                    font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        config_frame.pack(fill=tk.X, pady=(0, 10))

        # 学習速度 (Learning Rate)
        tk.Label(config_frame, text="学習速度 (Learning Rate):", bg=self.BG_WHITE, font=("Meiryo", 9)).pack(anchor="w", padx=15, pady=(10, 0))
        self.lr_scale = tk.Scale(config_frame, from_=0.01, to=1.0, resolution=0.01, orient=tk.HORIZONTAL,
                                bg=self.BG_WHITE, highlightthickness=0, command=self.update_params)
        self.lr_scale.set(0.2)
        self.lr_scale.pack(fill=tk.X, padx=15, pady=(0, 10))

        # 実行速度 (Wait Time)
        tk.Label(config_frame, text="シミュレーション速度 (低速 ←→ 高速):", bg=self.BG_WHITE, font=("Meiryo", 9)).pack(anchor="w", padx=15, pady=(5, 0))
        self.speed_scale = tk.Scale(config_frame, from_=0.05, to=0.001, resolution=0.001, orient=tk.HORIZONTAL,
                                   bg=self.BG_WHITE, highlightthickness=0, showvalue=False, command=self.update_speed)
        self.speed_scale.set(0.01)
        self.speed_scale.pack(fill=tk.X, padx=15, pady=(0, 15))

        # 2. 学習スイッチ
        self.train_btn = tk.Button(self.left_panel, text="学習を開始する ▶", 
                                  command=self.toggle_training,
                                  bg=self.SAFE_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                  relief=tk.FLAT, cursor="hand2", pady=15)
        self.train_btn.pack(fill=tk.X, pady=10)

        # 3. 学習ステータス
        status_frame = tk.LabelFrame(self.left_panel, text=" 📊 学習統計 ", 
                                    font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, pady=10)
        
        self.lbl_episode = tk.Label(status_frame, text="試行回数: 0", bg=self.BG_WHITE, font=("Meiryo", 10))
        self.lbl_episode.pack(anchor="w", padx=15, pady=5)
        
        self.lbl_steps = tk.Label(status_frame, text="生存ステップ: 0", bg=self.BG_WHITE, font=("Meiryo", 10))
        self.lbl_steps.pack(anchor="w", padx=15, pady=5)

        self.lbl_best = tk.Label(status_frame, text="最高記録: 0", bg=self.BG_WHITE, 
                                font=("Meiryo", 10, "bold"), fg=self.PRIMARY_COLOR)
        self.lbl_best.pack(anchor="w", padx=15, pady=5)

        # 4. 思考ログ
        log_frame = tk.LabelFrame(self.left_panel, text=" 📝 AI思考ログ ", 
                                 font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Consolas", 9), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- 右側：シミュレーション画面 ---
        self.right_panel = tk.Frame(self.main_container, bg=self.BG_WHITE, relief=tk.RIDGE, bd=2)
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        self.canvas = tk.Canvas(self.right_panel, bg="#2C3E50", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def update_params(self, _=None):
        """スライダーの値をAIエージェントに反映"""
        self.agent.learning_rate = float(self.lr_scale.get())

    def update_speed(self, _=None):
        """シミュレーションの待ち時間を更新"""
        self.sim_speed = float(self.speed_scale.get())

    def write_log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def toggle_training(self):
        self.is_training = not self.is_training
        if self.is_training:
            self.train_btn.config(text="学習を停止 ⏹", bg=self.ALERT_COLOR)
            self.write_log("学習開始。スライダーで速度を調整できます。")
            threading.Thread(target=self.learning_loop, daemon=True).start()
        else:
            self.train_btn.config(text="学習を開始する ▶", bg=self.SAFE_COLOR)
            self.write_log("学習を一時停止しました。")

    def learning_loop(self):
        """強化学習のメインループ"""
        while self.is_training:
            self.episode_count += 1
            angle, v = self.env.reset()
            state = self.agent.get_state_index(angle, v)
            
            while self.is_training:
                # 1. 行動選択
                action = self.agent.decide_action(state)
                
                # 2. 環境更新
                next_angle, next_v, reward, done = self.env.step(action)
                next_state = self.agent.get_state_index(next_angle, next_v)
                
                # 3. 学習 (現在のスライダー値に基づいた学習率で更新)
                self.agent.update(state, action, reward, next_state)
                
                state = next_state
                
                # UI更新
                self.root.after(0, lambda s=self.env.steps: self.lbl_steps.config(text=f"生存ステップ: {s}"))
                
                if done:
                    if self.env.steps > self.best_steps:
                        self.best_steps = self.env.steps
                        self.root.after(0, lambda: self.write_log(f"新記録! {self.best_steps}歩"))
                    break
                
                # 可変スピード
                time.sleep(self.sim_speed)

            self.root.after(0, lambda: self.lbl_episode.config(text=f"試行回数: {self.episode_count}"))
            self.root.after(0, lambda: self.lbl_best.config(text=f"最高記録: {self.best_steps}"))
            time.sleep(0.1)

    def draw_robot(self):
        self.canvas.delete("all")
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw < 50: return

        floor_y = ch * 0.7
        self.canvas.create_line(0, floor_y, cw, floor_y, fill="#5D6D7E", width=2)

        cx = cw / 2 + self.env.pos_x * 50
        cy = floor_y - 20 
        
        self.canvas.create_rectangle(cx-40, cy-20, cx+40, cy+20, fill="#ECF0F1", outline="#34495E", width=2)
        self.canvas.create_oval(cx-35, cy+10, cx-15, cy+30, fill="#34495E")
        self.canvas.create_oval(cx+15, cy+10, cx+35, cy+30, fill="#34495E")

        pendulum_len = 150
        px = cx + pendulum_len * math.sin(self.env.angle)
        py = cy - pendulum_len * math.cos(self.env.angle)
        
        self.canvas.create_line(cx, cy, px, py, fill=self.PRIMARY_COLOR, width=8, capstyle=tk.ROUND)
        self.canvas.create_oval(px-12, py-12, px+12, py+12, fill=self.SECONDARY_COLOR, outline="white")

        # ステータス表示
        status_color = "red" if abs(self.env.angle) > 0.6 else "#2ECC71"
        self.canvas.create_text(50, 40, text=f"角度: {math.degrees(self.env.angle):.1f}°", 
                               fill=status_color, font=("Meiryo", 14, "bold"), anchor="w")
        self.canvas.create_text(50, 70, text=f"学習率: {self.agent.learning_rate:.2f}", 
                               fill="white", font=("Consolas", 10), anchor="w")

    def update_loop(self):
        self.root.update_idletasks()
        self.draw_robot()
        if self.is_running:
            self.root.after(30, self.update_loop)

    def on_closing(self):
        self.is_running = False
        self.is_training = False
        self.root.destroy()
        sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = RobotApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()