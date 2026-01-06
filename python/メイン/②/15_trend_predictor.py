# AIトレンド予測・感情分析システム ✨
# インストール: pip install tkinter janome matplotlib pillow requests
# 実行方法: python 15_trend_predictor.py
# Select Interpreter: Python 3.11.9

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from janome.tokenizer import Tokenizer
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import requests
import json
import threading
import time
import random
import datetime
import os

# --- 感情分析エンジン ---
class SentimentAI:
    def __init__(self):
        self.tokenizer = Tokenizer()
        # 簡易的な感情極性辞書 (ポジティブ: 1.0, ネガティブ: -1.0)
        self.pn_dict = {
            "最高": 1.0, "素晴らしい": 1.0, "欲しい": 0.8, "バズ": 0.5, "便利": 0.7, "神": 0.9,
            "可愛い": 0.6, "おすすめ": 0.5, "期待": 0.4, "面白い": 0.6, "楽しみ": 0.5,
            "最悪": -1.0, "ゴミ": -0.8, "嫌い": -0.7, "ひどい": -0.9, "炎上": -0.6, "ショック": -0.5,
            "失望": -0.8, "高い": -0.2, "怪しい": -0.4, "無能": -0.9, "バカ": -1.0, "死ね": -1.0
        }

    def get_score(self, text):
        """文章の感情スコア (-1.0 ～ 1.0) を計算"""
        tokens = self.tokenizer.tokenize(text)
        score = 0
        count = 0
        for token in tokens:
            word = token.surface
            base = token.base_form
            if word in self.pn_dict:
                score += self.pn_dict[word]
                count += 1
            elif base in self.pn_dict:
                score += self.pn_dict[base]
                count += 1
        
        if count == 0: return 0.0
        return score / count

class TrendPredictorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIトレンド予測・感情分析システム ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数 (シリーズ統一デザイン)
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"        # 緑
        self.ALERT_COLOR = "#E74C3C"       # 赤

        # AIの初期化
        self.sentiment_ai = SentimentAI()
        
        # データ管理
        self.time_labels = []
        self.sentiment_history = []
        self.mock_data_mode = True 
        self.is_monitoring = False
        
        self.setup_ui()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="📈 AIトレンド予測・感情分析", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：左(設定)1, 右(表示)4
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=4)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 1. 検索設定
        config_frame = tk.LabelFrame(self.left_panel, text=" ⚙️ 解析設定 ", 
                                    font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        config_frame.pack(fill=tk.X, pady=5)

        tk.Label(config_frame, text="分析キーワード:", bg=self.BG_WHITE, font=("Meiryo", 9)).pack(anchor="w", padx=15, pady=(15, 0))
        self.keyword_entry = tk.Entry(config_frame, font=("Meiryo", 12), relief=tk.SOLID, bd=1)
        self.keyword_entry.pack(fill=tk.X, padx=15, pady=10)
        self.keyword_entry.insert(0, "新発売のスマホ")

        tk.Label(config_frame, text="Twitter API Bearer Token (任意):", bg=self.BG_WHITE, font=("Meiryo", 9)).pack(anchor="w", padx=15, pady=(5, 0))
        self.token_entry = tk.Entry(config_frame, font=("Consolas", 10), relief=tk.SOLID, bd=1, show="*")
        self.token_entry.pack(fill=tk.X, padx=15, pady=10)

        self.mode_var = tk.BooleanVar(value=True)
        tk.Checkbutton(config_frame, text="シミュレーションモードを使用", variable=self.mode_var, 
                       bg=self.BG_WHITE, font=("Meiryo", 9)).pack(anchor="w", padx=15, pady=5)

        # 2. 実行ボタン
        self.run_btn = tk.Button(self.left_panel, text="トレンド予測を開始 🚀", 
                                command=self.toggle_monitoring,
                                bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                relief=tk.FLAT, cursor="hand2", pady=15)
        self.run_btn.pack(fill=tk.X, pady=10)

        # 3. 予測サマリー
        self.summary_frame = tk.LabelFrame(self.left_panel, text=" 🧠 AI予測レポート ", 
                                          font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                          fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        self.summary_frame.pack(fill=tk.X, pady=5)

        self.lbl_prediction = tk.Label(self.summary_frame, text="待機中", bg=self.BG_WHITE, 
                                      font=("Meiryo", 14, "bold"), fg=self.TEXT_COLOR, wraplength=300)
        self.lbl_prediction.pack(pady=20, padx=10)

        # 4. 操作ヒント (修正箇所: LabelからLabelFrameへ変更し配置を固定)
        guide_frame = tk.LabelFrame(self.left_panel, text=" 💡 予測のヒント ", 
                                   font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        guide_frame.pack(fill=tk.X, pady=5)
        
        guide_text = "・急激なスコア低下は「炎上」\n・急激な上昇は「バズ」を意味します。\n・APIキー未入力時は予測の\n　デモンストレーションを行います。"
        guide_label = tk.Label(guide_frame, text=guide_text, bg=self.BG_WHITE, justify=tk.LEFT, 
                               font=("Meiryo", 9), fg=self.TEXT_COLOR, padx=10, pady=10)
        guide_label.pack(fill=tk.X)


        # --- 右側：グラフ＆ログパネル ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        # 1. 感情推移グラフ
        graph_frame = tk.LabelFrame(self.right_panel, text=" 📊 感情スコアのリアルタイム推移 (ポジティブ ↑ / ネガティブ ↓) ", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        graph_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        self.fig, self.ax = plt.subplots(figsize=(8, 4), dpi=100)
        self.fig.patch.set_facecolor('white')
        self.ax.set_ylim(-1.1, 1.1)
        self.ax.axhline(0, color='gray', linestyle='--', alpha=0.5)
        self.line, = self.ax.plot([], [], color=self.PRIMARY_COLOR, marker='o', lw=2)
        
        self.canvas_graph = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas_graph.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 2. 収集ログ
        log_frame = tk.LabelFrame(self.right_panel, text=" 📜 最新の投稿解析ログ ", 
                                 font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.X)

        self.log_area = scrolledtext.ScrolledText(log_frame, height=8, font=("Meiryo", 10), 
                                                 bg="#F7F7F7", relief=tk.FLAT, padx=10, pady=10)
        self.log_area.pack(fill=tk.X, padx=5, pady=5)

    def write_log(self, message):
        self.log_area.insert(tk.END, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)

    def toggle_monitoring(self):
        if not self.is_monitoring:
            self.is_monitoring = True
            self.run_btn.config(text="解析を停止する ⏹", bg=self.ALERT_COLOR)
            self.write_log(f"解析開始: キーワード「{self.keyword_entry.get()}」")
            self.time_labels = []
            self.sentiment_history = []
            threading.Thread(target=self.monitoring_loop, daemon=True).start()
        else:
            self.is_monitoring = False
            self.run_btn.config(text="トレンド予測を開始 🚀", bg=self.PRIMARY_COLOR)
            self.write_log("解析を停止しました。")

    def monitoring_loop(self):
        while self.is_monitoring:
            keyword = self.keyword_entry.get()
            token = self.token_entry.get()
            is_mock = self.mode_var.get()
            
            current_tweets = []
            if not is_mock and token:
                current_tweets = self.fetch_real_tweets(keyword, token)
            else:
                current_tweets = self.generate_mock_tweets(keyword)

            avg_score = 0
            if current_tweets:
                total_s = sum(self.sentiment_ai.get_score(t) for t in current_tweets)
                avg_score = total_s / len(current_tweets)
                self.root.after(0, lambda: self.write_log(f"解析中: 「{current_tweets[0][:40]}...」"))
            
            self.sentiment_history.append(avg_score)
            self.time_labels.append(datetime.datetime.now().strftime("%H:%M"))
            if len(self.sentiment_history) > 20:
                self.sentiment_history.pop(0)
                self.time_labels.pop(0)

            self.root.after(0, self.update_dashboard)
            time.sleep(2 if is_mock else 15)

    def fetch_real_tweets(self, keyword, token):
        try:
            url = f"https://api.twitter.com/2/tweets/search/recent?query={requests.utils.quote(keyword)}&max_results=10"
            headers = {"Authorization": f"Bearer {token}"}
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                return [t['text'] for t in data.get('data', [])]
            else:
                self.root.after(0, lambda: self.write_log(f"APIエラー: {res.status_code}"))
                self.mode_var.set(True)
                return []
        except Exception:
            return []

    def generate_mock_tweets(self, keyword):
        pos = [f"{keyword}最高！", f"{keyword}を予約した", f"{keyword}が神"]
        neg = [f"{keyword}最悪...", f"{keyword}が高すぎ", f"{keyword}が炎上"]
        neu = [f"{keyword}について調べ中", f"{keyword}ってどう？"]
        t_count = len(self.sentiment_history)
        if 5 < t_count < 10: pool = neg * 3 + neu
        elif t_count >= 15: pool = pos * 3 + neu
        else: pool = pos + neg + neu
        return [random.choice(pool) for _ in range(5)]

    def update_dashboard(self):
        self.ax.clear()
        self.ax.set_ylim(-1.1, 1.1)
        self.ax.axhline(0, color='gray', linestyle='--', alpha=0.3)
        self.ax.set_title(f"Sentiment Trend: {self.keyword_entry.get()}", fontsize=10)
        x = range(len(self.sentiment_history))
        y = self.sentiment_history
        self.ax.plot(x, y, color=self.PRIMARY_COLOR, marker='o', lw=2)
        if len(self.time_labels) > 0:
            self.ax.set_xticks(x[::2])
            self.ax.set_xticklabels(self.time_labels[::2], rotation=45, fontsize=8)
        self.canvas_graph.draw()

        if len(self.sentiment_history) < 3:
            self.lbl_prediction.config(text="解析中...", fg=self.TEXT_COLOR)
            return

        recent_diff = self.sentiment_history[-1] - self.sentiment_history[-2]
        avg_last_3 = sum(self.sentiment_history[-3:]) / 3

        if recent_diff < -0.3:
            msg = "🚨 【緊急】 炎上予兆を検知！\n対応の検討をお勧めします。"
            color = self.ALERT_COLOR
        elif recent_diff > 0.3:
            msg = "🔥 【好調】 バズ予兆あり！\nプロモーションの強化チャンス！"
            color = self.SAFE_COLOR
        elif avg_last_3 < -0.4:
            msg = "⚠️ 【注意】 停滞・不評の状態\nイメージ回復の必要があります。"
            color = "#E67E22"
        elif avg_last_3 > 0.4:
            msg = "✨ 【良好】 安定した人気\n高い満足度が維持されています。"
            color = self.SAFE_COLOR
        else:
            msg = "📊 【安定】 平常運転\n大きな変化は見られません。"
            color = self.TEXT_COLOR
        self.lbl_prediction.config(text=msg, fg=color)

    def on_closing(self):
        self.is_monitoring = False
        plt.close(self.fig)
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception: pass
    app = TrendPredictorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()