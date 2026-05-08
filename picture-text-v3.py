import pygame
from pygame.locals import *
from OpenGL.GL import *
import numpy as np
import cv2
import json
import os

# 配置參數
GRID_RES = 4
SCREEN_RES = (1280, 720) 
SAVE_FILE = "warp_config.json"

class TextRenderer:
    """專門處理在 OpenGL 環境中顯示文字的類別"""
    def __init__(self, font_size=24):
        pygame.font.init()
        self.font = pygame.font.SysFont("Arial", font_size)

    def draw(self, text, x, y):
        # 將文字渲染到 Surface
        text_surface = self.font.render(text, True, (255, 255, 255))
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        width, height = text_surface.get_size()

        # 建立臨時貼圖
        tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

        # 繪製文字方塊 (使用正交投影座標)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        
        # 將螢幕座標轉為 OpenGL 座標 (-1 to 1)
        nx = (x / SCREEN_RES[0]) * 2 - 1
        ny = (1 - y / SCREEN_RES[1]) * 2 - 1
        nw = (width / SCREEN_RES[0]) * 2
        nh = (height / SCREEN_RES[1]) * 2

        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(nx, ny - nh)
        glTexCoord2f(1, 0); glVertex2f(nx + nw, ny - nh)
        glTexCoord2f(1, 1); glVertex2f(nx + nw, ny)
        glTexCoord2f(0, 1); glVertex2f(nx, ny)
        glEnd()

        glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)
        glDeleteTextures([tex])

class Warper:
    def __init__(self, img_path):
        if not os.path.exists(img_path):
            img = np.zeros((720, 1280, 3), dtype=np.uint8)
            cv2.putText(img, "TEST IMAGE", (400, 360), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 255), 5)
        else:
            img = cv2.imread(img_path)
            
        img = cv2.flip(img, 0)
        self.img_h, self.img_w = img.shape[:2]
        img_data = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).tobytes()

        self.texid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texid)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, self.img_w, self.img_h, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)

        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
                self.mesh_x = np.array(data["x"])
                self.mesh_y = np.array(data["y"])
        else:
            x = np.linspace(-1.0, 1.0, GRID_RES)
            y = np.linspace(-1.0, 1.0, GRID_RES)
            self.mesh_x, self.mesh_y = np.meshgrid(x, y)
        
        self.tex_x, self.tex_y = np.meshgrid(np.linspace(0.0, 1.0, GRID_RES), np.linspace(0.0, 1.0, GRID_RES))
        self.selected_node = None
        self.symmetry = True

    def update_node(self, idx, gx, gy):
        self.mesh_x[idx], self.mesh_y[idx] = gx, gy
        if self.symmetry:
            row, col = idx
            target_col = (GRID_RES - 1) - col
            if target_col != col:
                self.mesh_x[row, target_col], self.mesh_y[row, target_col] = -gx, gy

    def draw(self, show_points=True):
        glClear(GL_COLOR_BUFFER_BIT)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texid)
        for i in range(GRID_RES - 1):
            glBegin(GL_TRIANGLE_STRIP)
            for j in range(GRID_RES):
                glTexCoord2f(self.tex_x[i, j], self.tex_y[i, j]); glVertex2f(self.mesh_x[i, j], self.mesh_y[i, j])
                glTexCoord2f(self.tex_x[i+1, j], self.tex_y[i+1, j]); glVertex2f(self.mesh_x[i+1, j], self.mesh_y[i+1, j])
            glEnd()
        if show_points:
            glDisable(GL_TEXTURE_2D); glPointSize(12); glBegin(GL_POINTS)
            for i in range(GRID_RES):
                for j in range(GRID_RES):
                    if self.symmetry and j >= GRID_RES // 2: glColor3f(0, 1, 1)
                    else: glColor3f(1, 0, 0)
                    glVertex2f(self.mesh_x[i, j], self.mesh_y[i, j])
            glEnd(); glColor3f(1, 1, 1)

def main():
    pygame.init()
    pygame.display.set_mode(SCREEN_RES, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("RPi Warp UI")
    
    warper = Warper("test.png") 
    text_renderer = TextRenderer(20)
    clock = pygame.time.Clock()
    show_points = True
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            m_pos = pygame.mouse.get_pos()
            gx, gy = (m_pos[0]/SCREEN_RES[0])*2-1, (1-m_pos[1]/SCREEN_RES[1])*2-1

            if event.type == MOUSEBUTTONDOWN:
                dists = np.sqrt((warper.mesh_x - gx)**2 + (warper.mesh_y - gy)**2)
                idx = np.unravel_index(np.argmin(dists), dists.shape)
                if dists[idx] < 0.1: warper.selected_node = idx
            if event.type == MOUSEBUTTONUP: warper.selected_node = None
            if event.type == KEYDOWN:
                if event.key == K_s: 
                    with open(SAVE_FILE, "w") as f: json.dump({"x": warper.mesh_x.tolist(), "y": warper.mesh_y.tolist()}, f)
                if event.key == K_y: warper.symmetry = not warper.symmetry
                if event.key == K_h: show_points = not show_points

        if warper.selected_node: warper.update_node(warper.selected_node, gx, gy)

        warper.draw(show_points)
        
        # 繪製左下角文字說明
        if show_points:
            text_renderer.draw(f"[S] Save Config", 20, 600)
            text_renderer.draw(f"[Y] Symmetry Mode: {'ON' if warper.symmetry else 'OFF'}", 20, 630)
            text_renderer.draw(f"[H] Hide Control Points", 20, 660)
            text_renderer.draw(f"Drag Red Points to warp", 20, 690)

        pygame.display.flip()
        clock.tick(60)
    pygame.quit()

if __name__ == "__main__":
    main()
