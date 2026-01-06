# AI価格予測システム ✨
# インストール: pip install yfinance pandas numpy scikit-learn matplotlib pillow
# 実行方法: python 14_price_predictor.py
# Select Interpreter: Python 3.11.9

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import warnings
import ssl
import time
import os

# SSL証明書エラー対策
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except:
    pass

# 警告の抑制
warnings.simplefilter('ignore')

# --- 市場予測エンジン (既存のシステムを完全に継承) ---
class MarketPredictorEngine:
    """市場予測のロジックを担当するクラス"""
    def __init__(self, ticker, period="2y", interval="1d"):
        self.ticker = ticker
        self.period = period
        self.interval = interval
        self.features = ['SMA_Ratio', 'RSI', 'Volatility', 'Momentum_5d', 'Volume_Change']
        self.model = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42)
        self.df = None

    def fetch_and_prepare(self):
        """データの取得と特徴量生成"""
        try:
            if not self.ticker:
                return None, "銘柄コードを入力または選択してください。"

            df = yf.download(self.ticker, period=self.period, interval=self.interval, auto_adjust=True, progress=False)
            
            if df is None or df.empty:
                return None, "有効なデータを取得できませんでした。"

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            if 'Close' not in df.columns:
                return None, "終値データ(Close)が見つかりません。"

            if len(df) < 35:
                return None, f"データ数が不足しています（現在 {len(df)}件）。"
            
            df = df.copy()
            df['SMA_5'] = df['Close'].rolling(window=5).mean()
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
            df['SMA_Ratio'] = df['SMA_5'] / df['SMA_20']
            
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 1e-9)
            df['RSI'] = 100 - (100 / (1 + rs))
            
            df['Volatility'] = np.log(df['Close'] / df['Close'].shift(1)).rolling(window=20).std()
            df['Momentum_5d'] = df['Close'] / df['Close'].shift(5) - 1
            df['Volume_Change'] = df['Volume'].pct_change()
            
            df.dropna(subset=self.features, inplace=True)
            self.df = df
            return df, None
        except Exception as e:
            return None, f"エラーが発生しました:\n{str(e)}"

    def train_and_predict(self):
        """学習と予測"""
        if self.df is None or len(self.df) < 20: 
            return None
        
        try:
            df = self.df.copy()
            df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
            
            predict_row = df.iloc[[-1]].copy()
            train_df = df.dropna(subset=['Target']).copy()
            
            X = train_df[self.features]
            y = train_df['Target']
            
            split = max(int(len(X) * 0.8), len(X) - 20)
            if split <= 0 or split >= len(X):
                self.model.fit(X, y)
                accuracy = 0.5
            else:
                X_train, X_test = X.iloc[:split], X.iloc[split:]
                y_train, y_test = y.iloc[:split], y.iloc[split:]
                self.model.fit(X_train, y_train)
                accuracy = accuracy_score(y_test, self.model.predict(X_test))
                self.model.fit(X, y)
            
            prob = self.model.predict_proba(predict_row[self.features])[0]
            prediction = np.argmax(prob)
            
            return {
                "prediction": prediction,
                "probability": prob[prediction],
                "accuracy": accuracy,
                "last_close": predict_row['Close'].iloc[0],
                "last_date": predict_row.index[0].strftime('%Y-%m-%d')
            }
        except Exception:
            return None

class PredictorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI価格予測システム ✨")
        
        # ウィンドウサイズ：大型標準サイズの 1400x900
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数 (シリーズ共通)
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"        # 緑
        self.ALERT_COLOR = "#E74C3C"       # 赤

        self.setup_ui()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="📈 AI価格予測システム", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：左(設定)1, 右(表示)4
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=4)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=350)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        config_frame = tk.LabelFrame(self.left_panel, text=" ⚙️ 予測設定 ", 
                                    font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        config_frame.pack(fill=tk.X, pady=(0, 10))

        # 銘柄選択
        tk.Label(config_frame, text="銘柄コードを入力または選択:", bg=self.BG_WHITE, font=("Meiryo", 9)).pack(anchor="w", padx=10, pady=(10, 0))
        ticker_options = [
            "BTC-USD", "ETH-USD", "7203.T", "9984.T", "8306.T", "^N225", 
            "AAPL", "NVDA", "TSLA", "MSFT", "GOOGL", "AMZN"
        ]
        self.combo_ticker = ttk.Combobox(config_frame, values=ticker_options, font=("Consolas", 11))
        self.combo_ticker.insert(0, "BTC-USD")
        self.combo_ticker.pack(fill=tk.X, padx=10, pady=5)
        
        # 期間選択
        tk.Label(config_frame, text="データ学習期間:", bg=self.BG_WHITE, font=("Meiryo", 9)).pack(anchor="w", padx=10, pady=(5, 0))
        self.combo_period = ttk.Combobox(config_frame, values=["1y", "2y", "5y", "max"], state="readonly", font=("Consolas", 11))
        self.combo_period.set("2y")
        self.combo_period.pack(fill=tk.X, padx=10, pady=5)

        # 実行ボタン
        self.run_btn = tk.Button(self.left_panel, text="AI分析を開始 🚀", 
                                command=self.start_analysis_thread,
                                bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                relief=tk.FLAT, cursor="hand2", pady=15)
        self.run_btn.pack(fill=tk.X, pady=10)

        # 案内
        guide_text = "【ヒント】\n yfinanceに対応した銘柄コード\nを入力することで、あらゆる市場の\nトレンドを予測可能です。"
        tk.Label(self.left_panel, text=guide_text, bg="#FFFBEB", fg="#95A5A6", 
                 font=("Meiryo", 9), justify=tk.LEFT).pack(side=tk.BOTTOM, pady=20)

        # --- 右側：プレビュー＆チャートエリア ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        # 1. 予測レポートカード
        report_frame = tk.LabelFrame(self.right_panel, text=" 📊 AI予測レポート ", 
                                    font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        report_frame.pack(fill=tk.X, pady=(0, 15))

        self.report_inner = tk.Frame(report_frame, bg=self.BG_WHITE, padx=20, pady=15)
        self.report_inner.pack(fill=tk.X)

        self.lbl_predict = tk.Label(self.report_inner, text="銘柄を選択して分析ボタンを押してください", 
                                   font=("Meiryo", 16, "bold"), bg=self.BG_WHITE, fg=self.TEXT_COLOR)
        self.lbl_predict.pack()

        self.prob_bar = ttk.Progressbar(self.report_inner, orient="horizontal", mode="determinate")
        self.prob_bar.pack(fill=tk.X, pady=15)
        
        self.lbl_stats = tk.Label(self.report_inner, text="", bg=self.BG_WHITE, font=("Meiryo", 10), fg="#333")
        self.lbl_stats.pack()

        # 2. チャート表示エリア
        chart_frame = tk.LabelFrame(self.right_panel, text=" 📈 市場トレンド・インジケーター ", 
                                    font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        chart_frame.pack(fill=tk.BOTH, expand=True)

        self.chart_container = tk.Frame(chart_frame, bg=self.BG_WHITE)
        self.chart_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.loading_label = tk.Label(self.right_panel, text="", fg=self.PRIMARY_COLOR, bg="#FFFBEB", font=("Meiryo", 10, "italic"))
        self.loading_label.pack(pady=5)

    def start_analysis_thread(self):
        ticker = self.combo_ticker.get().strip().upper()
        if not ticker:
            messagebox.showwarning("入力エラー", "銘柄を入力してください。")
            return
        
        self.run_btn.config(state="disabled", text="AIが分析中...", bg="#BDC3C7")
        self.loading_label.config(text=f"AIが {ticker} の膨大な過去データを学習しています...")
        
        threading.Thread(target=self.run_analysis, args=(ticker,), daemon=True).start()

    def run_analysis(self, ticker):
        engine = MarketPredictorEngine(ticker, period=self.combo_period.get())
        df, error = engine.fetch_and_prepare()
        
        if error:
            self.root.after(0, lambda: self.show_error(error))
            return

        result = engine.train_and_predict()
        if result is None:
            self.root.after(0, lambda: self.show_error("予測モデルの構築に失敗しました。"))
            return
        
        self.root.after(0, lambda: self.update_ui(df, result, ticker))

    def show_error(self, msg):
        messagebox.showerror("エラー", msg)
        self.run_btn.config(state="normal", text="AI分析を開始 🚀", bg=self.PRIMARY_COLOR)
        self.loading_label.config(text="")

    def update_ui(self, df, result, ticker):
        # 予測方向の表示
        direction = "上昇予測 (UP) 📈" if result["prediction"] == 1 else "下落予測 (DOWN) 📉"
        color = self.SAFE_COLOR if result["prediction"] == 1 else self.ALERT_COLOR
        
        self.lbl_predict.config(text=direction, fg=color)
        self.prob_bar["value"] = result["probability"] * 100
        
        stats_text = (
            f"銘柄: {ticker}  |  最終終値: {result['last_close']:,.2f} ({result['last_date']})\n"
            f"AI確信度: {result['probability']:.1%}  |  バックテスト精度(参考): {result['accuracy']:.1%}"
        )
        self.lbl_stats.config(text=stats_text)

        # グラフ描画エリアのクリア
        for widget in self.chart_container.winfo_children():
            widget.destroy()

        # Figureの作成 (2つのグラフを表示するために縦長に設定)
        fig = Figure(figsize=(10, 8), dpi=100, facecolor='#ffffff')
        
        # 上段: 価格チャート
        ax1 = fig.add_subplot(211)
        plot_df = df.tail(100)
        ax1.plot(plot_df.index, plot_df['Close'], color=self.PRIMARY_COLOR, lw=2.5, label="Close Price")
        ax1.fill_between(plot_df.index, plot_df['Close'], color=self.PRIMARY_COLOR, alpha=0.1)
        ax1.set_title(f"{ticker} - Price Trend", fontsize=11, fontweight='bold')
        ax1.grid(True, linestyle='--', alpha=0.5)
        ax1.legend()

        # 下段: RSIチャート
        ax2 = fig.add_subplot(212)
        ax2.plot(plot_df.index, plot_df['RSI'], color="#3498DB", lw=1.5, label="RSI (14)")
        ax2.axhline(70, color=self.ALERT_COLOR, linestyle='--', alpha=0.6, label="Overbought (70)")
        ax2.axhline(30, color=self.SAFE_COLOR, linestyle='--', alpha=0.6, label="Oversold (30)")
        ax2.set_ylim(0, 100)
        ax2.set_title("RSI Indicator", fontsize=11, fontweight='bold')
        ax2.grid(True, linestyle='--', alpha=0.5)
        ax2.legend(loc='upper right', fontsize='small')
        
        fig.tight_layout() # 要素の重なりを自動解消
        
        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        self.run_btn.config(state="normal", text="AI分析を開始 🚀", bg=self.PRIMARY_COLOR)
        self.loading_label.config(text="分析完了 ✅")

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = PredictorApp(root)
    root.mainloop()