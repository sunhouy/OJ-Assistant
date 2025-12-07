import time
import pyperclip
import keyboard
import pyautogui
from tkinter import messagebox


class InputSimulator:
    def __init__(self, gui):
        self.gui = gui
        self.typing_active = True
        self.left_brace_count = 0
        self.line_count = 0
        self.esc_pressed = False

    def reset(self):
        """重置状态"""
        self.typing_active = True
        self.left_brace_count = 0
        self.line_count = 0
        self.esc_pressed = False

    def set_esc_pressed(self, event=None):
        """设置ESC键按下标志"""
        if not self.esc_pressed:  # 避免重复触发
            self.esc_pressed = True
            self.typing_active = False

    def paste_code(self, code):
        """使用复制粘贴方式输入代码"""
        try:
            # 安装ESC键监听
            keyboard.on_press_key('esc', self.set_esc_pressed, suppress=False)

            # 激活编辑器（点击屏幕中央）
            screen_width, screen_height = pyautogui.size()
            x = screen_width // 2
            y = screen_height // 2
            pyautogui.click(x=x, y=y)
            time.sleep(0.05)

            # 清空编辑器内容
            keyboard.press_and_release('ctrl+a')
            time.sleep(0.05)
            keyboard.press_and_release('delete')
            time.sleep(0.05)

            # 检查ESC键
            if self.esc_pressed:
                self.gui.log("用户按下了ESC键，终止代码粘贴")
                self._show_termination_message()
                keyboard.unhook_all()
                return False

            # 复制代码到剪贴板并粘贴
            pyperclip.copy(code)
            time.sleep(0.05)
            keyboard.press_and_release('ctrl+v')
            time.sleep(0.05)

            self.gui.log("代码已通过复制粘贴完成输入")

            # 移除ESC键监听
            keyboard.unhook_all()

            # 显示完成消息
            self.gui.root.after(0, lambda: messagebox.showinfo("提示", "代码输入已完成"))
            return True

        except Exception as e:
            self.gui.log(f"复制粘贴失败: {e}")
            keyboard.unhook_all()
            return False

    def simulate_typing(self, text, is_first_chunk=False):
        """模拟键盘输入代码"""
        try:
            # 如果是第一个块，开始模拟键盘输入
            if is_first_chunk:
                self.gui.log("开始模拟键盘输入代码...")
                self.line_count = 0
                self.esc_pressed = False

                # 安装ESC键监听
                keyboard.on_press_key('esc', self.set_esc_pressed, suppress=False)

                # 检查ESC键
                if self.esc_pressed:
                    self.gui.log("用户按下了ESC键，终止代码输入")
                    self._show_termination_message()
                    keyboard.unhook_all()
                    return False

                # 激活编辑器（点击屏幕中央）
                screen_width, screen_height = pyautogui.size()
                x = screen_width // 2
                y = screen_height // 2
                pyautogui.click(x=x, y=y)
                time.sleep(0.05)

                # 清空编辑器内容
                keyboard.press_and_release('ctrl+a')
                time.sleep(0.05)
                keyboard.press_and_release('delete')
                time.sleep(0.05)

            # 使用批量输入
            lines = text.split('\n')
            for line_index, line in enumerate(lines):
                # 检查ESC键
                if self.esc_pressed:
                    self.gui.log("用户按下了ESC键，终止代码输入")
                    self._show_termination_message()
                    keyboard.unhook_all()
                    return False

                # 处理当前行
                if line.strip():  # 非空行
                    # 处理行内的左括号，每个左括号都需要特殊处理
                    if '{' in line:
                        # 分割行以便处理左括号
                        parts = []
                        last_index = 0
                        for i, char in enumerate(line):
                            if char == '{':
                                # 添加左括号前的部分
                                if i > last_index:
                                    plain_part = line[last_index:i]
                                    # 直接输入普通文本
                                    keyboard.write(plain_part)
                                # 处理左括号：输入左括号，等待自动补全，然后删除右括号
                                keyboard.write('{')
                                time.sleep(0.05)  # 等待编辑器自动补全右括号
                                keyboard.press_and_release('delete')
                                last_index = i + 1

                        # 添加剩余部分
                        if last_index < len(line):
                            plain_part = line[last_index:]
                            keyboard.write(plain_part)
                    else:
                        # 没有左括号，直接发送整行
                        keyboard.write(line)

                # 如果是最后一行且为空行，不需要处理
                # 如果不是最后一行，添加换行
                if line_index < len(lines) - 1:
                    keyboard.press_and_release('enter')
                    time.sleep(0.05)  # 换行后的短暂等待
                    keyboard.press_and_release('home')

                # 记录行数（包括空行）
                if line_index < len(lines) - 1:
                    self.line_count += 1

            return True

        except Exception as e:
            self.gui.log(f"模拟键盘输入失败: {e}")
            keyboard.unhook_all()
            return False

    def finalize_formatting(self):
        """完成代码输入后的格式化操作"""
        try:
            self.gui.log(f"代码输入完成，共处理了{self.line_count}行")
            # 移除ESC键监听
            keyboard.unhook_all()
            self.gui.root.after(0, lambda: messagebox.showinfo("提示", "代码输入已完成。"))
            return True

        except Exception as e:
            self.gui.log(f"代码格式化失败: {e}")
            keyboard.unhook_all()
            return False

    def _show_termination_message(self):
        """显示终止消息"""
        self.gui.root.after(0, lambda: messagebox.showinfo("提示", "用户已终止代码输入"))