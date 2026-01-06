# AIニュース要約ボット GUIアプリケーション
# インストール: pip install tkinter pillow feedparser requests beautifulsoup4 sumy
# 実行方法: python 11_news_bot.py
# Select Interpreter: Python 3.11.9

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import feedparser
import requests
from bs4 import BeautifulSoup
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer
import datetime
import urllib.parse
import threading
import time
import os

class NewsBotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIニュース要約ボット ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SUCCESS_COLOR = "#2ECC71"     # 緑

        # --- 既存システムの初期設定を継承 ---
        self.webhook_url = "https://discord.com/api/webhooks/1444232363637997659/c9oDNYEjj1dqTTGHaVzs4zCQMiH0ulc7hDAONZVHgH-rv_mB9ImpAKZLAF-NhJWe9i5x"
        self.default_keyword = "AI開発 Python"
        self.is_running = False

        self.setup_ui()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="📰 AIニュース要約ボット", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # 比率調整：左1, 右3
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：設定パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=350)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 検索設定フレーム
        config_frame = tk.LabelFrame(self.left_panel, text=" ⚙️ 配信設定 ", 
                                    font=("Meiryo", 10, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        config_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(config_frame, text="検索キーワード:", bg=self.BG_WHITE, font=("Meiryo", 9)).pack(anchor="w", padx=10, pady=(10, 0))
        self.keyword_entry = tk.Entry(config_frame, font=("Meiryo", 10), relief=tk.SOLID, bd=1)
        self.keyword_entry.insert(0, self.default_keyword)
        self.keyword_entry.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(config_frame, text="要約行数:", bg=self.BG_WHITE, font=("Meiryo", 9)).pack(anchor="w", padx=10, pady=(5, 0))
        self.count_spin = tk.Spinbox(config_frame, from_=1, to=10, font=("Meiryo", 10), relief=tk.SOLID, bd=1)
        self.count_spin.delete(0, "end")
        self.count_spin.insert(0, "3")
        self.count_spin.pack(fill=tk.X, padx=10, pady=(5, 15))

        # 実行ボタン
        self.run_btn = tk.Button(self.left_panel, text="ボットを稼働 🚀", 
                                command=self.start_bot_thread,
                                bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                relief=tk.FLAT, cursor="hand2", pady=15)
        self.run_btn.pack(fill=tk.X, pady=10)

        # ステータス表示
        self.status_label = tk.Label(self.left_panel, text="待機中", bg="#FFFBEB", 
                                    font=("Meiryo", 10, "bold"), fg=self.TEXT_COLOR)
        self.status_label.pack(pady=10)

        # 送信先情報
        webhook_info = tk.Label(self.left_panel, text=f"送信先: Discord\nWebhook設定済み", 
                               bg="#FFFBEB", fg="#95A5A6", font=("Meiryo", 8), justify=tk.LEFT)
        webhook_info.pack(side=tk.BOTTOM, pady=10)

        # --- 右側：プレビュー表示エリア ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        preview_frame = tk.LabelFrame(self.right_panel, text=" 📜 取得ニュースと要約のプレビュー ", 
                                     font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                     fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.log_area = scrolledtext.ScrolledText(preview_frame, font=("Meiryo", 10), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, state=tk.DISABLED,
                                                 padx=15, pady=15)
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def write_log(self, message, is_title=False):
        """画面ログに追記"""
        self.log_area.config(state=tk.NORMAL)
        timestamp = datetime.datetime.now().strftime("[%H:%M:%S] ")
        if is_title:
            self.log_area.insert(tk.END, f"\n--- {message} ---\n", "title")
            self.log_area.tag_config("title", foreground=self.PRIMARY_COLOR, font=("Meiryo", 10, "bold"))
        else:
            self.log_area.insert(tk.END, timestamp + message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    # --- 既存の処理システムを継承・統合 ---

    def get_google_news_url(self, keyword):
        encoded_keyword = urllib.parse.quote(keyword)
        return f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ja&gl=JP&ceid=JP:ja"

    def get_article_content(self, url):
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, "html.parser")
            paragraphs = soup.find_all("p")
            text = ""
            for p in paragraphs:
                content = p.get_text().strip()
                if len(content) > 30: 
                    text += content + "\n"
            return text
        except Exception as e:
            return ""

    def summarize_text(self, text, sentence_count):
        if not text:
            return ["（本文取得失敗）"]
        try:
            parser = PlaintextParser.from_string(text, Tokenizer("japanese"))
            summarizer = LexRankSummarizer()
            summarizer.stop_words = [" "] 
            summary = summarizer(parser.document, sentence_count)
            return [str(sentence) for sentence in summary]
        except:
            return ["（要約処理に失敗しました）"]

    def send_discord(self, title, summary_lines, link, keyword):
        summary_text = "".join([f"・{line}\n" for line in summary_lines])
        data = {
            "embeds": [{
                "title": title,
                "description": summary_text,
                "url": link,
                "color": 16760643, # オレンジ
                "footer": {"text": f"AI News Bot: {keyword}"},
                "timestamp": datetime.datetime.now().isoformat()
            }]
        }
        try:
            requests.post(self.webhook_url, json=data, timeout=10)
            return True
        except:
            return False

    def start_bot_thread(self):
        """非同期でボット処理を開始（GUIフリーズ防止）"""
        if self.is_running: return
        self.is_running = True
        self.run_btn.config(state=tk.DISABLED, text="取得中...", bg="#BDC3C7")
        self.status_label.config(text="✨ ニュースを検索中...", fg=self.PRIMARY_COLOR)
        
        threading.Thread(target=self.run_bot_logic, daemon=True).start()

    def run_bot_logic(self):
        keyword = self.keyword_entry.get().strip()
        count = int(self.count_spin.get())

        self.write_log(f"キーワード「{keyword}」で検索を開始します", is_title=True)
        
        rss_url = self.get_google_news_url(keyword)
        feed = feedparser.parse(rss_url)
        
        entries = feed.entries[:3] # 上位3件
        self.write_log(f"{len(feed.entries)}件の記事が見つかりました。最新の3件を処理します。")

        for entry in entries:
            title = entry.title
            link = entry.link
            self.write_log(f"処理中: {title}")
            
            body_text = self.get_article_content(link)
            
            if len(body_text) > 50:
                summary_lines = self.summarize_text(body_text, count)
            else:
                summary_lines = ["（記事本文の抽出が難しいサイトです）"]
            
            # プレビュー表示
            for line in summary_lines:
                self.write_log(f" > {line}")

            # Discord送信
            success = self.send_discord(title, summary_lines, link, keyword)
            if success:
                self.write_log("✅ Discordへの送信が完了しました。")
            else:
                self.write_log("❌ 送信に失敗しました。")
            
            time.sleep(1) # 負荷軽減

        self.write_log("すべての処理が完了しました。", is_title=True)
        self.root.after(0, self.finish_bot)

    def finish_bot(self):
        self.is_running = False
        self.run_btn.config(state=tk.NORMAL, text="ボットを稼働 🚀", bg=self.PRIMARY_COLOR)
        self.status_label.config(text="✅ 完了", fg=self.SUCCESS_COLOR)
        messagebox.showinfo("完了", "最新ニュースの要約と送信が完了しました！")

if __name__ == "__main__":
    root = tk.Tk()
    # Windows高解像度対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = NewsBotApp(root)
    root.mainloop()