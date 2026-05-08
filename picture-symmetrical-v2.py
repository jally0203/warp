import pygame
from pygame.locals import *
from OpenGL.GL import *
import numpy as np
import cv2
import json
import os

# 配置參數
GRID_RES = 4  # 改為 4x4 網格
SCREEN_RES = (1280, 720) 
SAVE_FILE = "warp_config.json"

class Warper:
    def __init__(self, img_path):
        # 1. 載入影像
        if not os.path.exists(img_path):
            img = np.zeros((720, 1280, 3), dtype=np.uint8)
            cv2.putText(img, "TEST IMAGE", (400, 360), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 255), 5)
        else:
            img = cv2.imread(img_path)
            
        img = cv2.flip(img, 0)
        self.img_h, self.img_w = img.shape[:2]
        img_data = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).tobytes()

        # 2. 建立 OpenGL 紋理
        self.texid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texid)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, self.img_w, self.img_h, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)

        # 3. 初始化或讀取頂點座標
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
                self.mesh_x = np.array(data["x"])
                self.mesh_y = np.array(data["y"])
            print("載入現有存檔成功")
        else:
            x = np.linspace(-1.0, 1.0, GRID_RES)
            y = np.linspace(-1.0, 1.0, GRID_RES)
            self.mesh_x, self.mesh_y = np.meshgrid(x, y)
        
        # 紋理座標固定
        tx = np.linspace(0.0, 1.0, GRID_RES)
        ty = np.linspace(0.0, 1.0, GRID_RES)
        self.tex_x, self.tex_y = np.meshgrid(tx, ty)

        self.selected_node = None
        self.symmetry = True # 對稱模式開關

    def save_config(self):
        data = {"x": self.mesh_x.tolist(), "y": self.mesh_y.tolist()}
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)
        print("存檔成功")

    def update_node(self, idx, gx, gy):
        # 更新目前選中的點
        self.mesh_x[idx] = gx
        self.mesh_y[idx] = gy
        
        # 如果開啟對稱模式，連動右側對應點
        if self.symmetry:
            row, col = idx
            target_col = (GRID_RES - 1) - col
            if target_col != col: # 避開中間軸
                # X 座標鏡像 (相對於中心 0)
                self.mesh_x[row, target_col] = -gx
                # Y 座標同步
                self.mesh_y[row, target_col] = gy

    def draw(self, show_points=True):
        glClear(GL_COLOR_BUFFER_BIT)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texid)
        
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
            glPointSize(10)
            glBegin(GL_POINTS)
            for i in range(GRID_RES):
                for j in range(GRID_RES):
                    # 對稱點顯示不同顏色
                    if self.symmetry and j >= GRID_RES // 2:
                        glColor3f(0, 1, 1) # 右側點為青色
                    else:
                        glColor3f(1, 0, 0) # 左側控制點為紅色
                    glVertex2f(self.mesh_x[i, j], self.mesh_y[i, j])
            glEnd()
            glColor3f(1, 1, 1)

def main():
    pygame.init()
    pygame.display.set_mode(SCREEN_RES, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("4x4 Symmetry Warp - [S]ave [Y]mmetry [H]ide")
    
    warper = Warper("test.png") 
    clock = pygame.time.Clock()
    show_points = True

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            m_pos = pygame.mouse.get_pos()
            gx = (m_pos[0] / SCREEN_RES[0]) * 2 - 1
            gy = (1 - m_pos[1] / SCREEN_RES[1]) * 2 - 1

            if event.type == MOUSEBUTTONDOWN:
                dists = np.sqrt((warper.mesh_x - gx)**2 + (warper.mesh_y - gy)**2)
                min_idx = np.unravel_index(np.argmin(dists), dists.shape)
                if dists[min_idx] < 0.1:
                    warper.selected_node = min_idx
            
            if event.type == MOUSEBUTTONUP:
                warper.selected_node = None
            
            if event.type == KEYDOWN:
                if event.key == K_s: warper.save_config()
                if event.key == K_y: warper.symmetry = not warper.symmetry
                if event.key == K_h: show_points = not show_points

        if warper.selected_node:
            warper.update_node(warper.selected_node, gx, gy)

        warper.draw(show_points)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
