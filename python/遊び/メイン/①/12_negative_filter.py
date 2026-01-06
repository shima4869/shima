# AIネガティブ・フィルター
# インストール: pip install janome pillow numpy
# 実行方法: python 12_negative_filter.py
# Select Interpreter: Python 3.11.9

import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from janome.tokenizer import Tokenizer
from PIL import Image, ImageTk
import time
import os

# --- AIエンジン (既存のシステムを完全に継承) ---
class NegativeFilterAI:
    def __init__(self):
        # 日本語解析エンジンの準備
        self.tokenizer = Tokenizer()

        # ネガティブ辞書
        self.negative_dict = {
            'バカ': -3, '阿呆': -3, 'アホ': -3,
            '死ね': -5, '殺す': -5, '消えろ': -4,
            'うざい': -2, 'キモい': -3, 'きもい': -3,
            '最悪': -2, 'ゴミ': -3, 'クズ': -4,
            '下手': -1, '嫌い': -2, 'ダメ': -1,
            'ブス': -4, 'デブ': -3, '老害': -3,
            '辞めろ': -2, '馬鹿': -3
        }

    def analyze(self, text):
        """文章を分析して、フィルタリング結果とスコアを返す"""
        if not text:
            return "", 0, []

        tokens = self.tokenizer.tokenize(text)
        filtered_text = ""
        total_score = 0
        detected_words = []

        for token in tokens:
            word = token.surface
            base_form = token.base_form
            
            score = 0
            if word in self.negative_dict:
                score = self.negative_dict[word]
            elif base_form in self.negative_dict:
                score = self.negative_dict[base_form]
            
            if score < 0:
                total_score += score
                detected_words.append(word)
                filtered_text += "*" * len(word)
            else:
                filtered_text += word

        return filtered_text, total_score, detected_words

class FilterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIネガティブ・フィルター ✨")
        
        # ウィンドウサイズ（コンパクト：700x500）
        self.root.geometry("700x500")
        self.root.configure(bg="#FFFBEB")

        # カラー定数 (シリーズ共通)
        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"        # 緑
        self.ALERT_COLOR = "#E74C3C"       # 赤

        # AIの初期化
        self.ai = NegativeFilterAI()
        
        self.setup_ui()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🛡️ AIネガティブ・フィルター", 
                              font=("Meiryo", 16, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(15, 5))

        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 【重要】比率調整：左(入力)1, 右(結果)1 の 5:5 構成
        self.main_container.columnconfigure(0, weight=1, uniform="group1")
        self.main_container.columnconfigure(1, weight=1, uniform="group1")
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：ステップ1（入力パネル） ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # 実行ボタンを下側に配置（確実に表示）
        self.run_btn = tk.Button(self.left_panel, text="AI検閲を実行 🔍", 
                                command=self.process_filter,
                                bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 11, "bold"),
                                relief=tk.FLAT, cursor="hand2", pady=8)
        self.run_btn.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        input_frame = tk.LabelFrame(self.left_panel, text=" 📖 STEP 1: 入力 ", 
                                   font=("Meiryo", 9, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        input_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.input_area = scrolledtext.ScrolledText(input_frame, font=("Meiryo", 10), 
                                                   relief=tk.FLAT, padx=5, pady=5)
        self.input_area.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # --- 右側：ステップ2（結果パネル） ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # 2. 分析レポートを先に下側に配置（確実に表示）
        report_frame = tk.LabelFrame(self.right_panel, text=" 📊 AI分析レポート ", 
                                    font=("Meiryo", 9, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        report_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        self.report_container = tk.Frame(report_frame, bg=self.BG_WHITE, padx=10, pady=10)
        self.report_container.pack(fill=tk.X)

        self.lbl_score = tk.Label(self.report_container, text="スコア: 0", 
                                 font=("Meiryo", 10), bg=self.BG_WHITE, fg=self.TEXT_COLOR)
        self.lbl_score.pack(anchor="w")

        self.lbl_detected = tk.Label(self.report_container, text="検知: なし", 
                                    font=("Meiryo", 9), bg=self.BG_WHITE, fg="#E67E22", 
                                    wraplength=300, justify="left")
        self.lbl_detected.pack(anchor="w")

        self.lbl_warning = tk.Label(self.report_container, text="安全な投稿です ✅", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, fg=self.SAFE_COLOR)
        self.lbl_warning.pack(pady=(5, 0))

        # 1. フィルタリング結果（残りの中央スペースを占有）
        output_frame = tk.LabelFrame(self.right_panel, text=" 📝 STEP 2: 修正イメージ ", 
                                    font=("Meiryo", 9, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        output_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.output_area = scrolledtext.ScrolledText(output_frame, font=("Meiryo", 10), 
                                                    bg="#F7F7F7", relief=tk.FLAT,
                                                    fg=self.TEXT_COLOR, state=tk.DISABLED,
                                                    padx=5, pady=5)
        self.output_area.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    def process_filter(self):
        """入力テキストの取得と解析（既存ロジックを統合）"""
        text = self.input_area.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("お知らせ", "文章を入力してください。")
            return

        # AI分析実行
        clean_text, score, bad_words = self.ai.analyze(text)

        # 1. 修正テキストの反映
        self.output_area.config(state="normal")
        self.output_area.delete("1.0", tk.END)
        self.output_area.insert(tk.END, clean_text)
        self.output_area.config(state="disabled")

        # 2. スコアと単語の表示
        self.lbl_score.config(text=f"感情スコア: {score}")
        if bad_words:
            unique_words = list(set(bad_words))
            self.lbl_detected.config(text=f"検知: {', '.join(unique_words)}")
        else:
            self.lbl_detected.config(text="検知: なし")

        # 3. 警告ラベルと配色の更新
        if score == 0:
            self.lbl_warning.config(text="安全な投稿です ✅", fg=self.SAFE_COLOR)
        elif score > -5:
            self.lbl_warning.config(text="⚠️ 不適切な表現あり", fg="#E67E22")
        elif score >= -10:
            self.lbl_warning.config(text="❌ 攻撃的な内容です", fg=self.ALERT_COLOR)
        else:
            self.lbl_warning.config(text="🚨 凍結対象レベル 🚨", fg=self.ALERT_COLOR)

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = FilterApp(root)
    root.mainloop()