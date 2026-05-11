import pygame

def test_event_loop():
    pygame.init()
    pygame.display.set_mode((400, 300))
    clock = pygame.time.Clock()
    print("測試事件循環與偵率限制...")
    try:
        for i in range(60): # 測試兩秒
            for event in pygame.event.get():
                if event.type == pygame.QUIT: break
            clock.tick(30)
            if i % 10 == 0: print(f"已運行 {i} 幀...")
        print("Success: 事件循環運作正常。")
    except Exception as e:
        print(f"Failed: 事件循環異常: {e}")
    pygame.quit()

if __name__ == "__main__":
    test_event_loop()
    input("按 Enter 結束...")
