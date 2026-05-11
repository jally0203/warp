import pygame

def test_font():
    pygame.init()
    try:
        font_name = "Arial"
        font = pygame.font.SysFont(font_name, 28)
        print(f"字體 [{font_name}] 載入成功")
        surface = font.render("Test Text", True, (255, 255, 255))
        print("文字渲染測試成功")
    except Exception as e:
        print(f"字體系統異常: {e}")
    pygame.quit()

if __name__ == "__main__":
    test_font()
