@echo off
echo 检查 Python 环境...

:: 检查 Python 是否在 PATH 中
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到 Python。请确保 Python 已安装并添加到系统 PATH 中。
    pause
    exit /b 1
)

echo 安装依赖...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo 错误: 依赖安装失败。请检查网络连接或权限。
    pause
    exit /b 1
)

echo 依赖安装成功。正在启动翻译工具...
python translator_app.py

pause