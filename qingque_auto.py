import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import pyautogui
import time
import keyboard
import os
import pygetwindow as gw
from datetime import datetime
import sys
from PIL import Image, ImageTk
import cv2
import numpy as np


def resource_path(relative_path):
    """ 获取资源绝对路径，兼容 Dev 和 PyInstaller 打包后的环境 """
    try:
        # PyInstaller 创建临时文件夹并将路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# ================= 配置区域 =================
TEMPLATE_IMAGE_PATH = resource_path('e_disabled.jpg')
ICON_PATH = resource_path('icon.ico')
SKILL_KEY = 'e'
ATTACK_KEY = 'q'
# 默认匹配阈值 (现在作为初始值)
DEFAULT_MATCH_THRESHOLD = 0.5
# 基准分辨率高度
BASE_RESOLUTION_HEIGHT = 2160
# ===========================================


class QingqueBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("青雀自动机")
        self.root.geometry("420x500")  # 稍微加高一点窗口以容纳新控件
        self.root.attributes('-topmost', True)

        try:
            if os.path.exists(ICON_PATH):
                self.root.iconbitmap(ICON_PATH)
        except Exception as e:
            print(f"加载图标失败: {e}")

        # === 状态变量 ===
        self.is_running = False
        self.is_paused = False
        self.stop_event = threading.Event()

        # === 新增：阈值控制变量 ===
        # 使用 tkinter 的 DoubleVar 绑定 UI 控件
        self.match_threshold_var = tk.DoubleVar(value=DEFAULT_MATCH_THRESHOLD)

        # 游戏窗口对象 (用于重获焦点)
        self.target_window = None
        self.game_region = None

        # === CV 相关变量 ===
        self.template_cv = None  # OpenCV 格式的模板图片
        self.base_scale_ratio = 1.0  # 基准缩放比例

        # === 按键控制 ===
        self.skill_count = 0
        self.start_time = None
        self.spam_enabled = False

        # === 界面布局 ===
        self.setup_ui()

    def setup_ui(self):
        # 1. 顶部状态栏
        self.status_frame = tk.Frame(self.root, pady=5)
        self.status_frame.pack(fill=tk.X)

        self.lbl_status = tk.Label(
            self.status_frame, text="就绪", font=("微软雅黑", 14, "bold"), fg="gray")
        self.lbl_status.pack()

        self.lbl_info = tk.Label(
            self.status_frame, text="等待启动...", font=("微软雅黑", 10))
        self.lbl_info.pack()

        # --- 分割线 ---
        ttk.Separator(self.root, orient='horizontal').pack(fill='x', pady=5)

        # 2. === 新增：设置区域 (阈值滑动条) ===
        self.settings_frame = tk.Frame(self.root, pady=5)
        self.settings_frame.pack(fill=tk.X, padx=15)

        # 左侧标签
        tk.Label(self.settings_frame, text="识别阈值:",
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)

        # 滑动条
        self.scale_threshold = tk.Scale(
            self.settings_frame,
            from_=0.1, to=1.0,       # 范围
            resolution=0.05,         # 步进
            orient=tk.HORIZONTAL,    # 横向
            variable=self.match_threshold_var,  # 绑定变量
            length=200,
            showvalue=True           # 显示数值
        )
        self.scale_threshold.pack(
            side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        # 提示文本
        tk.Label(self.root, text="(越低越容易识别，越高越严格)",
                 font=("微软雅黑", 8), fg="gray").pack()

        # --- 分割线 ---
        ttk.Separator(self.root, orient='horizontal').pack(fill='x', pady=10)

        # 3. 控制按钮
        self.btn_frame = tk.Frame(self.root, pady=5)
        self.btn_frame.pack()

        self.btn_start = ttk.Button(
            self.btn_frame, text="启动 (F8)", command=self.toggle_script)
        self.btn_start.pack(side=tk.LEFT, padx=5)

        self.btn_quit = ttk.Button(
            self.btn_frame, text="退出", command=self.quit_app)
        self.btn_quit.pack(side=tk.LEFT, padx=5)

        # 4. 日志显示区域
        self.log_area = scrolledtext.ScrolledText(
            self.root, height=10, state='disabled', font=("Consolas", 9))
        self.log_area.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        # 5. 注册全局热键
        keyboard.add_hotkey('f8', self.toggle_script_safe)

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {message}\n"
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, full_msg)
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def update_status(self, status_text, color="black", info_text=""):
        """更新顶部状态标签 (线程安全)"""
        self.lbl_status.config(text=status_text, fg=color)
        if info_text:
            self.lbl_info.config(text=info_text)

    def toggle_script_safe(self):
        """热键调用的线程安全包装"""
        self.root.after(0, self.toggle_script)

    def prepare_cv_template(self, window_height):
        """ 核心：准备 OpenCV 使用的模板，并计算基础缩放比 """
        try:
            if not os.path.exists(TEMPLATE_IMAGE_PATH):
                self.log(f"错误: 找不到图片 {TEMPLATE_IMAGE_PATH}")
                return False

            # 1. 读取图片 (OpenCV 默认读取为 BGR)
            # cv2.imdecode 可以处理中文路径
            img_data = np.fromfile(TEMPLATE_IMAGE_PATH, dtype=np.uint8)
            original_img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)

            if original_img is None:
                self.log("错误: 图片文件损坏或无法读取")
                return False

            # 2. 转为灰度图 (匹配形状和明暗，忽略色相)
            self.template_cv = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)

            # 3. 计算基准缩放比例
            self.base_scale_ratio = window_height / BASE_RESOLUTION_HEIGHT
            self.log(f"基准缩放比例: {self.base_scale_ratio:.2f}")

            return True
        except Exception as e:
            self.log(f"CV 初始化失败: {e}")
            return False

    def find_game_window(self):
        titles = ["崩坏：星穹铁道", "Honkai: Star Rail"]
        for title in titles:
            windows = gw.getWindowsWithTitle(title)
            if windows:
                return windows[0]
        return None

    def get_game_region(self, window):
        # 保持原有的区域计算逻辑
        region_left = int(window.left + window.width * 0.89)
        region_top = int(window.top + window.height * 0.70)
        region_width = int(window.width * 0.1)
        region_height = int(window.height * 0.15)
        return (region_left, region_top, region_width, region_height)

    def toggle_script(self):
        if not self.is_running:
            # === 启动 ===
            if not os.path.exists(TEMPLATE_IMAGE_PATH):
                self.log(f"错误: 找不到 {TEMPLATE_IMAGE_PATH}")
                return

            # 寻找窗口
            window = self.find_game_window()
            if not window:
                self.log("错误: 未找到《崩坏：星穹铁道》窗口")
                return

            try:
                if not window.isActive:
                    window.activate()
            except:
                pass

            time.sleep(0.2)  # 等待窗口激活

            self.target_window = window
            self.game_region = self.get_game_region(window)

            # 准备 OpenCV 数据
            if not self.prepare_cv_template(window.height):
                return

            self.is_running = True
            self.is_paused = False
            self.stop_event.clear()
            self.spam_enabled = True

            self.btn_start.config(text="暂停 (F8)")
            self.update_status("运行中", "green", "正在监控...")
            self.log(f"监控区域: {self.game_region}")
            self.log(f"当前阈值: {self.match_threshold_var.get()}")

            # === 启动双线程 ===
            # 线程1: 视觉识别 (大脑)
            self.vision_thread = threading.Thread(
                target=self.vision_loop, daemon=True)
            self.vision_thread.start()

            # 线程2: 按键输出 (手速)
            self.spam_thread = threading.Thread(
                target=self.spam_loop, daemon=True)
            self.spam_thread.start()

        else:
            # === 暂停/继续 ===
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.spam_enabled = False
                self.btn_start.config(text="继续 (F8)")
                self.update_status("已暂停", "orange", "等待指令")
                self.log("脚本已暂停")
            else:
                self.activate_window()
                self.spam_enabled = True
                self.btn_start.config(text="暂停 (F8)")
                self.update_status("运行中", "green", "继续监控...")
                self.log("脚本继续运行")

    def activate_window(self):
        if self.target_window:
            try:
                if not self.target_window.isActive:
                    self.target_window.activate()
            except:
                pass

    # =================================================================
    # 核心改进：OpenCV 视觉识别算法
    # =================================================================
    def match_template_robust(self, screen_img_gray):
        """
        多尺度匹配算法：
        即使窗口大小有细微变化（比如分辨率计算差了几像素），
        通过在 [0.9x, 1.0x, 1.1x] 范围内尝试不同大小的模板，也能精准识别。
        """
        found = False
        max_confidence = 0

        # 获取当前界面上设定的阈值
        current_threshold = self.match_threshold_var.get()

        # 定义搜索的缩放范围
        scales = np.linspace(0.9 * self.base_scale_ratio,
                             1.1 * self.base_scale_ratio, 3)

        if abs(self.base_scale_ratio - 1.0) < 0.05:
            scales = [1.0, 0.9, 1.1]

        h, w = self.template_cv.shape[:2]

        for scale in scales:
            # 1. 调整模板大小
            resized_w = int(w * scale)
            resized_h = int(h * scale)

            # 避免尺寸过小报错
            if resized_w < 10 or resized_h < 10:
                continue
            if resized_w > screen_img_gray.shape[1] or resized_h > screen_img_gray.shape[0]:
                continue

            resized_template = cv2.resize(
                self.template_cv, (resized_w, resized_h))

            # 2. 模板匹配 (TM_CCOEFF_NORMED 标准化相关系数匹配，结果 -1 到 1)
            res = cv2.matchTemplate(
                screen_img_gray, resized_template, cv2.TM_CCOEFF_NORMED)

            # 3. 获取最大匹配值
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

            if max_val > max_confidence:
                max_confidence = max_val

            # 使用变量 current_threshold 而不是全局常量
            if max_val >= current_threshold:
                found = True
                break

        return found, max_confidence

    def vision_loop(self):
        self.skill_count = 0

        while not self.stop_event.is_set():
            if not self.is_running:
                break

            if self.is_paused:
                time.sleep(0.5)
                continue

            try:
                # 1. 截取屏幕 (PIL Image)
                # region=(left, top, width, height)
                screenshot = pyautogui.screenshot(region=self.game_region)

                # 2. PIL -> OpenCV (Numpy array) -> Grayscale
                # pyautogui 截图是 RGB，OpenCV 需要 BGR 或 Gray
                screen_np = np.array(screenshot)
                screen_gray = cv2.cvtColor(screen_np, cv2.COLOR_RGB2GRAY)

                # 3. 运行多尺度匹配算法
                is_found, confidence = self.match_template_robust(screen_gray)

                # # 调试用：如果置信度较高但没触发，可以打印看看
                # if confidence > 0.5: print(f"Confidence: {confidence:.2f}")

                if is_found:
                    # === 发现暗杠图标 ===
                    self.spam_enabled = False  # 停手

                    if self.skill_count > 0:
                        final_duration = time.time() - self.start_time if self.start_time else 0
                        self.root.after(
                            0, self.log, f"暗杠达成！({final_duration:.1f} 秒)")
                        self.start_time = None
                    else:
                        self.root.after(0, self.log, "检测到暗杠状态")

                    self.root.after(0, self.update_status, "释放攻击",
                                    "blue", f"置信度: {confidence:.2f}")

                    pyautogui.press(ATTACK_KEY)
                    self.skill_count = 0

                    # 简单的防抖动延迟
                    time.sleep(2.5)

                    if self.is_running and not self.is_paused:
                        self.root.after(0, self.update_status, "运行中", "green")
                        self.spam_enabled = True
                else:
                    # === 未发现图标 ===
                    if not self.is_paused:
                        self.spam_enabled = True

                time.sleep(0.05)

            except Exception as e:
                print(f"Vision Error: {e}")
                time.sleep(1)

    # =================================================================
    # 线程 2: 按键循环
    # =================================================================
    def spam_loop(self):
        while not self.stop_event.is_set():
            if not self.is_running:
                break

            if not self.is_paused and self.spam_enabled:
                if self.start_time is None:
                    self.start_time = time.time()

                pyautogui.press(SKILL_KEY)
                self.skill_count += 1

                if self.skill_count % 10 == 0:
                    current_duration = time.time() - self.start_time if self.start_time else 0
                    info_text = f"抽牌中... ({int(current_duration)} 秒)"
                    self.root.after(0, self.update_status,
                                    "抽牌中", "purple", info_text)

                time.sleep(0.03)
            else:
                time.sleep(0.1)

    def quit_app(self):
        self.is_running = False
        self.stop_event.set()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = QingqueBotGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.quit_app)
    root.mainloop()
