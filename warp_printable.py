import pygame
from pygame.locals import *
from OpenGL.GL import *
import numpy as np
import cv2
import json
import os
import sys
import traceback

# Configuration
GRID_RES = 4
SCREEN_RES = (1920, 1080)
SAVE_FILE = "warp_config.json"
VIDEO_FILE = "video.mp4"
IMAGE_FILE = "test.png"

def get_resource_path(filename):
    """ 取得資源檔案的絕對路徑，確保在 EXE 模式下路徑正確 """
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)

class TextRenderer:
    def __init__(self, font_size=28):
        try:
            pygame.font.init()
            self.font = pygame.font.SysFont("Arial", font_size)
            if self.font is None:
                print("Warning: 無法載入 Arial 字體，切換至系統預設字體")
                self.font = pygame.font.SysFont(None, font_size)
        except Exception as e:
            print(f"TextRenderer 初始化失敗: {e}")

    def draw(self, text, x, y):
        try:
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
        except Exception as e:
            print(f"文字渲染出錯: {e}")

class Warper:
    def __init__(self):
        print(f"正在初始化 Warper...")
        self.texid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texid)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        config_path = get_resource_path(SAVE_FILE)
        print(f"檢查設定檔: {config_path}")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                    self.mesh_x, self.mesh_y = np.array(data["x"]), np.array(data["y"])
                print("成功載入現有設定檔")
            except Exception as e:
                print(f"讀取設定檔失敗: {e}，改用預設網格")
                self.reset_mesh()
        else:
            print("設定檔不存在，建立預設網格")
            self.reset_mesh()
        
        self.tex_x, self.tex_y = np.meshgrid(np.linspace(0.0, 1.0, GRID_RES), np.linspace(0.0, 1.0, GRID_RES))
        self.selected_node = None
        self.symmetry = True
        self.mode = "IMAGE" 
        self.cap = None
        self.load_image(get_resource_path(IMAGE_FILE))

    def reset_mesh(self):
        x, y = np.linspace(-1.0, 1.0, GRID_RES), np.linspace(-1.0, 1.0, GRID_RES)
        self.mesh_x, self.mesh_y = np.meshgrid(x, y)

    def load_image(self, path):
        print(f"載入圖片: {path}")
        if os.path.exists(path):
            img = cv2.imread(path)
            if img is None:
                print("Error: OpenCV 無法讀取圖片數據")
                img = np.zeros((1080,1920,3), np.uint8)
        else:
            print("Warning: 找不到圖片，使用黑色背景")
            img = np.zeros((1080,1920,3), np.uint8)
        
        img = cv2.flip(img, 0)
        h, w = img.shape[:2]
        data = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).tobytes()
        glBindTexture(GL_TEXTURE_2D, self.texid)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1) # 增加對齊相容性
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, data)

    def toggle_mode(self):
        if self.mode == "IMAGE":
            v_path = get_resource_path(VIDEO_FILE)
            print(f"切換至影片模式: {v_path}")
            self.cap = cv2.VideoCapture(v_path)
            if self.cap.isOpened():
                self.mode = "VIDEO"
                print("影片開啟成功")
            else:
                print("Error: 無法開啟影片檔案")
        else:
            if self.cap: self.cap.release()
            self.mode = "IMAGE"
            print("切換至圖片模式")
            self.load_image(get_resource_path(IMAGE_FILE))

    def update_video_frame(self):
        if self.mode == "VIDEO" and self.cap:
            ret, frame = self.cap.read()
            if not ret:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 0)
                h, w = frame.shape[:2]
                data = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).tobytes()
                glBindTexture(GL_TEXTURE_2D, self.texid)
                glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, data)

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
            glDisable(GL_TEXTURE_2D); glPointSize(15); glBegin(GL_POINTS)
            for i in range(GRID_RES):
                for j in range(GRID_RES):
                    if self.symmetry and j >= GRID_RES // 2: glColor3f(0, 1, 1)
                    else: glColor3f(1, 0, 0)
                    glVertex2f(self.mesh_x[i, j], self.mesh_y[i, j])
            glEnd(); glColor3f(1, 1, 1)

def main():
    print("--- 程式啟動 ---")
    try:
        pygame.init()
        print(f"嘗試建立視窗: {SCREEN_RES}")
        # 建議第一次測試先拿掉 FULLSCREEN，若成功再手動加上
        pygame.display.set_mode(SCREEN_RES, DOUBLEBUF | OPENGL | FULLSCREEN)
        
        warper = Warper() 
        text_renderer = TextRenderer(28)
        clock = pygame.time.Clock()
        show_ui = True
        running = True

        print("進入主迴圈...")
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                m_pos = pygame.mouse.get_pos()
                gx, gy = (m_pos[0]/SCREEN_RES[0])*2-1, (1-m_pos[1]/SCREEN_RES[1])*2-1

                if event.type == MOUSEBUTTONDOWN and warper.mode == "IMAGE":
                    dists = np.sqrt((warper.mesh_x - gx)**2 + (warper.mesh_y - gy)**2)
                    idx = np.unravel_index(np.argmin(dists), dists.shape)
                    if dists[idx] < 0.1: warper.selected_node = idx
                if event.type == MOUSEBUTTONUP: warper.selected_node = None
                
                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE: running = False
                    if event.key == K_p: warper.toggle_mode()
                    if event.key == K_s: 
                        s_path = get_resource_path(SAVE_FILE)
                        with open(s_path, "w") as f: 
                            json.dump({"x": warper.mesh_x.tolist(), "y": warper.mesh_y.tolist()}, f)
                        print(f"設定已儲存至: {s_path}")
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
                y_base = SCREEN_RES[1] - 220
                # 確保每一行結尾都有正確的右括號 )
                text_renderer.draw(f"CALIBRATION MODE", 40, y_base)
                text_renderer.draw(f"[P] Start Video Playback", 40, y_base + 35)
                text_renderer.draw(f"[S] Save Config", 40, y_base + 70)
                text_renderer.draw(f"[Y] Symmetry: {'ON' if warper.symmetry else 'OFF'}", 40, y_base + 105)
                text_renderer.draw(f"[H] Hide UI", 40, y_base + 140)
                text_renderer.draw(f"[Esc] Exit", 40, y_base + 175)
