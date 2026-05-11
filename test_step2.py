import cv2
import os

def test_assets():
    files = ["test.png", "video.mp4"]
    for f in files:
        exists = os.path.exists(f)
        print(f"檔案 [{f}] 是否存在: {exists}")
        if exists:
            if f.endswith('.png'):
                img = cv2.imread(f)
                print(f" -> 圖片讀取成功，尺寸: {img.shape if img is not None else '讀取失敗'}")
            else:
                cap = cv2.VideoCapture(f)
                ret, frame = cap.read()
                print(f" -> 影片讀取成功: {ret}")
                cap.release()

if __name__ == "__main__":
    test_assets()
