# AI映画・音楽レコメンドシステム (ローカル版)
# インストール: pip install tkinter pillow
# 実行方法: python 15_movie_recommender.py
# Select Interpreter: Python 3.11.9

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import threading
import time
import os
import difflib

class LocalRecommenderEngine:
    """ローカルデータベースを使用してレコメンドを行うクラス"""
    def __init__(self):
        # --- 映画データベース ---
        self.movie_db = {
            "インセプション": {"genre": ["SF", "アクション", "難解"], "desc": "夢の中に入る階層構造の設定が近く、映像美が素晴らしい作品です。"},
            "インターステラー": {"genre": ["SF", "宇宙", "感動"], "desc": "相対性理論を軸にした重厚な人間ドラマと宇宙の映像美が共通しています。"},
            "ダークナイト": {"genre": ["アクション", "DC", "シリアス"], "desc": "クリストファー・ノーラン監督特有の緊張感とリアルな描写が楽しめます。"},
            "マトリックス": {"genre": ["SF", "アクション", "哲学"], "desc": "「世界の真実を知る」というテーマやスタイリッシュな戦闘シーンが魅力です。"},
            "君の名は。": {"genre": ["アニメ", "恋愛", "SF"], "desc": "運命的な出会いと美しい背景描写、音楽との融合が素晴らしい作品です。"},
            "千と千尋の神隠し": {"genre": ["アニメ", "ファンタジー", "冒険"], "desc": "独自の世界観と成長物語、圧倒的な作画クオリティが共通しています。"},
            "タイタニック": {"genre": ["恋愛", "感動", "歴史"], "desc": "壮大なスケールで描かれる悲恋と、映像の迫力が共通しています。"},
            "アベンジャーズ": {"genre": ["アクション", "ヒーロー", "お祭り"], "desc": "多数のキャラクターが共闘する高揚感と迫力のバトルが楽しめます。"},
            "ショーシャンクの空に": {"genre": ["ドラマ", "希望", "名作"], "desc": "人間の尊厳と希望を描いた感動の物語として、高い評価を得ている名作です。"},
            "パルプ・フィクション": {"genre": ["犯罪", "スタイリッシュ", "群像劇"], "desc": "時系列が入り混じる構成と、独特な会話劇のセンスが光る作品です。"}
        }

        # --- 音楽データベース ---
        self.music_db = {
            "Official髭男dism": {"genre": ["J-POP", "キャッチー", "ピアノ"], "desc": "美しいメロディとハイトーンボイス、洗練されたサウンドが共通しています。"},
            "King Gnu": {"genre": ["ロック", "オルタナティブ", "ミクスチャー"], "desc": "高度な演奏技術と、和洋折衷な独特の音楽センスが刺激的なグループです。"},
            "米津玄師": {"genre": ["J-POP", "アーティスティック", "ボカロ出身"], "desc": "独特なリズム感と情緒的な歌詞の世界観が、多くのファンを魅了しています。"},
            "YOASOBI": {"genre": ["J-POP", "物語", "キャッチー"], "desc": "小説を音楽にするというコンセプトと、耳に残るデジタルサウンドが特徴です。"},
            "Queen": {"genre": ["ロック", "オペラ", "伝説"], "desc": "壮大なコーラスとドラマチックな楽曲構成が、世代を超えて愛されています。"},
            "The Beatles": {"genre": ["ロック", "ポップ", "古典"], "desc": "現代音楽の礎を築いた美しいメロディと、革新的な楽曲制作が魅力です。"},
            "宇多田ヒカル": {"genre": ["R&B", "J-POP", "実力派"], "desc": "圧倒的な歌唱力と、時代を先取りするサウンドメイクが共通の魅力です。"},
            "Vaundy": {"genre": ["マルチ", "モダン", "クリエイティブ"], "desc": "ジャンルに縛られない自由な発想と、現代的なグルーヴ感が楽しめるアーティストです。"}
        }

    def get_recommendations(self, title, category_name):
        """入力された作品から類似したものを探す"""
        db = self.movie_db if "映画" in category_name else self.music_db
        
        # 1. 直接一致または近似一致を探す
        matches = difflib.get_close_matches(title, db.keys(), n=1, cutoff=0.3)
        
        if not matches:
            return None, f"データベースに「{title}」の情報がありませんでした。別の作品名（例：インセプション、米津玄師など）を試してみてください。"

        base_title = matches[0]
        base_info = db[base_title]
        recommendations = []

        # 2. ジャンルの重なりでスコアリング
        for target_title, target_info in db.items():
            if target_title == base_title:
                continue
            
            # 共通ジャンルの数を計算
            common = set(base_info["genre"]) & set(target_info["genre"])
            if common:
                recommendations.append({
                    "title": target_title,
                    "reason": f"{', '.join(common)}という要素が「{base_title}」と共通しています。{target_info['desc']}",
                    "score": len(common)
                })

        # スコア順にソートして上位3つを返す
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations[:3], None

class RecommendationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI映画・音楽レコメンドシステム ✨")
        self.root.geometry("1400x900")
        self.root.configure(bg="#FFFBEB")

        # カラー定数
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.ACCENT_BLUE = "#3498DB"
        self.SUCCESS_COLOR = "#2ECC71"

        self.engine = LocalRecommenderEngine()
        self.is_loading = False
        
        self.setup_ui()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🎬 映画・音楽レコメンド (Offline Edition)", 
                              font=("Meiryo", 24, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(20, 10))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=3)
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：操作パネル ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB", width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_panel.pack_propagate(False)

        input_frame = tk.LabelFrame(self.left_panel, text=" 🔍 作品を入力 ", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        input_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(input_frame, text="作品名・アーティスト名:", bg=self.BG_WHITE, font=("Meiryo", 9)).pack(anchor="w", padx=15, pady=(15, 0))
        self.title_entry = tk.Entry(input_frame, font=("Meiryo", 12), relief=tk.SOLID, bd=1)
        self.title_entry.pack(fill=tk.X, padx=15, pady=10)

        tk.Label(input_frame, text="カテゴリー:", bg=self.BG_WHITE, font=("Meiryo", 9)).pack(anchor="w", padx=15, pady=(5, 0))
        self.cat_combo = ttk.Combobox(input_frame, values=["映画 (Movie)", "音楽 (Music)"], state="readonly", font=("Meiryo", 10))
        self.cat_combo.set("映画 (Movie)")
        self.cat_combo.pack(fill=tk.X, padx=15, pady=(5, 20))

        self.run_btn = tk.Button(self.left_panel, text="おすすめを探す 🚀", 
                                command=self.start_recommendation,
                                bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 12, "bold"),
                                relief=tk.FLAT, cursor="hand2", pady=18)
        self.run_btn.pack(fill=tk.X, pady=15)

        # ステータス
        self.status_label = tk.Label(self.left_panel, text="準備完了", bg="#FFFBEB", 
                                    font=("Meiryo", 10, "bold"), fg=self.TEXT_COLOR)
        self.status_label.pack(pady=10)

        guide_text = "【ヒント】\n・有名な作品名を入力してください。\n・APIを使わないため、通信エラーの\n　心配なく一瞬で結果が出ます。"
        tk.Label(self.left_panel, text=guide_text, bg="#FFFBEB", justify=tk.LEFT, 
                 font=("Meiryo", 9), fg="#95A5A6").pack(side=tk.BOTTOM, pady=20)

        # --- 右側：結果表示エリア ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew")

        res_frame = tk.LabelFrame(self.right_panel, text=" 📜 レコメンド・レポート ", 
                                 font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                 fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        res_frame.pack(fill=tk.BOTH, expand=True)

        self.result_area = scrolledtext.ScrolledText(res_frame, font=("Meiryo", 11), 
                                                    bg=self.BG_WHITE, relief=tk.FLAT,
                                                    fg=self.TEXT_COLOR, state=tk.DISABLED,
                                                    padx=25, pady=25)
        self.result_area.pack(fill=tk.BOTH, expand=True)

    def write_log(self, message, is_header=False, is_title=False):
        self.result_area.config(state=tk.NORMAL)
        if is_header:
            self.result_area.insert(tk.END, f"✨ {message} ✨\n", "header")
            self.result_area.tag_config("header", foreground=self.PRIMARY_COLOR, font=("Meiryo", 16, "bold"))
            self.result_area.insert(tk.END, "="*60 + "\n")
        elif is_title:
            self.result_area.insert(tk.END, f"\n📌 {message}\n", "title")
            self.result_area.tag_config("title", foreground=self.ACCENT_BLUE, font=("Meiryo", 12, "bold"))
        else:
            self.result_area.insert(tk.END, message + "\n")
        
        self.result_area.see(tk.END)
        self.result_area.config(state=tk.DISABLED)

    def start_recommendation(self):
        target = self.title_entry.get().strip()
        category = self.cat_combo.get()
        if not target:
            messagebox.showwarning("入力不足", "作品名を入力してください。")
            return
        
        self.result_area.config(state=tk.NORMAL)
        self.result_area.delete("1.0", tk.END)
        self.result_area.config(state=tk.DISABLED)
        
        results, error = self.engine.get_recommendations(target, category)
        
        if error:
            self.write_log(error)
            return

        self.write_log(f"「{target}」がお好きな方へのおすすめ", is_header=True)
        
        if results:
            for i, item in enumerate(results, 1):
                self.write_log(f"候補 {i}: {item['title']}", is_title=True)
                self.write_log(f"💡 おすすめの理由:\n   {item['reason']}")
                self.write_log("-" * 45)
        else:
            self.write_log("関連する作品がデータベースに見つかりませんでした。別のキーワードでお試しください。")

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = RecommendationApp(root)
    root.mainloop()