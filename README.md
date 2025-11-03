# AI_translator
这是一个基于 Python 的桌面应用程序，旨在通过 AI 模型快速翻译屏幕上的文本。它通过全局热键启动截图选择，并将翻译结果显示在一个可拖动、可调整大小的透明窗口中。

## 🚀 功能特性

*   **全局热键支持:** 快速启动截图和翻译流程。
*   **自定义选区:** 精确选择需要翻译的屏幕区域。
*   **AI 驱动:** 利用强大的视觉语言模型进行高精度翻译。
*   **透明结果窗口:** 翻译结果以浮动窗口形式显示，支持拖动和调整大小。
*   **Markdown 支持:** 结果窗口支持显示 Markdown 格式的文本。
*   **配置灵活:** 可通过 JSON 文件配置 API 密钥、模型、热键和窗口样式。

## 🛠️ 环境要求

1.  **Python 3.x:** 确保您的系统安装了 Python 并已添加到 PATH。
2.  **Windows 系统:** 本程序使用了 `ctypes.windll.user32` 和 `ImageGrab`，主要针对 Windows 平台设计。

## 📦 安装与启动

1.  **克隆或下载项目文件。**
2.  **一键启动:**
    运行根目录下的 [`一键启动.bat`](一键启动.bat) 文件。该脚本将自动检查 Python 环境，安装所有依赖（来自 [`requirements.txt`](requirements.txt)），并启动程序。

    ```bash
    # 一键启动.bat 执行的步骤:
    python --version # 检查 Python
    pip install -r requirements.txt # 安装依赖
    python translator_app.py # 启动应用
    ```

## ⚙️ 配置

在启动程序之前，您必须编辑 [`translator_config.json`](translator_config.json) 文件，配置您的 AI API 密钥和 URL。

| 字段 | 描述 | 默认值 (示例) |
| :--- | :--- | :--- |
| `api_url` | AI 模型的 API 地址。 | `"https://you_api_url/v1/chat/completions"` |
| `api_key` | 您的 API 密钥。 | `"you_api_key"` |
| `model_name` | 使用的 AI 模型名称。(需要支持多模态） | `"gemini-2.5-flash"` |
| `system_prompt` | 给 AI 的指令，用于指导翻译行为。 | `"请将图片中的所有文本翻译成简体中文。你只需要返回'翻译后的文本（原文）'，不需要其他任何内容。"` |
| `hotkey_select` | 启动截图选择模式的热键。 | `"<ctrl>+<alt>+q"` |
| `hotkey_capture` | 确认截图并发送翻译的热键。 | `"x"` |
| `result_bg_color` | 结果窗口背景色。 | `"#FFFFFF"` |
| `result_font_size` | 结果窗口字体大小。 | `14` |
| `result_width` | 结果窗口默认宽度。 | `400` |
| `result_height` | 结果窗口默认高度。 | `200` |

## 💡 使用方法

1.  运行 [`一键启动.bat`](一键启动.bat) 启动程序。控制台窗口将显示程序已启动。
2.  **启动选区:** 按下配置的 `hotkey_select` (默认: `<ctrl>+<alt>+q`)。屏幕将变暗，进入选区模式。
3.  **选择区域:** 使用鼠标拖拽出您想要翻译的区域。
4.  **确认翻译:** 选区设置完成后，按下配置的 `hotkey_capture` (默认: `x`)。程序将截图并发送给 AI 进行翻译。
5.  **查看结果:** 翻译结果将显示在一个浮动的透明窗口中。您可以拖动或调整该窗口的大小。
6.  **关闭结果窗口:** 点击结果窗口右上角的 `X` 按钮。窗口位置和大小将被自动保存到 [`translator_config.json`](translator_config.json) 中。
7.  **退出程序:** 关闭启动程序的控制台窗口即可。

## 依赖列表

本程序依赖以下 Python 库（详见 [`requirements.txt`](requirements.txt)）：

*   `requests`
*   `Pillow`
*   `pynput`
*   `markdown`
*   `tkhtmlview`
