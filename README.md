# 🀄️ Qingque Auto (青雀自动机)

> **“忙里偷闲，讲究的就是「偷」呀~” —— 青雀**

专为《崩坏：星穹铁道》角色 **青雀 (Qingque)** 在“货币战争”模式中打造的自动化辅助工具。

本工具通过图像识别技术，自动执行“狂按战技 (E) 直到触发暗杠（四张同色牌），然后释放强化普攻 (Q)”的操作。解放双手，让摸鱼变得更轻松。

## ✨ 功能特点 (Features)

  * **🎯 智能识别**：利用 OpenCV 模板匹配，精准识别 E 技能是否锁定（即“暗杠”状态）。
  * **🚀 极速响应**：动态计算游戏窗口坐标，仅锁定右下角极小区域进行扫描，大幅降低 CPU 占用并提升响应速度。
  * **🖼️ 窗口锁定**：自动寻找并锁定《崩坏：星穹铁道》游戏窗口，支持窗口模式和全屏模式。
  * **🖥️ 图形界面**：提供直观的 GUI 悬浮窗，实时显示抽牌次数和当前状态。
  * **🛡️ 自动提权**：构建版本自带管理员权限请求，确保在游戏内按键模拟生效。
  * **⌨️ 便捷热键**：
      * `F8`: 暂停 / 继续
      * `ESC`: 退出程序

## 📦 下载与使用 (For Users)

### 1\. 获取软件

前往本项目的 [Release](https://github.com/t0saki/HSR-Qingque-Auto/releases) 页面下载最新的 `QingqueAuto.exe`。

> **注意**：该程序包含自动化按键功能，杀毒软件可能会误报，请添加信任或暂时关闭。

### 2\. 运行

1.  确保游戏《崩坏：星穹铁道》已启动，且使用16:9分辨率，否则需要修改检测区域参数。如果您对代码较为熟悉，可以参考之后的开发说明进行调整。
2.  右键 `QingqueAuto.exe` -\> **以管理员身份运行** (通常双击即可，程序已强制请求权限)。
      * *为什么需要管理员权限？* 游戏通常以高权限运行，普通权限的脚本无法向游戏发送按键指令。
3.  看到悬浮窗出现后，进入战斗，轮到青雀回合时，按 **`F8`** 开始自动抽牌。

### 3\. 关键设置

程序内置了一张 `e_disabled.jpg`（E技能不可用/暗杠时的图标）。

  * **如果脚本一直按 E 不停下**：说明图像识别匹配失败（分辨率或渲染差异）。
  * **解决方法**：
    1.  在游戏中截图（全屏）。
    2.  截取右下角 E 技能图标上 **红色的禁止符号** 或 **灰色的状态**。
    3.  将其保存为 `e_disabled.jpg` 并放在 exe 同级目录下（程序会优先读取外部图片）。

## 🛠️ 开发与源码运行 (For Developers)

如果您想修改源码或自行构建，请按照以下步骤操作。

### 目录结构

```text
.
├── .github/workflows/build.yml  # GitHub Actions 自动构建脚本
├── e_disabled.jpg               # 模板图片（资源文件）
├── icon.ico                     # 图标文件
├── qingque_auto.py              # 主程序源码
├── requirements.txt             # 依赖列表
└── README.md                    # 说明文档
```

### 环境准备

确保安装 Python 3.10+。

```bash
# 1. 克隆仓库
git clone https://github.com/t0saki/HSR-Qingque-Auto.git
cd HSR-Qingque-Auto

# 2. 安装依赖
pip install -r requirements.txt
```

### 运行代码

请注意运行需要管理员权限。如果您使用较新的 Windows 版本，可以直接加`sudo`前缀，否则请先使用管理员权限运行Shell。

```bash
python qingque_auto.py
```

### 本地打包 (Build EXE)

如果不想使用 GitHub Actions，可以在本地打包：

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --clean --uac-admin --windowed --icon "icon.ico" --add-data "e_disabled.jpg;." --add-data "icon.ico;." --name "QingqueAuto" qingque_auto.py
```

  * `--uac-admin`: 申请管理员权限。
  * `--windowed`: 隐藏黑色命令行窗口（如果使用 GUI 版本）。
  * `--add-data`: 将图片资源打包进 exe。

## ⚙️ 配置说明 (Configuration)

在 `qingque_auto.py` 顶部可以调整参数：

```python
SKILL_KEY = 'e'      # 战技按键
ATTACK_KEY = 'q'     # 强化普攻按键
CONFIDENCE = 0.8     # 图像识别相似度阈值 (0.6 - 0.9)
```

## ⚠️ 免责声明 (Disclaimer)

1.  **封号风险**：本工具属于脚本辅助/宏类软件。虽然它基于图像识别（非内存注入），难以被反作弊系统直接检测，但**米哈游（miHoYo）用户协议严禁使用第三方辅助软件**。
2.  **使用建议**：建议仅在“模拟宇宙”等非竞争性、重复性高的场景下，且**人在电脑前监控**的情况下使用。
3.  **责任**：本软件仅供学习交流 Python 图像识别与自动化技术使用。开发者不对因使用本软件导致的账号封禁、数据丢失或其他损失承担任何责任。

-----

**Enjoy your Gacha\! 🎲**
