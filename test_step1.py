import pygame
from pygame.locals import *
from OpenGL.GL import *

def run_test():
    pygame.init()
    # 建議先測試視窗化，排除全螢幕解析度不支援的問題
    screen_size = (1280, 720) 
    print(f"正在嘗試建立視窗: {screen_size}")
    try:
        pygame.display.set_mode(screen_size, DOUBLEBUF | OPENGL)
        print("OpenGL 視窗建立成功！")
        
        for _ in range(100): # 執行約 3 秒
            glClearColor(0.2, 0.4, 0.6, 1.0) # 藍色背景
            glClear(GL_COLOR_BUFFER_BIT)
            pygame.display.flip()
            pygame.time.wait(30)
        print("渲染測試完成。")
    except Exception as e:
        print(f"錯誤報告: {e}")
    pygame.quit()

if __name__ == "__main__":
    run_test()
