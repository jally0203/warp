import pygame
from pygame.locals import *
from OpenGL.GL import *
import numpy as np
import cv2
import json
import os
import time

# Configuration
GRID_RES = 8
SCREEN_RES = (1920, 1080)
SAVE_FILE = "warp_config.json"
VIDEO_FILE = "video.mp4"
IMAGE_FILE = "test.png"

class TextRenderer:
    def __init__(self, font_size=28):
        pygame.font.init()
        self.font = pygame.font.SysFont("Arial", font_size)

    def draw(self, text, x, y):
        text_surface = self.font.render(text, True, (255, 255, 255))
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        width, height = text_surface.get_size()

        tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        
        nx, ny = (x / SCREEN_RES[0]) * 2 - 1, (1 - y / SCREEN_RES[1]) * 2 - 1
        nw, nh = (width / SCREEN_RES[0]) * 2, (height / SCREEN_RES[1]) * 2

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
    def __init__(self):
        self.texid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texid)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
                self.mesh_x, self.mesh_y = np.array(data["x"]), np.array(data["y"])
        else:
            x, y = np.linspace(-1.0, 1.0, GRID_RES), np.linspace(-1.0, 1.0, GRID_RES)
            self.mesh_x, self.mesh_y = np.meshgrid(x, y)
        
        self.tex_x, self.tex_y = np.meshgrid(np.linspace(0.0, 1.0, GRID_RES), np.linspace(0.0, 1.0, GRID_RES))
        self.selected_node = None
        self.symmetry = True
        self.mode = "IMAGE" 
        self.cap = None
        
        # 速度修正計時器變數
        self.video_fps = 30.0
        self.frame_delay = 1.0 / 30.0
        self.last_frame_time = 0.0
        
        self.load_image(IMAGE_FILE)

    def load_image(self, path):
        img = cv2.imread(path) if os.path.exists(path) else np.zeros((1080,1920,3), np.uint8)
        img = cv2.flip(img, 0)
        h, w = img.shape[:2]
        data = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).tobytes()
        glBindTexture(GL_TEXTURE_2D, self.texid)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, data)

    def toggle_mode(self):
        if self.mode == "IMAGE":
            self.cap = cv2.VideoCapture(VIDEO_FILE)
            if self.cap.isOpened():
                fps = self.cap.get(cv2.CAP_PROP_FPS)
                if fps > 0:
                    self.video_fps = fps
                    self.frame_delay = 1.0 / fps
                self.mode = "VIDEO"
                self.last_frame_time = time.time()
        else:
            if self.cap: self.cap.release()
            self.mode = "IMAGE"
            self.load_image(IMAGE_FILE)

    def update_video_frame(self):
        if self.mode == "VIDEO" and self.cap:
            current_time = time.time()
            if current_time - self.last_frame_time >= self.frame_delay:
                ret, frame = self.cap.read()
                if not ret:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self.cap.read()
                if ret:
                    frame = cv2.flip(frame, 0)
                    h, w = frame.shape[:2]
                    data = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).tobytes()
                    glBindTexture(GL_TEXTURE_2D, self.texid)
                    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, data)
                self.last_frame_time = current_time

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
        
        if show_points and self.mode == "IMAGE":
            glDisable(GL_TEXTURE_2D)
            
            # --- 【關鍵修改：放大控制點並改成圓形】 ---
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glEnable(GL_POINT_SMOOTH) # 開啟抗鋸齒，讓點變成圓形而非正方形
            glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
            
            glPointSize(20.0)         # 設定點的大小（愈大愈好，20 已經非常巨大，可依需求調整）
            
            glBegin(GL_POINTS)
            for i in range(GRID_RES):
                for j in range(GRID_RES):
                    if self.symmetry and j >= GRID_RES // 2: glColor3f(0, 1, 1)
                    else: glColor3f(1, 0, 0)
                    glVertex2f(self.mesh_x[i, j], self.mesh_y[i, j])
            glEnd()
            
            # 關閉設定，避免影響其他繪圖邏輯
            glDisable(GL_POINT_SMOOTH)
            glDisable(GL_BLEND)
            glColor3f(1, 1, 1)

def main():
    global SCREEN_RES
    SCREEN_RES = (3168, 1200)

    os.environ['SDL_VIDEO_WINDOW_POS'] = '1920,0'

    pygame.init()
    pygame.display.set_mode(SCREEN_RES, DOUBLEBUF | OPENGL | NOFRAME)
    
    warper = Warper() 
    text_renderer = TextRenderer(28)
    clock = pygame.time.Clock()
    show_ui = True
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            m_pos = pygame.mouse.get_pos()
            gx, gy = (m_pos[0]/SCREEN_RES[0])*2-1, (1-m_pos[1]/SCREEN_RES[1])*2-1

            if event.type == MOUSEBUTTONDOWN and warper.mode == "IMAGE":
                dists = np.sqrt((warper.mesh_x - gx)**2 + (warper.mesh_y - gy)**2)
                idx = np.unravel_index(np.argmin(dists), dists.shape)
                # 配合大點，稍微放寬滑鼠選取判定半徑到 0.06，手感會更好
                if dists[idx] < 0.06: warper.selected_node = idx
            if event.type == MOUSEBUTTONUP: warper.selected_node = None
            
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE: running = False
                if event.key == K_p: warper.toggle_mode()
                if event.key == K_s: 
                    with open(SAVE_FILE, "w") as f: json.dump({"x": warper.mesh_x.tolist(), "y": warper.mesh_y.tolist()}, f)
                if event.key == K_y: warper.symmetry = not warper.symmetry
                if event.key == K_h: show_ui = not show_ui

        if warper.mode == "VIDEO":
            warper.update_video_frame()
        elif warper.selected_node:
            warper.mesh_x[warper.selected_node], warper.mesh_y[warper.selected_node] = gx, gy
            if warper.symmetry:
                r, c = warper.selected_node
                tc = (GRID_RES-1) - c
                if tc != c: warper.mesh_x[r, tc], warper.mesh_y[r, tc] = -gx, gy

        warper.draw(show_ui)
        
        if show_ui and warper.mode == "IMAGE":
            y_base = SCREEN_RES[1] - 250
            text_renderer.draw(f"CALIBRATION MODE (3168x1200) - 16x16 GRID", 40, y_base)
            text_renderer.draw(f"[P] Start Video Playback", 40, y_base + 35)
            text_renderer.draw(f"[S] Save Config", 40, y_base + 70)
            text_renderer.draw(f"[Y] Symmetry: {'ON' if warper.symmetry else 'OFF'}", 40, y_base + 105)
            text_renderer.draw(f"[H] Hide UI", 40, y_base + 140)
            text_renderer.draw(f"[Esc] Exit", 40, y_base + 175)

        pygame.display.flip()
        clock.tick(120)
    
    if warper.cap: warper.cap.release()
    pygame.quit()

if __name__ == "__main__":
    main()
