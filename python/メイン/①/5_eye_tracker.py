# 視線追跡マウスシステムアプリケーション
# インストール: pip install opencv-python mediapipe pyautogui numpy
# 実行方法: python 5_eye_tracker_mouse.py
# Secrect Interpreter: Python 3.11.9

import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import time
import sys
import math

class EyeTrackerMouse:
    """
    視線追跡マウスシステムクラス
    
    MediaPipe Face Meshを利用して虹彩(Iris)の位置を検出し、
    マウスカーソルの移動とクリック操作を行います。
    """
    
    def __init__(self):
        print("システムを初期化しています...")
        
        # --- 設定エリア (感度調整) ---
        self.mouse_sensitivity = 1.5   # マウス感度（大きいほど少しの動きで大きく動く）
        self.smooth_factor = 0.2       # 動きの滑らかさ (0.1~0.9, 小さいほど遅延するが滑らか)
        self.blink_threshold = 0.045   # まばたき判定の閾値（目の縦幅率。個人差あり調整が必要）
        self.click_cooldown = 1.0      # クリック後の待機時間（秒）
        # ---------------------------

        # マウス安全装置の解除（画面端で停止する機能を無効化し、Escキーでの終了を優先）
        # ※ 注意: プログラムが暴走した場合は Ctrl+Alt+Del 等で強制終了してください
        pyautogui.FAILSAFE = False

        # 画面サイズの取得
        try:
            self.screen_w, self.screen_h = pyautogui.size()
        except Exception as e:
            print(f"【警告】画面サイズの取得に失敗しました: {e}")
            self.screen_w, self.screen_h = 1920, 1080

        # MediaPipe Face Meshの初期化
        # refine_landmarks=True にすることで虹彩(Iris)のランドマークを取得可能
        self.mp_face_mesh = mp.solutions.face_mesh
        try:
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        except Exception as e:
            print(f"【致命的エラー】AIモデルの読み込みに失敗しました: {e}")
            sys.exit(1)

        # Webカメラの初期化
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise IOError("カメラデバイスが見つかりません。")
            
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        except Exception as e:
            print(f"【致命的エラー】カメラの起動に失敗しました: {e}")
            sys.exit(1)

        # 内部変数の初期化
        self.prev_x, self.prev_y = 0, 0
        self.last_click_time = 0
        self.cam_w = 640
        self.cam_h = 480

        print("起動完了。")
        print("--------------------------------------------------")
        print("【操作方法】")
        print("  ・顔（目）を動かす -> マウス移動")
        print("  ・左目を強めに閉じる（ウインク） -> 左クリック")
        print("  ・[Esc] キー -> 緊急停止（終了）")
        print("--------------------------------------------------")

    def calculate_screen_coordinates(self, iris_x, iris_y):
        """
        目の座標を画面上のマウス座標に変換します。
        スムージング処理を含みます。
        """
        # カメラ座標をスクリーン座標へマッピング
        # カメラの中央付近を使うために範囲を少し絞って拡大する計算
        # 画面の端までカーソルが届くように感度を適用
        
        # 中心からのオフセットを計算 (0.5が中心)
        offset_x = iris_x - 0.5
        offset_y = iris_y - 0.5

        # 感度を掛けて、スクリーンサイズに合わせる
        # カメラ映像は鏡像(左右反転)させるため、X軸の計算を反転
        target_x = self.screen_w * (0.5 + offset_x * self.mouse_sensitivity * -1) # 左右反転
        target_y = self.screen_h * (0.5 + offset_y * self.mouse_sensitivity)

        # 画面外にはみ出さないようにクリッピング
        target_x = max(0, min(self.screen_w, target_x))
        target_y = max(0, min(self.screen_h, target_y))

        # スムージング（移動平均）
        # 現在位置 = 前回の位置 * (1-a) + 目標位置 * a
        cur_x = self.prev_x + (target_x - self.prev_x) * self.smooth_factor
        cur_y = self.prev_y + (target_y - self.prev_y) * self.smooth_factor

        self.prev_x, self.prev_y = cur_x, cur_y
        return int(cur_x), int(cur_y)

    def detect_blink_and_click(self, landmarks):
        """
        左目のまばたき（ウインク）を検出してクリックを実行します。
        Eye Aspect Ratio (EAR) の簡易版を使用。
        """
        # 左目の上下のランドマークID (MediaPipe Face Mesh)
        # 159: 上瞼, 145: 下瞼
        top = landmarks.landmark[159]
        bottom = landmarks.landmark[145]

        # 上下の距離（Y座標の差）を計算
        eye_height = abs(top.y - bottom.y)

        # 閾値より小さければ「目を閉じている」と判定
        if eye_height < self.blink_threshold:
            current_time = time.time()
            if current_time - self.last_click_time > self.click_cooldown:
                print("Click detected!")
                pyautogui.click()
                self.last_click_time = current_time
                # 視覚フィードバック（コンソール表示）
                return True
        return False

    def run(self):
        """メイン実行ループ"""
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    print("カメラ映像の取得に失敗しました。")
                    break

                # 画像処理
                frame = cv2.flip(frame, 1) # 鏡のように反転
                h, w, _ = frame.shape
                self.cam_h, self.cam_w = h, w
                
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                rgb_frame.flags.writeable = False
                
                results = self.face_mesh.process(rgb_frame)
                rgb_frame.flags.writeable = True

                if results.multi_face_landmarks:
                    for face_landmarks in results.multi_face_landmarks:
                        # ---------------------------
                        # 1. 視線（虹彩）による移動処理
                        # ---------------------------
                        # 虹彩の中心（右目: 473, 左目: 468）
                        # 今回は「右目(画面向かって左)」を使用してみる
                        # 両目の中心を取るとより安定するが、簡易実装のため片目ベース
                        iris_landmark = face_landmarks.landmark[473]
                        
                        # 座標変換とマウス移動
                        screen_x, screen_y = self.calculate_screen_coordinates(iris_landmark.x, iris_landmark.y)
                        pyautogui.moveTo(screen_x, screen_y)

                        # ---------------------------
                        # 2. まばたきクリック処理
                        # ---------------------------
                        is_clicked = self.detect_blink_and_click(face_landmarks)

                        # ---------------------------
                        # 3. デバッグ描画
                        # ---------------------------
                        # 虹彩の位置を描画
                        cx, cy = int(iris_landmark.x * w), int(iris_landmark.y * h)
                        color = (0, 255, 0) if not is_clicked else (0, 0, 255) # クリック時は赤
                        cv2.circle(frame, (cx, cy), 5, color, -1)
                        
                        # 目の上下を描画（まばたき判定用）
                        top = face_landmarks.landmark[159]
                        bottom = face_landmarks.landmark[145]
                        cv2.circle(frame, (int(top.x * w), int(top.y * h)), 2, (0, 255, 255), -1)
                        cv2.circle(frame, (int(bottom.x * w), int(bottom.y * h)), 2, (0, 255, 255), -1)

                # 画面表示
                cv2.putText(frame, "Press [Esc] to Quit", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.imshow('Eye Tracker Mouse', frame)

                # 終了判定 (Escキー)
                key = cv2.waitKey(1) & 0xFF
                if key == 27: # Esc
                    print("終了コマンドを受信しました。")
                    break

        except KeyboardInterrupt:
            print("\nユーザーによる中断を受け付けました。")
        except pyautogui.FailSafeException:
            print("\n【安全装置作動】マウスが画面端に移動したため停止しました。")
        except Exception as e:
            print(f"\n【予期せぬエラー】: {e}")
        finally:
            if self.cap is not None and self.cap.isOpened():
                self.cap.release()
            cv2.destroyAllWindows()
            print("システムを終了しました。")

if __name__ == "__main__":
    app = EyeTrackerMouse()
    app.run()