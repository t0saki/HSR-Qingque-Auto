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


def resource_path(relative_path):
    """ 获取资源绝对路径，兼容 Dev 和 PyInstaller 打包后的环境 """
    try:
        # PyInstaller 创建临时文件夹并将路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# ================= 配置区域 =================
# TEMPLATE_IMAGE = 'e_disabled.jpg'
TEMPLATE_IMAGE = resource_path('e_disabled.jpg')
ICON_PATH = resource_path('icon.ico')
SKILL_KEY = 'e'
ATTACK_KEY = 'q'
CONFIDENCE = 0.8
# ===========================================


class QingqueBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("青雀自动机")
        self.root.geometry("400x400")
        self.root.attributes('-topmost', True)  # 窗口置顶

        try:
            if os.path.exists(ICON_PATH):
                self.root.iconbitmap(ICON_PATH)
        except Exception as e:
            print(f"加载图标失败: {e}")

        # 状态变量
        self.is_running = False
        self.is_paused = False
        self.skill_count = 0  # 记录当前轮次E按了多少次
        self.game_region = None
        self.stop_event = threading.Event()

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

        self.log("程序已启动，请确保游戏在后台运行。")
        self.log("按 'F8' 键或点击按钮开始。")

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

    def toggle_script(self):
        if not self.is_running:
            # === 启动 ===
            if not os.path.exists(TEMPLATE_IMAGE):
                self.log(f"错误: 找不到 {TEMPLATE_IMAGE}")
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

            # 计算区域
            self.game_region = self.get_game_region(window)
            self.log(f"已锁定窗口，区域: {self.game_region}")

            self.is_running = True
            self.is_paused = False
            self.stop_event.clear()
            self.btn_start.config(text="暂停 (F8)")
            self.update_status("运行中", "green", "正在监控...")

            # 开启后台线程
            self.thread = threading.Thread(
                target=self.automation_loop, daemon=True)
            self.thread.start()

        else:
            # === 暂停/继续 ===
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.btn_start.config(text="继续 (F8)")
                self.update_status("已暂停", "orange", "等待指令")
                self.log("脚本已暂停")
            else:
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
        # 使用你之前觉得不错的参数
        region_left = int(window.left + window.width * 0.89)
        region_top = int(window.top + window.height * 0.70)
        region_width = int(window.width * 0.1)
        region_height = int(window.height * 0.15)
        return (region_left, region_top, region_width, region_height)

    def automation_loop(self):
        """核心自动化逻辑，在单独线程运行"""
        self.skill_count = 0

        while not self.stop_event.is_set():
            if not self.is_running:
                break

            if self.is_paused:
                time.sleep(0.2)
                continue

            try:
                # 识别图像
                location = pyautogui.locateOnScreen(
                    TEMPLATE_IMAGE,
                    confidence=CONFIDENCE,
                    grayscale=True,
                    region=self.game_region
                )

                if location:
                    # === 暗杠 (E不可用) ===
                    # 只有当之前是在抽牌状态，或者这是第一次检测到时，才记录日志
                    if self.skill_count > 0:
                        self.root.after(
                            0, self.log, f"暗杠达成！(累计E了 {self.skill_count} 次)")
                    else:
                        self.root.after(0, self.log, "检测到暗杠，释放 Q")

                    self.root.after(0, self.update_status,
                                    "释放攻击", "blue", "Q 键已按下")

                    pyautogui.press(ATTACK_KEY)

                    self.skill_count = 0  # 重置计数
                    time.sleep(2.5)  # 等待动画

                    # 恢复状态显示
                    self.root.after(0, self.update_status,
                                    "运行中", "green", "等待下一轮...")

                else:
                    # === 抽牌 (E可用) ===
                    self.skill_count += 1

                    # 只更新状态栏文字，不写日志，保持日志区干净
                    info_text = f"正在极速抽牌... (已按 {self.skill_count} 次)"
                    self.root.after(0, self.update_status,
                                    "抽牌中", "purple", info_text)

                    pyautogui.press(SKILL_KEY)
                    # 极速模式，微小延迟
                    time.sleep(0.05)

            except pyautogui.ImageNotFoundException:
                # 同上，没找到图也当作可以抽牌
                self.skill_count += 1
                info_text = f"正在极速抽牌... (已按 {self.skill_count} 次)"
                self.root.after(0, self.update_status,
                                "抽牌中", "purple", info_text)
                pyautogui.press(SKILL_KEY)
                time.sleep(0.05)

            except Exception as e:
                self.root.after(0, self.log, f"错误: {e}")
                time.sleep(1)


if __name__ == "__main__":
    # 创建主窗口
    root = tk.Tk()
    app = QingqueBotGUI(root)

    # 处理关闭窗口事件
    root.protocol("WM_DELETE_WINDOW", app.quit_app)
    root.mainloop()
