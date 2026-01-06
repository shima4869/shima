# AIスパム分類機
# インストール: pip install janome scikit-learn pillow numpy
# 実行方法: python 13_spam_classifier.py
# Select Interpreter: Python 3.11.9

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from janome.tokenizer import Tokenizer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
import numpy as np
from PIL import Image, ImageTk
import time
import os

# --- AIエンジン (既存のシステムを完全に継承) ---
class SpamDetector:
    def __init__(self):
        self.tokenizer = Tokenizer()
        # scikit-learnの仕様変更対策
        self.vectorizer = CountVectorizer(
            tokenizer=self._tokenize, 
            token_pattern=None
        )
        self.classifier = MultinomialNB()
        
        self.train_data = [
            "【当選】100万円が当たりました！今すぐクリック",
            "完全無料！出会い系サイトで彼女を作ろう",
            "未納料金があります。至急ご連絡ください",
            "絶対に儲かる投資話教えます。限定公開",
            "有料動画の閲覧履歴があります。法的手続きに入ります",
            "短時間で高収入！誰でも簡単に稼げます",
            "おめでとうございます！豪華賞品プレゼント",
            "明日の会議は10時から会議室Aで行います",
            "プロジェクトの進捗報告をお願いします",
            "先日はありがとうございました。また飲みに行きましょう",
            "Amazonでのご注文ありがとうございます。発送しました",
            "宿題の提出期限は明日までです",
            "今度の週末、映画でも見に行かない？",
            "お疲れ様です。資料を添付いたしましたのでご確認ください",
        ]
        self.train_labels = [1, 1, 1, 1, 1, 1, 1,  0, 0, 0, 0, 0, 0, 0]
        self.is_trained = False

    def _tokenize(self, text):
        if not text or not isinstance(text, str):
            return []
        return [token.surface for token in self.tokenizer.tokenize(text)]

    def train(self):
        try:
            X_train = self.vectorizer.fit_transform(self.train_data)
            self.classifier.fit(X_train, self.train_labels)
            self.is_trained = True
            return True
        except Exception:
            return False

    def predict(self, text):
        if not text or text.strip() == "":
            return None, "メッセージを入力してください。"
        if not self.is_trained:
            return None, "エラー: モデルが学習されていません。"
        try:
            X_test = self.vectorizer.transform([text])
            prediction = self.classifier.predict(X_test)[0]
            proba = self.classifier.predict_proba(X_test)[0]
            return prediction, proba[1]
        except Exception as e:
            return None, f"エラーが発生しました: {e}"

class SpamApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIスパム分類機 ✨")
        
        # ウィンドウサイズ（コンパクト：700x500）
        self.root.geometry("700x500")
        self.root.configure(bg="#FFFBEB")

        self.PRIMARY_COLOR = "#FF9F43"     # オレンジ
        self.SECONDARY_COLOR = "#FFCC33"   # イエロー
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_COLOR = "#4B4B4B"
        self.SAFE_COLOR = "#2ECC71"        # 緑
        self.ALERT_COLOR = "#E74C3C"       # 赤

        self.detector = SpamDetector()
        self.detector.train()
        
        self.setup_ui()

    def setup_ui(self):
        # メインタイトル
        title_label = tk.Label(self.root, text="🛡️ AIスパム分類機", 
                              font=("Meiryo", 16, "bold"), bg="#FFFBEB", fg=self.PRIMARY_COLOR)
        title_label.pack(pady=(15, 5))

        # メインコンテナ
        self.main_container = tk.Frame(self.root, bg="#FFFBEB")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # 左右 5:5 の比率設定
        self.main_container.columnconfigure(0, weight=1, uniform="group1")
        self.main_container.columnconfigure(1, weight=1, uniform="group1")
        self.main_container.rowconfigure(0, weight=1)

        # --- 左側：ステップ1（入力パネル） ---
        self.left_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # 実行ボタンを先に「下」へ配置（確実に表示するため）
        self.run_btn = tk.Button(self.left_panel, text="AI判定を実行 🔍", 
                                command=self.judge,
                                bg=self.PRIMARY_COLOR, fg="white", font=("Meiryo", 11, "bold"),
                                relief=tk.FLAT, cursor="hand2", pady=10)
        self.run_btn.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        # 入力枠を「残りすべてのスペース」に配置
        input_frame = tk.LabelFrame(self.left_panel, text=" 📩 STEP 1: 本文入力 ", 
                                   font=("Meiryo", 9, "bold"), bg=self.BG_WHITE, 
                                   fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        input_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.text_area = scrolledtext.ScrolledText(input_frame, font=("Meiryo", 10), 
                                                  relief=tk.FLAT, padx=5, pady=5, undo=True)
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # --- 右側：ステップ2（判定レポート） ---
        self.right_panel = tk.Frame(self.main_container, bg="#FFFBEB")
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        result_frame = tk.LabelFrame(self.right_panel, text=" 📊 STEP 2: 判定レポート ", 
                                    font=("Meiryo", 9, "bold"), bg=self.BG_WHITE, 
                                    fg=self.PRIMARY_COLOR, relief=tk.RIDGE, bd=2)
        result_frame.pack(fill=tk.BOTH, expand=True)

        self.report_container = tk.Frame(result_frame, bg=self.BG_WHITE, padx=10, pady=15)
        self.report_container.pack(fill=tk.BOTH, expand=True)

        self.status_icon = tk.Label(self.report_container, text="📩", 
                                   font=("Segoe UI Emoji", 42), bg=self.BG_WHITE)
        self.status_icon.pack(pady=(5, 5))

        self.result_label = tk.Label(self.report_container, text="メッセージを\n入力してね", 
                                   font=("Meiryo", 11, "bold"), bg=self.BG_WHITE, 
                                   fg=self.TEXT_COLOR, wraplength=280)
        self.result_label.pack(pady=10)

        self.score_label = tk.Label(self.report_container, text="判定スコア: --%", 
                                   font=("Meiryo", 9), bg=self.BG_WHITE, fg="#95A5A6")
        self.score_label.pack()

        hint_label = tk.Label(self.right_panel, text="AIが不審な単語の組み合わせを\n統計的に解析して見抜きます。", 
                             bg="#FFFBEB", fg="#95A5A6", font=("Meiryo", 8), justify=tk.CENTER)
        hint_label.pack(side=tk.BOTTOM, pady=(10, 0))

    def judge(self):
        input_text = self.text_area.get("1.0", tk.END).strip()
        prediction, proba = self.detector.predict(input_text)
        
        if prediction is None:
            messagebox.showwarning("入力エラー", proba)
            return

        score = proba * 100
        if prediction == 1:
            self.result_label.config(text=f"🚨 迷惑メールの可能性が大！", fg=self.ALERT_COLOR)
            self.status_icon.config(text="🚫")
            self.score_label.config(text=f"迷惑メール確信度: {score:.1f}%")
        else:
            self.result_label.config(text=f"✅ 通常のメッセージです", fg=self.SAFE_COLOR)
            self.status_icon.config(text="🛡️")
            self.score_label.config(text=f"迷惑メール確信度: {score:.1f}%")

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    app = SpamApp(root)
    root.mainloop()