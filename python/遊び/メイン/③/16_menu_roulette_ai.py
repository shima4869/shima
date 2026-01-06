# AI今日の献立ルーレット ✨
# インストール: pip install tkinter requests pillow
# 実行方法: python 16_menu_roulette_ai.py
# Select Interpreter: Python 3.11.9

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import requests
import json
import threading
import time
import random
import re
from PIL import Image, ImageTk

class MenuAI:
    """Gemini APIを使用して最適な献立を1つだけ決定するエンジン"""
    def __init__(self):
        # 以前提供されたAPIキーを設定
        self.api_key = "AIzaSyBzOeROpVGYEC1miK2ukPVeOdE0vEChv8Y" 
        self.model_id = "gemini-2.5-flash-preview-09-2025"

    def get_pinpoint_menu(self, ingredients, mood, weather, yesterday):
        """全ての要素を考慮して究極の1品を提案する"""
        prompt = (
            "あなたはプロの献立プランナーです。以下の条件をすべて考慮し、今日の夕飯に最適なメニューを「1つだけ」決定してください。\n\n"
            f"【冷蔵庫の食材】: {ingredients}\n"
            f"【今の気分】: {mood}\n"
            f"【天気】: {weather}\n"
            f"【昨日の夕飯】: {yesterday}\n\n"
            "昨日のメニューとはジャンルが被らないようにし、天気や気分に合わせた温度感や栄養バランスの料理を提案してください。"
            "回答は以下の厳密なJSON形式のみで返してください。説明文は不要です。\n\n"
            "{\n"
            '  "menu_name": "料理名",\n'
            '  "reason": "このメニューを選んだ理由（気分や天気を踏まえて）",\n'
            '  "ingredients_needed": ["追加で必要な材料1", "材料2"],\n'
            '  "recipe_tips": "美味しく作るためのワンポイントアドバイス"\n'
            "}"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}

        # 指数バックオフによるリトライ処理
        for i in range(3):
            try:
                response = requests.post(url, json=payload, timeout=30)
                if response.status_code == 200:
                    res_text = response.json()['candidates'][0]['content']['parts'][0]['text']
                    return json.loads(res_text), None
                if response.status_code == 429:
                    time.sleep(2 ** i)
                    continue
                return None, f"APIエラー: {response.status_code}"
            except Exception as e:
                if i == 2: return None, str(e)
        return None, "通信に失敗しました。"

class MenuRouletteApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI今日の献立ルーレット ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.ACCENT_GREEN = "#2ECC71"

        self.ai = MenuAI()
        self.is_spinning = False
        
        self.setup_ui()

    def setup_ui(self):
        # メインタイトル
        header = tk.Frame(self.root, bg="#FFFBEB")
        header.pack(pady=20)
        tk.Label(header, text="🍳 AI今日の献立ルーレット", 
                 font=("Meiryo", 28, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR).pack()

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=40, pady=5)
        
        self.main_container.columnconfigure(0, weight=1) # 入力
        self.main_container.columnconfigure(1, weight=2) # 結果
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：条件入力パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=400)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        # 各入力項目
        fields = [
            ("🥩 冷蔵庫の主な食材", "fridge"),
            ("🌈 今の気分（ガッツリ、さっぱり等）", "mood"),
            ("☀️ 今日の天気", "weather"),
            ("🍱 昨日の夕飯", "yesterday")
        ]
        
        self.entries = {}
        for label_text, key in fields:
            frame = tk.LabelFrame(self.left_panel, text=f" {label_text} ", 
                                 font=("Meiryo", 9, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
            frame.pack(fill=tk.X, pady=8)
            
            if key == "weather":
                entry = ttk.Combobox(frame, values=["晴れ", "曇り", "雨", "雪", "暑い", "寒い"], font=("Meiryo", 10))
                entry.set("晴れ")
            else:
                entry = tk.Entry(frame, font=("Meiryo", 11), relief=tk.FLAT)
                if key == "fridge": entry.insert(0, "鶏肉、玉ねぎ、卵")
                if key == "mood": entry.insert(0, "温かいものが食べたい")
                if key == "yesterday": entry.insert(0, "カレーライス")
            
            entry.pack(fill=tk.X, padx=10, pady=10)
            self.entries[key] = entry

        # ルーレット開始ボタン
        self.spin_btn = tk.Button(self.left_panel, text="献立を決定する！ 🎰", 
                                 command=self.start_roulette,
                                 bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 14, "bold"),
                                 relief=tk.FLAT, cursor="hand2", pady=20)
        self.spin_btn.pack(fill=tk.X, pady=20)

        # ステータス
        self.status_label = tk.Label(self.left_panel, text="条件を入力してね", 
                                    bg="#FFFBEB", fg="#95A5A6", font=("Meiryo", 9))
        self.status_label.pack()

        # --- 右側：結果・ルーレット表示パネル ---
        self.right_panel = tk.Frame(self.main_container, bg=self.BG_WHITE, relief=tk.RIDGE, bd=2)
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        # ルーレット演出用ラベル
        self.display_area = tk.Frame(self.right_panel, bg=self.BG_WHITE)
        self.display_area.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)

        self.lbl_main_result = tk.Label(self.display_area, text="READY", 
                                       font=("Meiryo", 42, "bold"), bg=self.BG_WHITE, fg="#DDD")
        self.lbl_main_result.pack(expand=True)

        self.result_info = scrolledtext.ScrolledText(self.display_area, font=("Meiryo", 12), 
                                                    bg="#F9F9F9", relief=tk.FLAT, height=12,
                                                    padx=20, pady=20, state=tk.DISABLED)
        self.result_info.pack(fill=tk.X, pady=20)

    def start_roulette(self):
        if self.is_spinning: return
        
        # 入力チェック
        data = {k: e.get().strip() for k, e in self.entries.items()}
        if not data["fridge"]:
            messagebox.showwarning("入力不足", "冷蔵庫の食材を教えてください。")
            return

        self.is_spinning = True
        self.spin_btn.config(state=tk.DISABLED, text="ルーレット回転中...")
        self.lbl_main_result.config(fg=self.PRIMARY_COLOR)
        
        # ログの初期化
        self.result_info.config(state=tk.NORMAL)
        self.result_info.delete("1.0", tk.END)
        self.result_info.config(state=tk.DISABLED)

        # アニメーションとAI処理を別スレッドで開始
        threading.Thread(target=self.run_logic, args=(data,), daemon=True).start()

    def run_logic(self, data):
        # 1. ルーレット演出 (ダミーの料理名を流す)
        dummy_menus = ["ハンバーグ", "肉じゃが", "パスタ", "オムライス", "焼き魚", "唐揚げ", "グラタン", "冷やし中華", "うどん"]
        for _ in range(15):
            menu = random.choice(dummy_menus)
            self.root.after(0, lambda m=menu: self.lbl_main_result.config(text=m))
            time.sleep(0.1)

        # 2. AIによる本物の献立生成
        self.root.after(0, lambda: self.status_label.config(text="✨ AIが究極の1品を選定しています...", fg=self.PRIMARY_COLOR))
        result, err = self.ai.get_pinpoint_menu(data["fridge"], data["mood"], data["weather"], data["yesterday"])
        
        if err:
            self.root.after(0, lambda: self.handle_error(err))
            return

        # 3. 結果発表演出
        for _ in range(10):
            menu = random.choice(dummy_menus)
            self.root.after(0, lambda m=menu: self.lbl_main_result.config(text=m))
            time.sleep(0.05 + (_ * 0.05)) # 徐々に遅く

        self.root.after(0, lambda: self.show_final_result(result))

    def show_final_result(self, result):
        self.is_spinning = False
        self.spin_btn.config(state=tk.NORMAL, text="献立を決定する！ 🎰")
        self.status_label.config(text="✅ 本日のメニューが決定しました！", fg=self.ACCENT_GREEN)
        
        # メイン表示
        self.lbl_main_result.config(text=result["menu_name"], fg=self.PRIMARY_COLOR)
        
        # 詳細表示
        self.result_info.config(state=tk.NORMAL)
        needed = "、".join(result.get("ingredients_needed", []))
        report = (
            f"【選ばれた理由】\n{result.get('reason')}\n\n"
            f"【買い足しが必要なもの】\n{needed if needed else 'なし'}\n\n"
            f"【プロのコツ】\n{result.get('recipe_tips')}"
        )
        self.result_info.insert(tk.END, report)
        self.result_info.config(state=tk.DISABLED)

    def handle_error(self, msg):
        self.is_spinning = False
        self.spin_btn.config(state=tk.NORMAL, text="献立を決定する！ 🎰")
        messagebox.showerror("エラー", f"献立の生成に失敗しました:\n{msg}")

if __name__ == "__main__":
    root = tk.Tk()
    # Windows高DPI対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = MenuRouletteApp(root)
    root.mainloop()