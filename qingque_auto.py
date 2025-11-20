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
CONFIDENCE = 0.65
# 核心修改：设置你截图时的基准分辨率高度 (4K通常是2160，2K是1440，1080p是1080)
BASE_RESOLUTION_HEIGHT = 2160
# ===========================================


class QingqueBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("青雀自动机")
        self.root.geometry("400x420")
        self.root.attributes('-topmost', True)  # 窗口置顶

        try:
            if os.path.exists(ICON_PATH):
                self.root.iconbitmap(ICON_PATH)
        except Exception as e:
            print(f"加载图标失败: {e}")

        # === 状态变量 ===
        self.is_running = False
        self.is_paused = False
        self.stop_event = threading.Event()

        # 游戏窗口对象 (用于重获焦点)
        self.target_window = None
        self.game_region = None

        # 图像处理
        self.current_template_image = None

        # === 新增：按键控制相关 ===
        self.skill_count = 0
        # 控制是否允许按E的标志位 (线程间共享)
        self.spam_enabled = False

        # === 界面布局 ===

        # 1. 顶部状态栏
        self.status_frame = tk.Frame(root, pady=5)
        self.status_frame.pack(fill=tk.X)

        self.lbl_status = tk.Label(
            self.status_frame, text="就绪", font=("微软雅黑", 14, "bold"), fg="gray")
        self.lbl_status.pack()

        self.lbl_info = tk.Label(
            self.status_frame, text="等待启动...", font=("微软雅黑", 10))
        self.lbl_info.pack()

        # 2. 控制按钮
        self.btn_frame = tk.Frame(root, pady=5)
        self.btn_frame.pack()

        self.btn_start = ttk.Button(
            self.btn_frame, text="启动 (F8)", command=self.toggle_script)
        self.btn_start.pack(side=tk.LEFT, padx=5)

        self.btn_quit = ttk.Button(
            self.btn_frame, text="退出", command=self.quit_app)
        self.btn_quit.pack(side=tk.LEFT, padx=5)

        # 3. 日志显示区域
        self.log_area = scrolledtext.ScrolledText(
            root, height=8, state='disabled', font=("Consolas", 9))
        self.log_area.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        # 4. 注册全局热键
        keyboard.add_hotkey('f8', self.toggle_script_safe)

        self.log("程序已启动。")
        self.log("独立线程按键模式已加载。")

    def log(self, message):
        """向日志框添加信息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {message}\n"

        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, full_msg)
        self.log_area.see(tk.END)  # 自动滚动到底部
        self.log_area.config(state='disabled')

    def update_status(self, status_text, color="black", info_text=""):
        """更新顶部状态标签 (线程安全)"""
        self.lbl_status.config(text=status_text, fg=color)
        if info_text:
            self.lbl_info.config(text=info_text)

    def toggle_script_safe(self):
        """热键调用的线程安全包装"""
        self.root.after(0, self.toggle_script)

    def prepare_template_image(self, window_height):
        """ 核心逻辑：根据窗口高度缩放模板图片 """
        try:
            if not os.path.exists(TEMPLATE_IMAGE_PATH):
                self.log(f"错误: 找不到图片 {TEMPLATE_IMAGE_PATH}")
                return False

            # 加载原始图片
            original_img = Image.open(TEMPLATE_IMAGE_PATH)

            # 计算缩放比例 (当前窗口高度 / 截图时的基准高度)
            scale_ratio = window_height / BASE_RESOLUTION_HEIGHT

            # 只有当比例差异较大时才缩放，否则用原图
            if abs(scale_ratio - 1.0) > 0.05:
                new_width = int(original_img.width * scale_ratio)
                new_height = int(original_img.height * scale_ratio)
                # 使用 LANCZOS 算法进行高质量缩放
                resized_img = original_img.resize(
                    (new_width, new_height), Image.Resampling.LANCZOS)
                self.current_template_image = resized_img
                self.log(f"检测到窗口高度 {window_height}，缩放比例: {scale_ratio:.2f}")
            else:
                self.current_template_image = original_img
                self.log(f"窗口高度 {window_height} 与基准接近，使用原图。")

            return True
        except Exception as e:
            self.log(f"图片处理失败: {e}")
            return False

    def activate_window(self):
        """ 尝试激活游戏窗口 """
        if self.target_window:
            try:
                if not self.target_window.isActive:
                    self.target_window.activate()
            except Exception:
                pass

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

            # 2. 计算区域和图片
            self.game_region = self.get_game_region(self.target_window)
            if not self.prepare_template_image(self.target_window.height):
                return

            self.log(f"已锁定窗口，区域: {self.game_region}")

            self.is_running = True
            self.is_paused = False
            self.stop_event.clear()
            self.spam_enabled = True  # 默认允许按E，直到看到禁止图标

            self.btn_start.config(text="暂停 (F8)")
            self.update_status("运行中", "green", "正在监控...")

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
            # === 暂停/继续逻辑 ===
            self.is_paused = not self.is_paused
            if self.is_paused:
                # 暂停
                self.spam_enabled = False  # 暂停时禁止乱按
                self.btn_start.config(text="继续 (F8)")
                self.update_status("已暂停", "orange", "等待指令")
                self.log("脚本已暂停")
            else:
                # 继续
                self.activate_window()  # === 核心修改：恢复运行时重新激活窗口 ===
                self.spam_enabled = True
                self.btn_start.config(text="暂停 (F8)")
                self.update_status("运行中", "green", "继续监控...")
                self.log("脚本继续运行")

    def quit_app(self):
        self.is_running = False
        self.stop_event.set()
        self.root.quit()

    def find_game_window(self):
        titles = ["崩坏：星穹铁道", "Honkai: Star Rail"]
        for title in titles:
            windows = gw.getWindowsWithTitle(title)
            if windows:
                return windows[0]
        return None

    def get_game_region(self, window):
        region_left = int(window.left + window.width * 0.89)
        region_top = int(window.top + window.height * 0.70)
        region_width = int(window.width * 0.1)
        region_height = int(window.height * 0.15)
        return (region_left, region_top, region_width, region_height)

    # =================================================================
    # 线程 1: 视觉识别循环 (大脑)
    # =================================================================
    def vision_loop(self):
        self.skill_count = 0

        while not self.stop_event.is_set():
            if not self.is_running:
                break

            # 暂停时，视觉线程也稍微休息，降低CPU占用
            if self.is_paused:
                time.sleep(0.5)
                continue

            try:
                # 识别是否存在“E不可用”图标
                location = pyautogui.locateOnScreen(
                    self.current_template_image,
                    confidence=CONFIDENCE,
                    grayscale=True,
                    region=self.game_region
                )

                if location:
                    # === 发现暗杠 ===
                    # 1. 立即停止按E
                    self.spam_enabled = False

                    # 2. 记录日志和操作
                    if self.skill_count > 0:
                        self.root.after(
                            0, self.log, f"暗杠达成！(累计E了 {self.skill_count} 次)")
                    else:
                        self.root.after(0, self.log, "检测到暗杠，释放 Q")

                    self.root.after(0, self.update_status,
                                    "释放攻击", "blue", "Q 键已按下")

                    # 3. 按下 Q
                    pyautogui.press(ATTACK_KEY)
                    self.skill_count = 0

                    # 4. 等待动画 (根据实际情况调整，如果是自动战斗，动画期间按键也无所谓)
                    time.sleep(2.5)

                    # 5. 恢复状态，允许继续按E (如果还在运行)
                    if self.is_running and not self.is_paused:
                        self.root.after(0, self.update_status,
                                        "运行中", "green", "等待下一轮...")
                        self.spam_enabled = True

                else:
                    # === 没找到图标 ===
                    # 只要没暂停，就允许按E
                    # 视觉线程不负责按键，只负责“授权”
                    if not self.is_paused:
                        self.spam_enabled = True

                # 视觉识别不需要太高频，0.1s 检查一次足够
                # 如果识别太快，CPU占用高
                time.sleep(0.1)

            except pyautogui.ImageNotFoundException:
                # 没找到图 = 可以按E
                if not self.is_paused:
                    self.spam_enabled = True
                time.sleep(0.1)
            except Exception as e:
                print(f"Vision Error: {e}")
                time.sleep(1)

    # =================================================================
    # 线程 2: 按键狂暴循环 (手速)
    # =================================================================
    def spam_loop(self):
        """ 单独的线程，只负责狂按 E """
        while not self.stop_event.is_set():
            if not self.is_running:
                break

            # 只有当未暂停，且视觉线程授权(spam_enabled=True)时才按
            if not self.is_paused and self.spam_enabled:
                pyautogui.press(SKILL_KEY)
                self.skill_count += 1

                # 更新UI (为了不卡死界面，每按10次更新一次显示)
                if self.skill_count % 10 == 0:
                    info_text = f"极速抽牌中... ({self.skill_count})"
                    self.root.after(0, self.update_status,
                                    "抽牌中", "purple", info_text)

                # 这里的延迟决定了手速
                # 0.02s ≈ 一秒50次 (理论值)，实际上会被游戏输入队列限制
                # 按过头了也没事，所以可以快一点
                time.sleep(0.02)
            else:
                # 如果不允许按，就休息一会，避免死循环占用CPU
                time.sleep(0.1)


if __name__ == "__main__":
    # 创建主窗口
    root = tk.Tk()
    app = QingqueBotGUI(root)

    # 处理关闭窗口事件
    root.protocol("WM_DELETE_WINDOW", app.quit_app)
    root.mainloop()
