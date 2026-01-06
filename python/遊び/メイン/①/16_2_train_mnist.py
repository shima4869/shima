import joblib
from sklearn.datasets import fetch_openml
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
import numpy as np

def main():
    print("==========================================")
    print("  AI学習プログラム (MNIST)")
    print("==========================================")
    print("1. 手書き数字データ(MNIST)をダウンロードしています...")
    print("   (初回は数分かかります。コーヒーでも飲んでお待ちください)")
    
    # 7万枚の手書き数字データを取得
    # 28x28ピクセルの画像データです
    mnist = fetch_openml('mnist_784', version=1, as_frame=False, parser='auto')
    
    # 画像データ(X)と正解ラベル(y)
    X = mnist.data
    y = mnist.target

    # データを0.0〜1.0の範囲に正規化（AIが学習しやすくなる）
    X = X / 255.0

    # 学習用とテスト用に分ける（6万枚で学習、1万枚でテスト）
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, random_state=42)

    print("2. 学習を開始します...")
    print("   (AIが7万枚の画像を勉強中...)")

    # ニューラルネットワーク（多層パーセプトロン）の作成
    # hidden_layer_sizes=(100,): 脳細胞の数
    model = MLPClassifier(hidden_layer_sizes=(100,), max_iter=20, verbose=True, random_state=42)
    
    # 学習実行
    model.fit(X_train, y_train)

    print("3. テストデータで実力を確認中...")
    score = model.score(X_test, y_test)
    print(f"   正解率: {score*100:.2f}%")

    # 学習済みモデルをファイルに保存
    joblib.dump(model, "mnist_model.pkl")
    print("4. 学習完了！ 'mnist_model.pkl' を保存しました。")

if __name__ == "__main__":
    main()