# AI歴史人物チャット (オフライン版) ✨
# インストール: pip install tkinter
# 実行方法: python 14_historical_chat_ai.py
# Select Interpreter: Python 3.11.9

import tkinter as tk
from tkinter import scrolledtext, ttk
import time
import os
import sys
import random

class HistoricalLocalAI:
    """外部通信を一切行わないローカル応答エンジン"""
    def __init__(self):
        self.db = {
            "織田信長": {
                "default": ["うむ、何用だ？", "余の天下布武の邪魔はさせぬぞ。", "貴様、見どころがあるな。", "是非もなし。", "敦盛を舞うか。"],
                "keywords": {
                    "天下": "天下は余が手中に収める。それが乱世を終わらせる唯一の道よ。",
                    "現代": "ほう、現代とはそんなに便利なものか。鉄砲よりも凄まじいな。",
                    "明智": "光秀か...奴は真面目が過ぎるのが玉に瑕よ。",
                    "本能寺": "何だその不吉な名は？ 余を脅そうというのか？",
                    "好き": "余を好くか。面白い。ならば余の覇道について参れ。",
                    "平和": "戦を終わらせ、新しい世を創る。それが余の願いである。"
                },
                "hints": "天下, 明智, 現代, 本能寺, 好き, 平和"
            },
            "坂本龍馬": {
                "default": ["おんし、どっから来たんじゃ？", "日本の夜明けは近いぜよ！", "まっこと面白い男じゃのう。", "海は広い。世界はもっと広いぜよ。", "まあ一杯やりましょう。"],
                "keywords": {
                    "日本": "日本を今一度、洗濯しなきゃいかん。そう思わんかえ？",
                    "洗濯": "日本を洗濯する。汚れた古い考えを洗い流すんじゃ！",
                    "船": "海援隊のいろは丸は最高ぜよ。これからは船の時代じゃきに。",
                    "現代": "スマホというのかえ？ まっこと魔法のような道具じゃのう！",
                    "平和": "喧嘩は損ぜよ。みんなで手を組んで新しい国を作ろうや。",
                    "土佐": "土佐の海が恋しいのう。おんしにも見せてやりたいぜよ。"
                },
                "hints": "日本, 洗濯, 船, 現代, 平和, 土佐"
            },
            "卑弥呼": {
                "default": ["鏡に影が映っております...", "天の啓示が降りてまいりました。", "鬼道の力を侮ってはなりませぬ。", "邪馬台国の安寧を祈りましょう。", "運命はすでに決まっているのです。"],
                "keywords": {
                    "未来": "未来の輝きが眩しすぎます... 鏡が曇って見えませぬ。",
                    "魏": "魏の皇帝から頂いた金印は、我が国の誇りです。",
                    "祈り": "わたくしの祈りが届く限り、この国は守られるでしょう。",
                    "卑弥呼": "わたくしの名を呼ぶのは誰ですか？ 声が遠くに聞こえます。",
                    "天気": "明日は恵みの雨が降るでしょう。天がそう告げております。",
                    "怖い": "恐れることはありません。すべては大きな流れの一部なのです。"
                },
                "hints": "未来, 祈り, 魏, 卑弥呼, 天気, 怖い"
            }
        }

    def get_response(self, char_name, user_text):
        char_data = self.db.get(char_name)
        for key, reply in char_data["keywords"].items():
            if key in user_text:
                return reply
        return random.choice(char_data["default"])

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("歴史人物チャット (Offline Edition) ✨")
        self.root.geometry("1000x800")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"
        self.SECONDARY_COLOR = "#FFCC33"
        self.LINE_BG = "#7494C0"
        self.USER_BUBBLE = "#95E17A"

        self.ai = HistoricalLocalAI()
        self.current_char = "織田信長"
        
        self.setup_ui()
        self.setup_tags()
        self.change_person()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        # フォント設定
        f_main = ("Meiryo", 20, "bold") if os.name == 'nt' else ("Helvetica", 20, "bold")
        f_chat = ("Meiryo", 11) if os.name == 'nt' else ("Helvetica", 11)

        header = tk.Label(self.root, text="🕰️ 歴史人物タイムトラベル・チャット", 
                          font=f_main, bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        header.pack(pady=(15, 5))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=250)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        self.left_panel.pack_propagate(False)

        # 人物選択
        select_frame = tk.LabelFrame(self.left_panel, text=" 👤 人物選択 ", 
                                    font=f_chat, bg="white", fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        select_frame.pack(fill=tk.X, pady=5)

        self.char_var = tk.StringVar(value="織田信長")
        for name in ["織田信長", "坂本龍馬", "卑弥呼"]:
            tk.Radiobutton(select_frame, text=name, variable=self.char_var, value=name,
                          font=f_chat, bg="white", command=self.change_person,
                          indicatoron=0, selectcolor=self.SECONDARY_COLOR, 
                          activebackground=self.SECONDARY_COLOR, pady=10).pack(fill=tk.X, padx=10, pady=5)

        # ヒントパネル (修正箇所: LabelからLabelFrameへ変更し配置を固定)
        self.guide_frame = tk.LabelFrame(self.left_panel, text=" 💡 キーワードのヒント ", 
                                   font=f_chat, bg="white", fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        self.guide_frame.pack(fill=tk.X, pady=10)
        
        self.hint_label = tk.Label(self.guide_frame, text="", bg="white", font=f_chat, 
                                   wraplength=200, justify=tk.LEFT, fg="#4B4B4B", padx=10, pady=10)
        self.hint_label.pack(fill=tk.X)

        # --- 右側：チャット画面 ---
        self.right_panel = tk.Frame(self.main_container, bg=self.LINE_BG, bd=4, relief=tk.RIDGE)
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        # チャットログ表示
        self.chat_display = scrolledtext.ScrolledText(self.right_panel, font=f_chat, 
                                                      bg=self.LINE_BG, relief=tk.FLAT, state=tk.DISABLED,
                                                      padx=10, pady=10)
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # 入力バー
        input_bar = tk.Frame(self.right_panel, bg="white", pady=15, padx=15)
        input_bar.pack(fill=tk.X)

        self.entry_msg = tk.Entry(input_bar, font=f_chat, relief=tk.SOLID, bd=1)
        self.entry_msg.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.entry_msg.bind("<Return>", lambda e: self.send_message())

        btn_send = tk.Button(input_bar, text="送信", command=self.send_message, bg=self.PRIMARY_COLOR, 
                            fg="white", font=("Meiryo", 10, "bold"), relief=tk.FLAT, width=10, cursor="hand2")
        btn_send.pack(side=tk.RIGHT)

    def setup_tags(self):
        """チャットの見た目を整えるためのタグ設定"""
        self.chat_display.tag_config("u_h", foreground="white", justify=tk.RIGHT, font=("Meiryo", 9))
        self.chat_display.tag_config("u_m", background=self.USER_BUBBLE, justify=tk.RIGHT, spacing1=5, spacing3=5, lmargin1=100)
        self.chat_display.tag_config("a_h", foreground="white", justify=tk.LEFT, font=("Meiryo", 9))
        self.chat_display.tag_config("a_m", background="white", justify=tk.LEFT, spacing1=5, spacing3=5, rmargin=100)
        self.chat_display.tag_config("sys", foreground="#F1C40F", justify=tk.CENTER, font=("Meiryo", 10, "bold"))

    def change_person(self):
        self.current_char = self.char_var.get()
        char_data = self.ai.db.get(self.current_char)
        self.hint_label.config(text=char_data["hints"])
        self.append_message("System", f"--- {self.current_char} が現れました ---")

    def send_message(self):
        text = self.entry_msg.get().strip()
        if not text: return
        self.entry_msg.delete(0, tk.END)
        self.append_message("あなた", text)
        
        # AIの返答 (少しディレイを入れる)
        self.root.after(400, lambda: self.append_message(self.current_char, self.ai.get_response(self.current_char, text)))

    def append_message(self, sender, text):
        self.chat_display.config(state=tk.NORMAL)
        ts = time.strftime("%H:%M")
        
        if sender == "あなた":
            self.chat_display.insert(tk.END, f"\n[あなた] {ts}\n", "u_h")
            self.chat_display.insert(tk.END, f" {text} \n", "u_m")
        elif sender == "System":
            self.chat_display.insert(tk.END, f"\n{text}\n", "sys")
        else:
            self.chat_display.insert(tk.END, f"\n[{sender}] {ts}\n", "a_h")
            self.chat_display.insert(tk.END, f" {text} \n", "a_m")
        
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def on_closing(self):
        """VS Codeやターミナルでのゾンビプロセス防止"""
        try:
            self.root.destroy()
        except:
            pass
        sys.exit(0)

if __name__ == "__main__":
    # システム起動時のログ
    print("AI Historical Chat System Starting...")
    
    root = tk.Tk()
    # Windows高DPI対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = ChatApp(root)
    root.mainloop()