# ARマーカー生成スクリプト ✨
# インストール: pip install opencv-python numpy
# 実行方法: python ar_generate.py
# Select Interpreter: Python 3.11.9

import cv2
import numpy as np

# マーカーの設定（検知側と同じ DICT_4X4_50 を指定）
dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

# ID 0 のマーカーを生成 (200x200ピクセル)
marker_img = np.zeros((200, 200, 1), dtype="uint8")

# OpenCVのバージョン互換性対応
try:
    cv2.aruco.generateImageMarker(dictionary, 0, 200, marker_img, 1)
except AttributeError:
    # 古いバージョン用
    cv2.aruco.drawMarker(dictionary, 0, 200, marker_img, 1)

cv2.imwrite("marker_id0.png", marker_img)
print("画像 'marker_id0.png' を保存しました。これを開いてカメラに見せてください。")