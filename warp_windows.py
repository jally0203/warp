import pygame
from pygame.locals import *
from OpenGL.GL import *
import numpy as np
import cv2
import json
import os
import sys
import ctypes

# --- 1. Windows DPI 4K 相容性修正 ---
if sys.platform == "win32":
    try:
        # 避免 Windows 縮放導致座標偏移
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass

# --- 2. 基礎設定與解析度偵測 ---
pygame.init()
info = pygame.display.Info()
# 自動抓取目前顯示器解析度
SCREEN_RES = (info.current_w, info.current_h) if info.current_w > 0 else (1366, 768)
GRID_RES = 4
SAVE_FILE = "warp_config.json"
VIDEO_FILE = "video.mp4"
IMAGE_FILE = "test.png"

def get_resource_path(filename):
    """ 確保在 EXE 環境下能讀寫 EXE 旁邊的資源檔與存檔 """
    if getattr(sys, 'frozen', False):
        # 如果是 PyInstaller 封裝後的環境
        base_path = os.path.dirname(sys.executable)
    else:
        # 如果是直接執行 .py
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)

CONFIG_PATH = get_resource_path(SAVE_FILE)
IMAGE_PATH = get_resource_path(IMAGE_FILE)
VIDEO_PATH = get_resource_path(VIDEO_FILE)

print(f"--- 系統啟動 ---")
print(f"偵測解析度: {SCREEN_RES}")
print(f"設定檔路徑: {CONFIG_PATH}")

class TextRenderer:
    def __init__(self, font_size=24):
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

        # 讀取現有設定
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    data = json.load(f)
                    # 使用 .copy() 確保陣列在 Windows 上可寫入，解決拖曳失效
                    self.mesh_x = np.array(data["x"], dtype=np.float32).copy()
                    self.mesh_y = np.array(data["y"], dtype=np.float32).copy()
                print("成功載入現有設定檔")
            except Exception as e:
                print(f"載入失敗: {e}，改用預設網格")
                self.reset_mesh()
        else:
            self.reset_mesh()

        self.tex_x, self.tex_y = np.meshgrid(np.linspace(0.0, 1.0, GRID_RES), np.linspace(0.0, 1.0, GRID_RES))
        self.selected_node = None
        self.symmetry = True
        self.mode = "IMAGE"
        self.cap = None
        self.load_image(IMAGE_PATH)

    def reset_mesh(self):
        x, y = np.linspace(-1.0, 1.0, GRID_RES), np.linspace(-1.0, 1.0, GRID_RES)
        self.mesh_x, self.mesh_y = np.meshgrid(x, y)

    def load_image(self, path):
        img = cv2.imread(path)
        if img is None:
            print(f"錯誤：找不到圖片 {path}，使用黑色背景")
            img = np.zeros((SCREEN_RES[1], SCREEN_RES[0], 3), np.uint8)
        img = cv2.flip(img, 0)
        h, w = img.shape[:2]
        data = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).tobytes()
        glBindTexture(GL_TEXTURE_2D, self.texid)
        # 設定對齊為 1，避免解析度寬度非 4 倍數時崩潰 (如 1366)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, data)

    def toggle_mode(self):
        if self.mode == "IMAGE":
            self.cap = cv2.VideoCapture(VIDEO_PATH)
            if self.cap.isOpened():
                self.mode = "VIDEO"
                print("切換至影片模式")
            else:
                print("錯誤：無法開啟影片檔")
        else:
            if self.cap: self.cap.release()
            self.mode = "IMAGE"
            print("切換至圖片模式")
            self.load_image(IMAGE_PATH)

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
            glDisable(GL_TEXTURE_2D)
            glPointSize(15)
            glBegin(GL_POINTS)
            for i in range(GRID_RES):
                for j in range(GRID_RES):
                    if self.symmetry and j >= GRID_RES // 2: glColor3f(0, 1, 1)
                    else: glColor3f(1, 0, 0)
                    glVertex2f(self.mesh_x[i, j], self.mesh_y[i, j])
            glEnd()
            glColor3f(1, 1, 1)

def main():
    # 建立全螢幕視窗
    pygame.display.set_mode(SCREEN_RES, DOUBLEBUF | OPENGL | FULLSCREEN)
    
    warper = Warper()
    text_renderer = TextRenderer(28)
    clock = pygame.time.Clock()
    show_ui = True
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == QUIT: running = False
            
            # 使用動態 SCREEN_RES 計算座標，修復拖曳偏移
            m_pos = pygame.mouse.get_pos()
            gx = (m_pos[0] / SCREEN_RES[0]) * 2 - 1
            gy = (1 - m_pos[1] / SCREEN_RES[1]) * 2 - 1

            if event.type == MOUSEBUTTONDOWN and warper.mode == "IMAGE":
                dists = np.sqrt((warper.mesh_x - gx)**2 + (warper.mesh_y - gy)**2)
                idx = np.unravel_index(np.argmin(dists), dists.shape)
                if dists[idx] < 0.15: # 稍微放大判定範圍，適應高解析度
                    warper.selected_node = idx
            
            if event.type == MOUSEBUTTONUP:
                warper.selected_node = None
            
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE: running = False
                if event.key == K_p: warper.toggle_mode()
                if event.key == K_s:
                    with open(CONFIG_PATH, "w") as f:
                        json.dump({"x": warper.mesh_x.tolist(), "y": warper.mesh_y.tolist()}, f)
                    print(f"已儲存至: {CONFIG_PATH}")
                if event.key == K_y: warper.symmetry = not warper.symmetry
                if event.key == K_h: show_ui = not show_ui

        if warper.mode == "VIDEO":
            warper.update_video_frame()
        elif warper.selected_node:
            warper.mesh_x[warper.selected_node], warper.mesh_y[warper.selected_node] = gx, gy
            if warper.symmetry:
                r, c = warper.selected_node
                tc = (GRID_RES - 1) - c
                if tc != c:
                    warper.mesh_x[r, tc], warper.mesh_y[r, tc] = -gx, gy

        warper.draw(show_ui)
        
        if show_ui and warper.mode == "IMAGE":
            y_base = SCREEN_RES[1] - 220
            text_renderer.draw("WARP CALIBRATION MODE", 40, y_base)
            text_renderer.draw("[P] Video/Image Toggle", 40, y_base + 35)
            text_renderer.draw("[S] Save Config", 40, y_base + 70)
            text_renderer.draw(f"[Y] Symmetry: {'ON' if warper.symmetry else 'OFF'}", 40, y_base + 105)
            text_renderer.draw("[H] Hide UI", 40, y_base + 140)
            text_renderer.draw("[Esc] Exit", 40, y_base + 175)

        pygame.display.flip()
        clock.tick(60)

    if warper.cap: warper.cap.release()
    pygame.quit()

if __name__ == "__main__":
    main()
