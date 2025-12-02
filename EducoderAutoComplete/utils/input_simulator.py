import pyautogui
import time
import pyperclip
from tkinter import messagebox


class InputSimulator:
    def __init__(self, gui):
        self.gui = gui
        self.typing_active = True
        self.left_brace_count = 0

    def reset(self):
        """重置状态"""
        self.typing_active = True
        self.left_brace_count = 0

    def paste_code(self, code):
        """使用复制粘贴方式输入代码"""
        try:
            # 清空编辑器
            screen_width, screen_height = pyautogui.size()
            x = screen_width // 2
            y = screen_height // 2
            pyautogui.click(x=x, y=y)
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            pyautogui.hotkey('delete')
            time.sleep(0.5)

            # 复制代码到剪贴板
            pyperclip.copy(code)
            time.sleep(0.1)

            # 粘贴代码
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.5)

            # 格式化代码
            pyautogui.hotkey('alt', 'shift', 'f')
            time.sleep(0.5)

            self.gui.log("代码已通过复制粘贴完成输入")
            messagebox.showinfo("提示", "代码输入已完成")
            return True

        except Exception as e:
            self.gui.log(f"复制粘贴失败: {e}")
            return False

    def simulate_typing(self, text, is_first_chunk=False):
        """模拟键盘输入代码"""
        try:
            # 检查鼠标是否在屏幕角落（用户终止信号）
            screen_width, screen_height = pyautogui.size()
            mouse_x, mouse_y = pyautogui.position()

            # 如果鼠标在屏幕左上角或右上角（10像素范围内），则停止输入
            if (mouse_x < 10 and mouse_y < 10) or (mouse_x > screen_width - 10 and mouse_y < 10):
                self.typing_active = False
                self.gui.log("检测到用户手动终止代码输入")
                return False

            if is_first_chunk:
                self.gui.log("开始模拟键盘输入代码...")

                # 点击屏幕中央激活编辑器
                screen_width, screen_height = pyautogui.size()
                x = screen_width // 2
                y = screen_height // 2
                pyautogui.click(x=x, y=y)

                time.sleep(0.1)
                pyautogui.hotkey('ctrl', 'a')  # 全选
                time.sleep(0.1)
                pyautogui.hotkey('delete')  # 删除
                time.sleep(0.5)

            if text.strip():
                # 统计左括号数量
                self.left_brace_count += text.count('{')

                # 输入文本
                pyautogui.write(text, interval=0.05)  # 稍微加快输入速度

            return True

        except Exception as e:
            self.gui.log(f"模拟键盘输入失败: {e}")
            return False

    def finalize_formatting(self):
        """完成代码输入后的格式化操作"""
        try:
            time.sleep(0.2)

            # 首先进行一次完整格式化
            pyautogui.hotkey('alt', 'shift', 'f')
            time.sleep(0.5)

            # 根据左括号数量删除多余的右括号
            if self.left_brace_count > 0:
                self.gui.log(f"检测到 {self.left_brace_count} 个左括号，正在删除多余的右括号...")

                # 移动到代码末尾
                pyautogui.hotkey('ctrl', 'end')
                time.sleep(0.1)

                # 删除多余的右括号，每次删除后都格式化
                for i in range(self.left_brace_count):
                    # 删除一个右括号
                    pyautogui.press('backspace')
                    time.sleep(0.1)

                    # 每次删除后都进行格式化
                    pyautogui.hotkey('alt', 'shift', 'f')
                    time.sleep(0.3)

                    self.gui.log(f"已删除 {i + 1}/{self.left_brace_count} 个多余的右括号并格式化")

                self.gui.log(f"已完成所有右括号删除和格式化")

            # 最终格式化一次确保代码整洁
            pyautogui.hotkey('alt', 'shift', 'f')
            time.sleep(0.3)

            self.gui.log("代码输入和格式化完成")
            messagebox.showinfo("提示", "代码输入已完成。如果大括号仍有问题，请手动调整。")
            return True

        except Exception as e:
            self.gui.log(f"代码格式化失败: {e}")
            return False