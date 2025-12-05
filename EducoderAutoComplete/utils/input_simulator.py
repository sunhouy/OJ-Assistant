import pyautogui
import time
import pyperclip
import keyboard
from tkinter import messagebox
import uiautomation as auto


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

    def escape_braces(self, text):
        """转义文本中的左括号"""
        # { -> {{}
        return text.replace('{', '{{}')

    def clean_code_markers(self, code):
        """清理代码中的代码块标记（如```c和```），处理标记和代码在同一行的情况"""
        lines = code.split('\n')
        cleaned_lines = []
        skip_first_marker = True  # 标记是否还需要跳过开头的代码块标记

        for i, line in enumerate(lines):
            stripped_line = line.strip()

            # 处理开头的代码块标记
            if skip_first_marker and stripped_line.startswith('```'):
                # 检查是否有语言标识（c, cpp, java, python, javascript, csharp等）
                marker_end = stripped_line.find(' ', 3)  # 找```后的第一个空格
                if marker_end == -1:
                    # 如果没有空格，可能是```c#include这种形式
                    if len(stripped_line) > 3:
                        # 检查后面的字符是否是语言标识
                        lang_part = stripped_line[3:].lower()
                        lang_identifiers = ['c', 'cpp', 'java', 'python', 'javascript', 'js', 'csharp', 'cs']

                        # 检查是否是纯语言标识（没有其他代码）
                        is_pure_lang_marker = True
                        for lang in lang_identifiers:
                            if lang_part.startswith(lang):
                                # 如果后面还有字符，检查是否是代码的开始
                                remaining = lang_part[len(lang):]
                                if remaining:  # 还有内容，说明标记和代码在同一行
                                    # 只移除```和语言标识，保留后面的代码
                                    cleaned_line = line.replace('```' + lang, '', 1).lstrip()
                                    if cleaned_line:  # 如果还有内容，添加到清理后的行
                                        cleaned_lines.append(cleaned_line)
                                        skip_first_marker = False
                                    else:
                                        # 如果移除标记后是空行，跳过
                                        pass
                                else:
                                    # 纯标记行，直接跳过
                                    pass
                                break
                        else:
                            # 不是语言标识，可能只是```，移除标记
                            cleaned_line = line.replace('```', '', 1).strip()
                            if cleaned_line:
                                cleaned_lines.append(cleaned_line)
                    else:
                        # 只有```，跳过这一行
                        pass
                else:
                    # 有空格，可能是```c #include这种形式
                    marker_part = stripped_line[:marker_end]
                    if marker_part.startswith('```'):
                        # 移除标记部分，保留后面的代码
                        cleaned_line = line[line.find(stripped_line[marker_end:]):]
                        if cleaned_line.strip():
                            cleaned_lines.append(cleaned_line)
                    skip_first_marker = False
                continue

            # 处理结尾的代码块标记
            if i == len(lines) - 1 and stripped_line == '```':
                # 跳过结尾的标记行
                continue

            # 对于其他行，直接添加
            cleaned_lines.append(line)
            skip_first_marker = False

        # 重新组合代码
        cleaned_code = '\n'.join(cleaned_lines)

        # 如果清理后代码为空，返回原始代码
        if not cleaned_code.strip():
            return code

        # 如果清理后的代码以```开头（说明之前的处理可能遗漏了），再次清理
        if cleaned_code.strip().startswith('```'):
            # 找到第一个换行符
            first_newline = cleaned_code.find('\n')
            if first_newline != -1:
                # 移除第一行的```部分
                first_line = cleaned_code[:first_newline]
                rest = cleaned_code[first_newline + 1:]
                # 移除第一行中的```
                first_line_cleaned = first_line.replace('```', '').strip()
                # 如果第一行还有内容，重新组合
                if first_line_cleaned:
                    cleaned_code = first_line_cleaned + '\n' + rest
                else:
                    cleaned_code = rest

        self.gui.log(f"已清理代码标记，原始行数: {len(lines)}，清理后行数: {len(cleaned_lines)}")
        return cleaned_code

    def paste_code(self, code):
        """使用复制粘贴方式输入代码，自动清理代码标记"""
        try:
            # 清理代码标记
            cleaned_code = self.clean_code_markers(code)

            # 安装ESC键监听
            keyboard.on_press_key('esc', self.set_esc_pressed, suppress=False)

            # 清空编辑器
            screen_width, screen_height = pyautogui.size()
            x = screen_width // 2
            y = screen_height // 2
            pyautogui.click(x=x, y=y)
            time.sleep(0.1)
            auto.SendKeys('{Ctrl}a')
            time.sleep(0.1)
            auto.SendKeys('{Delete}')
            time.sleep(0.2)

            # 检查ESC键
            if self.esc_pressed:
                self.gui.log("用户按下了ESC键，终止代码粘贴")
                self._show_termination_message()
                keyboard.unhook_all()
                return False

            # 复制清理后的代码到剪贴板
            pyperclip.copy(cleaned_code)
            time.sleep(0.05)

            # 使用uiautomation粘贴代码
            auto.SendKeys('{Ctrl}v')
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
            # 如果是第一个块，清理整个代码的标记
            if is_first_chunk:
                # 清理代码标记
                cleaned_text = self.clean_code_markers(text)
                # 使用清理后的文本
                text = cleaned_text
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

                # 点击屏幕中央激活编辑器
                screen_width, screen_height = pyautogui.size()
                x = screen_width // 2
                y = screen_height // 2
                pyautogui.click(x=x, y=y)
                time.sleep(0.1)
                auto.SendKeys('{Ctrl}a')    # 全选
                time.sleep(0.1)
                auto.SendKeys('{Delete}')   # 删除
                time.sleep(0.1)

            if text.strip():
                # 使用批量输入
                lines = text.split('\n')
                for line_index, line in enumerate(lines):
                    # 检查ESC键
                    if self.esc_pressed:
                        self.gui.log("用户按下了ESC键，终止代码输入")
                        self._show_termination_message()
                        keyboard.unhook_all()
                        return False

                    if line.strip():  # 只处理非空行
                        # 处理行内的左括号，每个左括号都需要特殊处理
                        if '{' in line:
                            # 分割行以便处理左括号
                            parts = []
                            last_index = 0
                            for i, char in enumerate(line):
                                if char == '{':
                                    # 添加左括号前的部分（转义右括号）
                                    if i > last_index:
                                        plain_part = line[last_index:i]
                                        # 转义左括号
                                        escaped_part = plain_part.replace('{', '{{}')
                                        parts.append(escaped_part)
                                    # 添加左括号（转义）并删除自动补全的右括号
                                    parts.append('{')
                                    last_index = i + 1

                            # 添加剩余部分
                            if last_index < len(line):
                                plain_part = line[last_index:]
                                # 转义左括号
                                escaped_part = plain_part.replace('{', '{{}')
                                parts.append(escaped_part)

                            # 合并并发送所有部分
                            for part in parts:
                                if part == '{':
                                    # 输入左括号（转义），等待自动补全，然后删除右括号
                                    auto.SendKeys('{{}')
                                    time.sleep(0.1)  # 等待编辑器自动补全右括号
                                    auto.SendKeys('{Delete}')
                                elif part:
                                    # 发送其他部分
                                    auto.SendKeys(part)
                        else:
                            # 没有左括号，直接发送整行（转义左括号）
                            escaped_line = line.replace('{', '{{}')
                            auto.SendKeys(escaped_line)

                    # 如果不是最后一行，添加换行
                    if line_index < len(lines) - 1:
                        auto.SendKeys('{Enter}')
                        auto.SendKeys('{Home}')   # 删除自动补全的空格
                        self.line_count += 1
                        time.sleep(0.05)  # 换行后的短暂等待
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