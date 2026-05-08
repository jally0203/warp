import pygame
from pygame.locals import *
from OpenGL.GL import *
import numpy as np
import cv2

# -------------------------
# 影片輸入
# -------------------------
cap = cv2.VideoCapture("video.mp4")  # 可換 0 = webcam

# -------------------------
# mesh（簡化：4點 warp）
# -------------------------
# 左上 / 右上 / 右下 / 左下
mesh = np.array([
    [0.0, 0.0],
    [1.0, 0.0],
    [1.0, 1.0],
    [0.0, 1.0],
], dtype=np.float32)

# -------------------------
# OpenGL shader
# -------------------------
VERTEX_SHADER = """
#version 120
attribute vec2 pos;
attribute vec2 texcoord;
varying vec2 v_texcoord;

void main() {
    gl_Position = vec4(pos * 2.0 - 1.0, 0.0, 1.0);
    v_texcoord = texcoord;
}
"""

FRAGMENT_SHADER = """
#version 120
uniform sampler2D tex;
varying vec2 v_texcoord;

void main() {
    gl_FragColor = texture2D(tex, v_texcoord);
}
"""

def compile_shader():
    vs = glCreateShader(GL_VERTEX_SHADER)
    glShaderSource(vs, VERTEX_SHADER)
    glCompileShader(vs)

    fs = glCreateShader(GL_FRAGMENT_SHADER)
    glShaderSource(fs, FRAGMENT_SHADER)
    glCompileShader(fs)

    program = glCreateProgram()
    glAttachShader(program, vs)
    glAttachShader(program, fs)
    glLinkProgram(program)

    return program

# -------------------------
# texture
# -------------------------
def create_texture():
    tex = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex)

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    return tex

def update_texture(tex, frame):
    frame = cv2.flip(frame, 0)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    glBindTexture(GL_TEXTURE_2D, tex)
    glTexImage2D(
        GL_TEXTURE_2D, 0, GL_RGB,
        frame.shape[1], frame.shape[0],
        0, GL_RGB, GL_UNSIGNED_BYTE,
        frame
    )

# -------------------------
# 初始化
# -------------------------
pygame.init()
display = (800, 600)
pygame.display.set_mode(display, DOUBLEBUF | OPENGL)

program = compile_shader()
glUseProgram(program)

tex = create_texture()

# -------------------------
# mesh（兩個三角形）
# -------------------------
vertices = np.array([
    0,0,  0,0,
    1,0,  1,0,
    1,1,  1,1,

    0,0,  0,0,
    1,1,  1,1,
    0,1,  0,1,
], dtype=np.float32)

# -------------------------
# 主迴圈
# -------------------------
running = True
while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    ret, frame = cap.read()
    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        continue

    update_texture(tex, frame)

    glClear(GL_COLOR_BUFFER_BIT)

    # bind texture
    glBindTexture(GL_TEXTURE_2D, tex)

    # 畫 full screen quad
    glBegin(GL_TRIANGLES)

    glTexCoord2f(0,0); glVertex2f(0,0)
    glTexCoord2f(1,0); glVertex2f(1,0)
    glTexCoord2f(1,1); glVertex2f(1,1)

    glTexCoord2f(0,0); glVertex2f(0,0)
    glTexCoord2f(1,1); glVertex2f(1,1)
    glTexCoord2f(0,1); glVertex2f(0,1)

    glEnd()

    pygame.display.flip()
    pygame.time.wait(10)

pygame.quit()
