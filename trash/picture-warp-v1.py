import pygame
from pygame.locals import *
from OpenGL.GL import *
import numpy as np
import cv2
import json
import os

# 配置參數
GRID_RES = 15  # 增加網格密度，讓球面變形更平滑
SCREEN_RES = (1280, 720) 
SAVE_FILE = "warp_config.json"

class Warper:
    def __init__(self, img_path):
        # 1. 載入影像
        if not os.path.exists(img_path):
            # 如果找不到 test.png，建立一個彩色測試圖
            print(f"找不到 {img_path}，建立臨時測試圖...")
            img = np.zeros((720, 1280, 3), dtype=np.uint8)
            cv2.putText(img, "TEST IMAGE", (400, 360), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 255), 5)
        else:
            img = cv2.imread(img_path)
            
        img = cv2.flip(img, 0) # OpenGL 座標 Y 軸向上
        self.img_h, self.img_w = img.shape[:2]
        img_data = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).tobytes()

        # 2. 建立 OpenGL 紋理
        self.texid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texid)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, self.img_w, self.img_h, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)

        # 3. 初始化頂點與紋理座標
        # mesh_x/y 是會變動的渲染位置 (-1 to 1)
        x = np.linspace(-1.0, 1.0, GRID_RES)
        y = np.linspace(-1.0, 1.0, GRID_RES)
        self.mesh_x, self.mesh_y = np.meshgrid(x, y)
        
        # tex_x/y 是固定的圖片取樣位置 (0 to 1)
        tx = np.linspace(0.0, 1.0, GRID_RES)
        ty = np.linspace(0.0, 1.0, GRID_RES)
        self.tex_x, self.tex_y = np.meshgrid(tx, ty)

        self.selected_node = None

    def save_config(self):
        data = {"x": self.mesh_x.tolist(), "y": self.mesh_y.tolist()}
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)
        print(f"設定已成功存檔至 {SAVE_FILE}")

    def draw(self, show_points=True):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texid)
        glColor3f(1, 1, 1)

        # 核心：使用 TRIANGLE_STRIP 畫出變形後的網格
        for i in range(GRID_RES - 1):
            glBegin(GL_TRIANGLE_STRIP)
            for j in range(GRID_RES):
                glTexCoord2f(self.tex_x[i, j], self.tex_y[i, j])
                glVertex2f(self.mesh_x[i, j], self.mesh_y[i, j])
                
                glTexCoord2f(self.tex_x[i+1, j], self.tex_y[i+1, j])
                glVertex2f(self.mesh_x[i+1, j], self.mesh_y[i+1, j])
            glEnd()
        
        if show_points:
            glDisable(GL_TEXTURE_2D)
            glPointSize(8)
            glBegin(GL_POINTS)
            glColor3f(1, 0, 0) # 紅色控制點
            for i in range(GRID_RES):
                for j in range(GRID_RES):
                    glVertex2f(self.mesh_x[i, j], self.mesh_y[i, j])
            glEnd()

def main():
    pygame.init()
    # 在樹莓派上使用硬體加速
    display_flags = DOUBLEBUF | OPENGL
    screen = pygame.display.set_mode(SCREEN_RES, display_flags)
    pygame.display.set_caption("RPi Keystone Simulation - Drag points")
    
    warper = Warper("test.png") 

    clock = pygame.time.Clock()
    running = True
    show_points = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # 滑鼠位置轉換
            m_pos = pygame.mouse.get_pos()
            gx = (m_pos[0] / SCREEN_RES[0]) * 2 - 1
            gy = (1 - m_pos[1] / SCREEN_RES[1]) * 2 - 1

            if event.type == MOUSEBUTTONDOWN:
                # 計算最近點
                dists = np.sqrt((warper.mesh_x - gx)**2 + (warper.mesh_y - gy)**2)
                min_idx = np.unravel_index(np.argmin(dists), dists.shape)
                if dists[min_idx] < 0.1:
                    warper.selected_node = min_idx
            
            if event.type == MOUSEBUTTONUP:
                warper.selected_node = None
            
            if event.type == KEYDOWN:
                if event.key == K_s:
                    warper.save_config()
                if event.key == K_h: # 按 H 切換控制點顯示/隱藏
                    show_points = not show_points

        # 即時更新選中點的座標，達成連動效果
        if warper.selected_node:
            warper.mesh_x[warper.selected_node] = gx
            warper.mesh_y[warper.selected_node] = gy

        # 繪圖
        warper.draw(show_points)
        pygame.display.flip()
        
        # 限制偵率節省樹莓派效能
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
