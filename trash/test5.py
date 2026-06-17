import pygame
from pygame.locals import *
from OpenGL.GL import *
import numpy as np

def test_alignment():
    pygame.init()
    # 故意使用非 4 倍數的解析度測試
    pygame.display.set_mode((800, 600), DOUBLEBUF | OPENGL)
    print("測試非標準寬度影像對齊 (Alignment)...")
    try:
        # 這是主程式可能缺失的關鍵指令
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        
        # 建立隨機數據 (1919x1079 是非標準尺寸範例)
        data = np.random.randint(0, 256, (1079, 1919, 3), dtype=np.uint8).tobytes()
        
        tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, 1919, 1079, 0, GL_RGB, GL_UNSIGNED_BYTE, data)
        print("Success: OpenGL 像素對齊與紋理上傳測試通過！")
    except Exception as e:
        print(f"Failed: 紋理操作失敗: {e}")
    pygame.quit()

if __name__ == "__main__":
    test_alignment()
    input("按 Enter 結束...")
