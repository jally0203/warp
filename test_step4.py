import sys
import os

def get_path(relative_path):
    """ 獲取檔案路徑，相容開發環境與 PyInstaller 打包環境 """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# 在 Warper 類別中使用：
# self.load_image(get_path(IMAGE_FILE))
# self.cap = cv2.VideoCapture(get_path(VIDEO_FILE))
