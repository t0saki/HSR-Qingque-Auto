import pyautogui
import time
import keyboard
import os
import pygetwindow as gw

# ================= 配置区域 =================
TEMPLATE_IMAGE = 'e_disabled.jpg'  # 确保图片是 E 键上出现红色禁止符号的样子
SKILL_KEY = 'e'
ATTACK_KEY = 'q'
CONFIDENCE = 0.8  # 如果识别太慢，可以尝试改低一点点比如 0.7，但不建议低于 0.6
# ===========================================

# 全局变量控制状态
running = True
paused = False


def on_pause_toggle():
    global paused
    paused = not paused
    status = "暂停" if paused else "继续"
    print(f"\n[系统] 脚本已{status}...")


def on_exit():
    global running
    running = False
    print("\n[系统] 正在退出...")


def find_game_window():
    titles = ["崩坏：星穹铁道", "Honkai: Star Rail"]
    for title in titles:
        windows = gw.getWindowsWithTitle(title)
        if windows:
            return windows[0]
    return None


def get_game_region(window):
    """
    计算右下角更精准的区域。
    E技能图标通常在右下角的特定位置，没必要扫描整个右下1/4屏幕。
    """
    region_left = int(window.left + window.width * 0.89)
    region_top = int(window.top + window.height * 0.70)
    region_width = int(window.width * 0.1)
    region_height = int(window.height * 0.15)
    return (region_left, region_top, region_width, region_height)


def main():
    global running, paused

    print("=== 青雀自动脚本 (极速响应版) ===")
    print("正在寻找游戏窗口...")
    game_window = find_game_window()

    if not game_window:
        print("错误: 未找到游戏窗口，请启动游戏。")
        return

    # 激活窗口
    try:
        if not game_window.isActive:
            game_window.activate()
    except:
        pass

    # 注册热键 (这是按键灵敏的关键)
    keyboard.add_hotkey('f8', on_pause_toggle)
    keyboard.add_hotkey('esc', on_exit)

    print(f"已锁定窗口: {game_window.title}")
    print("操作说明: 按 'F8' 暂停/继续 | 按 'ESC' 退出")

    # === 性能优化：在循环外计算一次区域 ===
    # 注意：脚本运行期间请勿大幅拖动窗口位置，否则需要重启脚本
    search_region = get_game_region(game_window)
    print(f"搜索区域已锁定: {search_region}")

    last_state = None  # 用于去重日志

    while running:
        if paused:
            time.sleep(0.1)
            continue

        try:
            # region 越小，速度越快
            location = pyautogui.locateOnScreen(
                TEMPLATE_IMAGE,
                confidence=CONFIDENCE,
                grayscale=True,
                region=search_region
            )

            if location:
                # === 发现禁止图标 (暗杠) ===
                print(
                    f"\r[{time.strftime('%H:%M:%S')}] >>> 暗杠达成! 释放强化普攻 (Q) <<<")
                pyautogui.press(ATTACK_KEY)
                last_state = "ATTACK"
                # 攻击动画较长，这里必须睡一会，否则会空按
                time.sleep(2.5)
            else:
                # === 未发现图标 (继续抽) ===
                # 只有当状态改变时才打印，防止刷屏
                # end='' 和 \r 可以让打印在同一行刷新
                if last_state != "SKILL":
                    print(
                        f"\n[{time.strftime('%H:%M:%S')}] 开始抽牌 (E)... ", end="")
                    last_state = "SKILL"

                print(".", end="", flush=True)  # 每次按E打一个点，表示在工作
                pyautogui.press(SKILL_KEY)
                time.sleep(0.05)

        except pyautogui.ImageNotFoundException:
            # 没找到图 = 可以抽牌
            if last_state != "SKILL":
                print(f"\n[{time.strftime('%H:%M:%S')}] 开始极速抽牌 (E)... ", end="")
                last_state = "SKILL"

            print(".", end="", flush=True)
            pyautogui.press(SKILL_KEY)
            time.sleep(0.05)

        except Exception as e:
            print(f"\n发生未知错误: {e}")
            time.sleep(1)


if __name__ == "__main__":
    main()
