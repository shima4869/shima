# AI競合サイト監視ツール ✨
# インストール: pip install tkinter requests pillow selenium beautifulsoup4 webdriver-manager
# 実行方法: python 10_web_monitor_ai.py
# Select Interpreter: Python 3.11.9

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import requests
import json
import threading
import time
import os
import base64
import datetime
from PIL import Image, ImageTk
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# --- 設定項目 ---
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1444232363637997659/c9oDNYEjj1dqTTGHaVzs4zCQMiH0ulc7hDAONZVHgH-rv_mB9ImpAKZLAF-NhJWe9i5x"

class WebMonitorAI:
    """Webサイトの監視とAIによる差分解析を行うエンジン"""
    def __init__(self):
        self.api_key = "AIzaSyBzOeROpVGYEC1miK2ukPVeOdE0vEChv8Y" # 実行環境から自動供給
        self.model_id = "gemini-2.5-flash-preview-09-2025"
        self.last_content = ""
        
        # Seleniumの設定 (Headlessモード)
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--window-size=1280,1024")

    def fetch_page(self, url):
        """ブラウザを使用してページをレンダリングし、テキストとスクショを取得"""
        driver = None
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.chrome_options)
            driver.get(url)
            time.sleep(3) # レンダリング待機
            
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")
            # 不要なスクリプト等を除去してテキスト抽出
            for s in soup(['script', 'style']): s.decompose()
            text_content = soup.get_text(separator=' ', strip=True)
            
            # スクリーンショット撮影
            screenshot_path = "latest_capture.png"
            driver.save_screenshot(screenshot_path)
            
            return text_content, screenshot_path, None
        except Exception as e:
            return None, None, str(e)
        finally:
            if driver: driver.quit()

    def analyze_changes(self, old_text, new_text):
        """Gemini AIを使用して、変更点に意味があるか（価格変更等）を判断"""
        if not old_text: return "初回監視のため、現在の状態を記録しました。", True
        
        prompt = (
            "以下の2つのテキストは、同じWebサイトの「前回」と「今回」の取得内容です。\n"
            "価格の変更、新商品の追加、在庫状況の変化など、ビジネス的に重要な変更があるか分析してください。\n\n"
            f"--- 前回の内容 (抜粋) ---\n{old_text[:2000]}\n\n"
            f"--- 今回の内容 (抜粋) ---\n{new_text[:2000]}\n\n"
            "重要な変更がある場合は、その内容を簡潔にまとめてください。特に変更がない場合は「変更なし」とだけ答えてください。"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        try:
            res = requests.post(url, json=payload, timeout=30)
            if res.status_code == 200:
                summary = res.json()['candidates'][0]['content']['parts'][0]['text']
                has_change = "変更なし" not in summary
                return summary, has_change
            return "AI解析に失敗しました。", True
        except:
            return "解析中にエラーが発生しました。", True

    def send_discord(self, message, screenshot_path):
        """Discordにメッセージと画像を送信"""
        try:
            with open(screenshot_path, "rb") as f:
                payload = {"content": f"🚨 **競合サイトに更新がありました！**\n\n{message}"}
                files = {"file": ("screenshot.png", f)}
                requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files, timeout=20)
            return True
        except:
            return False

class MonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI競合サイト監視ツール ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SUCCESS_COLOR = "#2ECC71"

        self.ai = WebMonitorAI()
        self.is_monitoring = False
        self.monitor_thread = None
        
        self.setup_ui()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="📡 AI競合サイト監視システム", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        self.main_container.columnconfigure(0, weight=1) # 操作
        self.main_container.columnconfigure(1, weight=3) # ログ
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：設定パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        config_frame = tk.LabelFrame(self.left_panel, text=" ⚙️ 監視ターゲット設定 ", 
                                    font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        config_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(config_frame, text="ターゲットURL:", bg=self.BG_WHITE, font=("Meiryo", 9)).pack(anchor="w", padx=15, pady=(15, 0))
        self.url_entry = tk.Entry(config_frame, font=("Consolas", 10), relief=tk.SOLID, bd=1)
        self.url_entry.pack(fill=tk.X, padx=15, pady=10)
        self.url_entry.insert(0, "https://www.apple.com/jp/shop/back-to-school")

        tk.Label(config_frame, text="チェック間隔 (分):", bg=self.BG_WHITE, font=("Meiryo", 9)).pack(anchor="w", padx=15, pady=(5, 0))
        self.interval_spin = tk.Spinbox(config_frame, from_=5, to=1440, font=("Meiryo", 10))
        self.interval_spin.pack(fill=tk.X, padx=15, pady=10)

        self.run_btn = tk.Button(self.left_panel, text="監視を開始する 🚀", 
                                command=self.toggle_monitoring,
                                bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                relief=tk.FLAT, cursor="hand2", pady=15)
        self.run_btn.pack(fill=tk.X, pady=10)

        self.status_label = tk.Label(self.left_panel, text="状態: 停止中", bg="#FFFBEB", 
                                    font=("Meiryo", 10, "bold"), fg=self.TEXT_COLOR)
        self.status_label.pack(pady=10)

        guide_text = "【ヒント】\n・AIが「重要な変化」のみを抽出して通知します。\n・デザインの微細な変更などは無視されます。\n・Discordには要約とスクショが届きます。"
        tk.Label(self.left_panel, text=guide_text, bg="#FFFBEB", justify=tk.LEFT, 
                 font=("Meiryo", 9), fg="#95A5A6").pack(side=tk.BOTTOM, pady=20)

        # --- 右側：ログ表示パネル ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        log_frame = tk.LabelFrame(self.right_panel, text=" 📜 監視アクティビティ・ログ ", 
                                 font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_area = scrolledtext.ScrolledText(log_frame, font=("Meiryo", 10), 
                                                 bg=self.BG_WHITE, relief=tk.FLAT,
                                                 fg=self.TEXT_COLOR, padx=15, pady=15)
        self.log_area.pack(fill=tk.BOTH, expand=True)
        self.write_log("システム準備完了。URLを入力して開始してください。")

    def write_log(self, message):
        timestamp = datetime.datetime.now().strftime("[%H:%M:%S] ")
        self.log_area.insert(tk.END, timestamp + message + "\n")
        self.log_area.see(tk.END)

    def toggle_monitoring(self):
        if not self.is_monitoring:
            url = self.url_entry.get().strip()
            if not url.startswith("http"):
                messagebox.showwarning("URLエラー", "正しいURLを入力してください。")
                return
            
            self.is_monitoring = True
            self.run_btn.config(text="監視を停止する ⏹", bg="#E74C3C")
            self.status_label.config(text="状態: 巡回中...", fg=self.PRIMARY_COLOR)
            self.write_log(f"監視を開始しました: {url}")
            
            self.monitor_thread = threading.Thread(target=self.monitor_loop, args=(url,), daemon=True)
            self.monitor_thread.start()
        else:
            self.is_monitoring = False
            self.run_btn.config(text="監視を開始する 🚀", bg=self.PRIMARY_COLOR)
            self.status_label.config(text="状態: 停止中", fg=self.TEXT_COLOR)
            self.write_log("監視を停止しました。")

    def monitor_loop(self, url):
        while self.is_monitoring:
            self.write_log(f"サイトを確認しています...")
            
            # 1. ページ取得
            new_text, screenshot_path, error = self.ai.fetch_page(url)
            
            if error:
                self.write_log(f"取得エラー: {error}")
            else:
                # 2. AIによる差分解析
                summary, has_change = self.ai.analyze_changes(self.ai.last_content, new_text)
                
                if has_change:
                    self.write_log(f"重要変更を検知！: {summary[:50]}...")
                    # 3. Discord通知
                    if self.ai.send_discord(summary, screenshot_path):
                        self.write_log("Discordへの通知を送信しました。")
                    else:
                        self.write_log("Discord通知に失敗しました。Webhookを確認してください。")
                else:
                    self.write_log("重要な変更は見つかりませんでした。")
                
                self.ai.last_content = new_text

            # 次の巡回まで待機
            try:
                interval = int(self.interval_spin.get()) * 60
            except:
                interval = 300
                
            self.write_log(f"次の確認まで待機します ({interval // 60}分後)")
            
            # 停止ボタンが押された場合にすぐ反応できるよう細かくスリープ
            for _ in range(interval):
                if not self.is_monitoring: break
                time.sleep(1)

    def on_closing(self):
        self.is_monitoring = False
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    # Windows高DPI対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = MonitorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()