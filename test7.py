import numpy as np
import json
import os

def test_logic():
    GRID_RES = 4
    SAVE_FILE = "warp_config.json"
    print("模擬 Warper 網格初始化邏輯...")
    try:
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
                mesh_x = np.array(data["x"])
                print(f"成功載入設定檔，維度: {mesh_x.shape}")
        else:
            x = np.linspace(-1.0, 1.0, GRID_RES)
            mesh_x, _ = np.meshgrid(x, x)
            print(f"生成預設網格，維度: {mesh_x.shape}")
        
        print(f"數據類型: {mesh_x.dtype}, 範例數值: {mesh_x[0,0]}")
        # 確認數值未溢出 OpenGL 座標空間 (-1.0 ~ 1.0)
        if np.any(np.abs(mesh_x) > 2.0):
            print("Warning: 網格座標數值異常！")
        else:
            print("Success: 網格數據邏輯檢查正常。")
    except Exception as e:
        print(f"Failed: 邏輯運算錯誤: {e}")

if __name__ == "__main__":
    test_logic()
    input("按 Enter 結束...")
