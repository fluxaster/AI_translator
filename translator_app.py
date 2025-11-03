import tkinter as tk
from PIL import ImageGrab
from pynput import keyboard
import requests
import base64
import io
import threading
import ctypes
import time
import json
import os
import markdown
from tkhtmlview import HTMLLabel # 导入 HTMLLabel

# --- 配置常量 ---
CONFIG_FILE = "translator_config.json"

def load_config():
    """加载配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置失败: {e}. 。")
    return default_config

default_config = {
    "result_window_geometry": None,
    "api_url": "https://you_api_url/v1/chat/completions",
    "api_key": "you_api_key",
    "system_prompt": "请将图片中的所有文本翻译成简体中文。你只需要返回'翻译后的文本（原文）'，不需要其他任何内容。",
    "model_name": "gemini-2.5-flash",
    "request_timeout_seconds": 60,
    "hotkey_select": "<ctrl>+<alt>+q",
    "hotkey_capture": "x",
    "result_bg_color": "#FFFFFF",
    "result_fg_color": "#000000",
    "result_font_family": "宋体",
    "result_font_size": 14,
    "result_width": 400,
    "result_height": 200
}
 
def save_config(config):
    """保存配置"""
    try:
        # 确保使用 UTF-8 编码并禁用 ASCII 转义，以正确保存中文
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"保存配置失败: {e}")

# 确保 DPI 兼容性
try:
    ctypes.windll.user32.SetProcessDPIAware()
except:
    pass

class SelectionWindow:
    """用于创建选择区域的覆盖窗口"""
    def __init__(self, parent_root, app_instance):
        self.app = app_instance
        self.master = parent_root
        
        # 获取屏幕尺寸
        user32 = ctypes.windll.user32
        self.screen_width = user32.GetSystemMetrics(0)
        self.screen_height = user32.GetSystemMetrics(1)
        
        self.selection_tk = tk.Toplevel(self.master)
        self.selection_tk.geometry(f"{self.screen_width}x{self.screen_height}+0+0")
        self.selection_tk.attributes("-alpha", 0.3)
        self.selection_tk.overrideredirect(True)
        self.selection_tk.attributes('-topmost', True) # 确保在最上层
        
        self.canvas = tk.Canvas(self.selection_tk, width=self.screen_width, height=self.screen_height, highlightthickness=0, bg='gray')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        self.selection_tk.bind("<Escape>", self.cancel_selection)
        
        self.start_x = None
        self.start_y = None
        self.rect = None
        
        print("进入截图选择模式... 请用鼠标拖拽出一个区域。")

    def on_mouse_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.rect: self.canvas.delete(self.rect)
        # 使用透明色来标记选区，并设置透明键
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2, fill='white')
        self.selection_tk.attributes("-transparentcolor", "white")

    def on_mouse_drag(self, event):
        cur_x, cur_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_mouse_release(self, event):
        end_x, end_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        x1, y1 = min(self.start_x, end_x), min(self.start_y, end_y)
        x2, y2 = max(self.start_x, end_x), max(self.start_y, end_y)
        
        if x2 - x1 > 5 and y2 - y1 > 5: # 确保选择区域足够大
            self.app.set_selection_box((x1, y1, x2, y2))
            hotkey_capture = self.app.config['hotkey_capture']
            print(f"区域已选择: ({int(x1)}, {int(y1)}) to ({int(x2)}, {int(y2)})。请按 '{hotkey_capture}' 截图翻译。")
        else:
            print("选择区域太小或无效，已取消。")
            self.app.set_selection_box(None)
            
        self.selection_tk.destroy()

    def cancel_selection(self, event=None):
        print("选择已取消。")
        self.app.set_selection_box(None)
        self.selection_tk.destroy()

class TranslationResultWindow:
    """用于固定显示翻译结果的窗口"""
    def __init__(self, parent_root, box, config):
        self.master = parent_root
        self.config = config
        self.result_tk = tk.Toplevel(self.master)
        
        # 允许调整大小和拖动，因此不能使用 overrideredirect(True)
        # 但我们需要移除边框，并实现自定义拖动
        self.result_tk.overrideredirect(True)
        self.result_tk.attributes('-topmost', True)
        self.result_tk.attributes("-alpha", 0.7) # 设置透明度为 70%
        self.result_tk.config(bg=self.config['result_bg_color'])
        
        # 1. 加载或计算几何信息
        geometry = self.config.get("result_window_geometry")
        if geometry:
            self.result_tk.geometry(geometry)
        else:
            # 窗口位置和大小：基于选区位置，使用默认大小
            x1, y1, x2, y2 = box
            
            screen_height = self.result_tk.winfo_screenheight()
            
            # 默认放在选区下方
            x_pos = x1
            y_pos = y2 + 10
            
            # 如果下方空间不足，则放在上方
            if y_pos + self.config['result_height'] > screen_height:
                y_pos = y1 - self.config['result_height'] - 10
                if y_pos < 0: # 如果上方也放不下，则放在屏幕中央
                    y_pos = (screen_height - self.config['result_height']) // 2
                    x_pos = (self.result_tk.winfo_screenwidth() - self.config['result_width']) // 2

            self.result_tk.geometry(f"{self.config['result_width']}x{self.config['result_height']}+{int(x_pos)}+{int(y_pos)}")

        # 2. 创建内容
        # 2. 创建内容 (使用 HTMLLabel 支持 Markdown/HTML)
        # 注意：HTMLLabel 内部处理字体和颜色，但我们可以设置背景色
        self.text_widget = HTMLLabel(self.result_tk,
                                     html="正在等待翻译结果...",
                                     background=self.config['result_bg_color'],
                                     borderwidth=0,
                                     highlightthickness=0)
        self.text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 3. 实现自定义拖动和调整大小
        self.result_tk.bind("<ButtonPress-1>", self.start_move_or_resize)
        self.result_tk.bind("<B1-Motion>", self.do_move_or_resize)
        self.result_tk.bind("<ButtonRelease-1>", self.stop_move_or_resize)
        
        # 4. 添加关闭按钮
        close_button = tk.Button(self.result_tk, text="X", command=self.close, bg='red', fg='white', bd=0, relief=tk.FLAT)
        close_button.place(x=self.result_tk.winfo_width() - 20, y=0, width=20, height=20)
        
        # 确保关闭按钮位置在窗口大小变化时更新
        self.result_tk.bind("<Configure>", lambda e: close_button.place(x=self.result_tk.winfo_width() - 20, y=0, width=20, height=20))
        
        self.resize_mode = None # 'move', 'resize_r', 'resize_b', 'resize_rb'
        self.resize_border = 10 # 调整大小的边框宽度

    def start_move_or_resize(self, event):
        self.x = event.x
        self.y = event.y
        
        w = self.result_tk.winfo_width()
        h = self.result_tk.winfo_height()
        
        # 检查是否在右下角进行调整大小
        if w - self.resize_border < event.x < w and h - self.resize_border < event.y < h:
            self.resize_mode = 'resize_rb'
            self.result_tk.config(cursor="sizing-all")
        # 检查是否在右边缘进行调整大小
        elif w - self.resize_border < event.x < w:
            self.resize_mode = 'resize_r'
            self.result_tk.config(cursor="right_side")
        # 检查是否在下边缘进行调整大小
        elif h - self.resize_border < event.y < h:
            self.resize_mode = 'resize_b'
            self.result_tk.config(cursor="bottom_side")
        # 否则，进行拖动
        else:
            self.resize_mode = 'move'
            self.result_tk.config(cursor="fleur")

    def do_move_or_resize(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        
        if self.resize_mode == 'move':
            x = self.result_tk.winfo_x() + deltax
            y = self.result_tk.winfo_y() + deltay
            self.result_tk.geometry(f"+{x}+{y}")
        
        elif self.resize_mode in ['resize_r', 'resize_rb']:
            new_width = self.result_tk.winfo_width() + deltax
            if new_width > 100: # 最小宽度
                self.result_tk.geometry(f"{new_width}x{self.result_tk.winfo_height()}")
                self.x = event.x # 重置起始点以防止累积误差
        
        if self.resize_mode in ['resize_b', 'resize_rb']:
            new_height = self.result_tk.winfo_height() + deltay
            if new_height > 50: # 最小高度
                self.result_tk.geometry(f"{self.result_tk.winfo_width()}x{new_height}")
                self.y = event.y # 重置起始点以防止累积误差

    def stop_move_or_resize(self, event):
        self.resize_mode = None
        self.result_tk.config(cursor="") # 恢复默认光标

    def update_text(self, text):
        # 将 Markdown 转换为 HTML，并启用表格扩展
        html_content = markdown.markdown(text, extensions=['tables'])
        
        # 包装 HTML 内容以应用配置中的背景和字体样式
        # 注意：tkhtmlview 对 CSS 支持有限，但可以设置基本样式
        style = f"background-color: {self.config['result_bg_color']}; color: {self.config['result_fg_color']}; font-family: {self.config['result_font_family']}; font-size: {self.config['result_font_size']}px;"
        
        final_html = f"""
        <body style="{style}">
            {html_content}
        </body>
        """
        
        self.text_widget.set_html(final_html)

    def close(self):
        # 保存几何信息
        self.save_geometry()
        self.result_tk.destroy()

    def save_geometry(self):
        """保存当前窗口的几何信息"""
        geometry = self.result_tk.geometry()
        self.config["result_window_geometry"] = geometry
        save_config(self.config)

class TranslatorApp:
    def __init__(self):
        self.selection_box = None
        self.result_window = None
        self.selection_window_instance = None # 用于跟踪 SelectionWindow 实例
        self.config = load_config() # 加载配置
        
        self.root = tk.Tk()
        self.root.withdraw() # 隐藏主窗口
        
        self.hotkey_listener = None
        self._setup_hotkeys()

    def _setup_hotkeys(self):
        """设置全局热键监听"""
        hotkeys = {
            self.config['hotkey_select']: self.toggle_selection_mode_safe,
            self.config['hotkey_capture']: self.capture_and_translate_safe
        }
        self.hotkey_listener = keyboard.GlobalHotKeys(hotkeys)
        self.hotkey_listener.start()
        
    def toggle_selection_mode_safe(self):
        """在 Tkinter 主线程中安全地启动选区模式"""
        self.root.after(0, self._toggle_selection_mode)

    def _toggle_selection_mode(self):
        """启动或取消区域选择 (防止叠加)"""
        # 1. 销毁旧的选择窗口（如果存在）
        if self.selection_window_instance and self.selection_window_instance.selection_tk.winfo_exists():
            self.selection_window_instance.cancel_selection()
            self.selection_window_instance = None
            return # 如果只是取消，则返回
            
        # 2. 销毁结果窗口（如果存在）
        if self.result_window:
            self.result_window.close()
            self.result_window = None
            
        # 3. 启动新的选择窗口
        self.selection_window_instance = SelectionWindow(self.root, self)

    def set_selection_box(self, box):
        """设置选区坐标，并创建结果窗口标记位置"""
        self.selection_box = box
        if self.result_window:
            self.result_window.close()
            self.result_window = None
            
        if self.selection_box:
            # 创建结果窗口，它将作为选区的视觉标记，并用于显示结果
            self.result_window = TranslationResultWindow(self.root, self.selection_box, self.config)
            self.result_window.update_text("选区已设置。请按 'x' 键开始翻译。")

    def capture_and_translate_safe(self):
        """在 Tkinter 主线程中安全地启动截图和翻译"""
        if self.selection_box:
            self.root.after(0, self._start_translation_thread)
        else:
            print(f"错误: 未选择任何区域。请先按 '{self.config['hotkey_select']}' 创建一个选区。")

    def _start_translation_thread(self):
        """启动一个新线程来处理截图和 API 调用"""
        if self.result_window:
            self.result_window.update_text("正在截图并发送给 AI 翻译...")
        
        # 截图和 API 调用是耗时操作，必须在单独的线程中运行
        threading.Thread(target=self._execute_capture_and_translate, daemon=True).start()

    def _execute_capture_and_translate(self):
        """执行截图、API 调用和结果更新"""
        try:
            # 1. 截图
            box = self.selection_box
            if not box: return
            
            # ImageGrab.grab 必须在非 GUI 线程中调用
            image = ImageGrab.grab(bbox=box, all_screens=True)
            
            # 2. 编码
            base64_image = self._encode_image_to_base64(image)
            if not base64_image:
                self._update_result_safe("错误: 图像编码失败。")
                return

            # 3. API 调用
            translation = self._send_image_to_api(base64_image)
            
            # 4. 更新结果
            if translation:
                self._update_result_safe(translation)
            else:
                self._update_result_safe("翻译失败：未收到有效的 AI 响应。")

        except Exception as e:
            print(f"翻译过程中发生致命错误: {e}")
            self._update_result_safe(f"翻译过程中发生错误: {e}")

    def _update_result_safe(self, text):
        """在 Tkinter 主线程中安全地更新结果窗口"""
        if self.result_window:
            self.root.after(0, lambda: self.result_window.update_text(text))

    def _encode_image_to_base64(self, image) -> str | None:
        """将 PIL 图像对象编码为 Base64 字符串"""
        try:
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"[错误] 编码图片失败: {e}")
            return None

    def _send_image_to_api(self, base64_image: str) -> str | None:
        """发送 Base64 编码的图像到 AI API 进行翻译"""
        api_key = self.config['api_key']
        api_url = self.config['api_url']
        system_prompt = self.config['system_prompt']
        model_name = self.config['model_name']
        timeout = self.config['request_timeout_seconds']
        
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        
        content_parts = [
            {"type": "text", "text": system_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
        ]
        
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content_parts}
            ]
        }

        print("正在向 API 发送翻译请求...")
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=timeout)
            
            if response.status_code == 200:
                content = response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
                if content and content.strip():
                    print("--- API 响应成功 ---")
                    return content
                else:
                    print("API 响应内容为空。")
                    return None
            else:
                print(f"API 返回错误状态码: {response.status_code}. 响应: {response.text}")
                return f"API 错误: {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            print(f"发生网络错误: {e}")
            return f"网络错误: {e}"

    def run(self):
        print("-------------------------------------------------")
        print("屏幕翻译工具已启动")
        print(f"  - 按下 [{self.config['hotkey_select']}] 启动区域选择框。")
        print(f"  - 按下 ['{self.config['hotkey_capture']}'] 截图并翻译选区内容。")
        print("  - 关闭此控制台窗口即可退出程序。")
        print("-------------------------------------------------")
        self.root.mainloop()
        
        # 退出时停止热键监听
        if self.hotkey_listener:
            self.hotkey_listener.stop()

if __name__ == "__main__":
    app = TranslatorApp()
    app.run()