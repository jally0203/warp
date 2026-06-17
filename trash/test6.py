import pygame
from pygame.locals import *
from OpenGL.GL import *

def test_fullscreen():
    pygame.init()
    target_res = (1920, 1080)
    print(f"正在測試全螢幕模式: {target_res}...")
    try:
        # 此行在 Windows + 內顯環境下最容易出錯
        screen = pygame.display.set_mode(target_res, DOUBLEBUF | OPENGL | FULLSCREEN)
        print("Success: 全螢幕 OpenGL 模式啟動成功！")
        
        glClearColor(1, 0, 0, 1) # 顯示紅色三秒
        glClear(GL_COLOR_BUFFER_BIT)
        pygame.display.flip()
        pygame.time.wait(3000)
    except Exception as e:
        print(f"Failed: 無法進入全螢幕模式。原因: {e}")
        print("建議：請檢查 Windows 顯示設定中的『縮放』是否為 100%，或嘗試取消 FULLSCREEN 標籤。")
    pygame.quit()

if __name__ == "__main__":
    test_fullscreen()
