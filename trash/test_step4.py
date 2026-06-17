import os
import cv2
import sys
import traceback

def test_files():
    try:
        # 取得 EXE 執行路徑
        base_path = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else "."
        print(f"--- 診斷開始 ---")
        print(f"EXE 路徑: {base_path}")

        targets = ["test.png", "video.mp4"]
        for name in targets:
            full_path = os.path.join(base_path, name)
            exists = os.path.exists(full_path)
            print(f"檔案 [{name}] 存在: {exists} (路徑: {full_path})")
            
            if exists:
                if name.endswith('.mp4'):
                    cap = cv2.VideoCapture(full_path)
                    ret, _ = cap.read()
                    print(f" -> 影片解碼測試: {'成功' if ret else '失敗'}")
                    cap.release()
    except Exception:
        print(traceback.format_exc())

if __name__ == "__main__":
    test_files()
    print(f"--- 診斷結束 ---")
    input("按 Enter 鍵結束程式...") # 確保視窗不會自動關閉
