import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

import keyboard


class TestInputDialog:
    def __init__(self, parent):
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("输入测试")
        self.dialog.geometry("700x700")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)

        # 居中显示
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')

        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 创建Notebook实现标签页布局
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 输入设置标签页
        input_frame = ttk.Frame(notebook, padding="10")
        notebook.add(input_frame, text="输入设置")

        # 输入内容标签和多行文本框
        ttk.Label(input_frame, text="要输入的内容:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))

        # 创建带滚动条的多行文本框
        text_frame = ttk.Frame(input_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 添加垂直滚动条
        text_scrollbar = ttk.Scrollbar(text_frame)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 多行文本框
        self.text_input = tk.Text(
            text_frame,
            height=8,
            width=50,
            wrap=tk.WORD,
            font=("Courier New", 10),
            yscrollcommand=text_scrollbar.set,
            relief=tk.SUNKEN,
            borderwidth=2
        )
        self.text_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scrollbar.config(command=self.text_input.yview)

        # 默认示例文本
        self.text_input.insert("1.0", "请在此输入要测试的文本...\n可以输入多行内容\n每行将按顺序输入")

        # 参数设置框架
        params_frame = ttk.LabelFrame(input_frame, text="参数设置", padding="10")
        params_frame.pack(fill=tk.X, pady=(5, 10))

        # 等待时间
        ttk.Label(params_frame, text="等待时间(秒):").grid(row=0, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        self.delay_var = tk.StringVar(value="2")
        delay_entry = ttk.Entry(params_frame, textvariable=self.delay_var, width=10)
        delay_entry.grid(row=0, column=1, sticky=tk.W, pady=5)

        # 输入速度
        ttk.Label(params_frame, text="输入间隔(秒):").grid(row=1, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        self.interval_var = tk.StringVar(value="0.05")
        interval_entry = ttk.Entry(params_frame, textvariable=self.interval_var, width=10)
        interval_entry.grid(row=1, column=1, sticky=tk.W, pady=5)

        # 特殊字符处理选项
        self.special_chars_var = tk.BooleanVar(value=True)
        special_chars_check = ttk.Checkbutton(
            params_frame,
            text="启用特殊字符处理（如换行、Tab等）",
            variable=self.special_chars_var
        )
        special_chars_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)

        # 状态显示标签页
        status_frame = ttk.Frame(notebook, padding="10")
        notebook.add(status_frame, text="日志信息")

        # 状态标签
        self.status_var = tk.StringVar(value="准备就绪")
        status_label = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            font=("Arial", 10),
            wraplength=400
        )
        status_label.pack(anchor=tk.W, pady=5)

        # 操作日志文本框
        ttk.Label(status_frame, text="操作日志:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
        log_frame = ttk.Frame(status_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)

        log_scrollbar = ttk.Scrollbar(log_frame)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(
            log_frame,
            height=6,
            width=50,
            wrap=tk.WORD,
            font=("Courier New", 9),
            yscrollcommand=log_scrollbar.set,
            state=tk.DISABLED,
            relief=tk.SUNKEN,
            borderwidth=1
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.config(command=self.log_text.yview)

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))

        # 开始按钮
        self.start_btn = ttk.Button(
            button_frame,
            text="开始测试",
            command=self.start_test,
            width=15
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        # 停止按钮
        self.stop_btn = ttk.Button(
            button_frame,
            text="停止测试",
            command=self.stop_test,
            width=15,
            state="disabled"
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))

        # 清除按钮
        clear_btn = ttk.Button(
            button_frame,
            text="清除内容",
            command=self.clear_content,
            width=15
        )
        clear_btn.pack(side=tk.LEFT)

        # 用于控制测试是否继续的标志
        self.test_running = False
        self._add_log("Keyboard 库加载成功")
        self._add_log("注意：某些系统可能需要管理员权限")

        # 绑定窗口关闭事件
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_test(self):
        """开始输入测试"""
        # 获取文本框中的所有内容
        content = self.text_input.get("1.0", tk.END).strip()
        delay_str = self.delay_var.get()
        interval_str = self.interval_var.get()

        if not content or content == "请在此输入要测试的文本...\n可以输入多行内容\n每行将按顺序输入":
            messagebox.showerror("输入错误", "请输入要测试的内容")
            return

        try:
            delay = float(delay_str)
            if delay < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("输入错误", "等待时间必须是正数")
            return

        try:
            interval = float(interval_str)
            if interval < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("输入错误", "输入间隔必须是正数")
            return

        # 设置测试运行标志
        self.test_running = True

        # 禁用开始按钮，启用停止按钮
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        self.status_var.set(f"等待 {delay} 秒后开始输入...")
        self._add_log(f"开始测试 - 等待时间: {delay}秒, 输入间隔: {interval}秒")
        self._add_log(f"特殊字符处理: {'启用' if self.special_chars_var.get() else '禁用'}")

        # 在新线程中执行测试
        threading.Thread(
            target=self._run_test,
            args=(content, delay, interval),
            daemon=True
        ).start()

    def _run_test(self, content, delay, interval):
        """实际执行输入测试的线程"""
        try:
            # 等待指定时间
            for i in range(int(delay * 10)):  # 每0.1秒检查一次
                if not self.test_running:
                    self._update_status("测试已停止", warning=True)
                    self._add_log("测试被用户停止")
                    return
                time.sleep(0.1)

            self._add_log(f"等待完成，开始输入...")

            # 检查是否仍然有 keyboard 库
            if not keyboard:
                self._update_status("错误: keyboard 不可用", error=True)
                return

            # 执行输入
            self._update_status("正在输入...")
            self._add_log(f"输入内容长度: {len(content)} 字符")

            if len(content) > 50:
                self._add_log(f"前50字符: {content[:50]}...")
            else:
                self._add_log(f"内容: {content}")

            # 根据设置选择输入方式
            if self.special_chars_var.get():
                # 处理特殊字符（逐字符输入）
                self._type_with_special_chars(content, interval)
            else:
                # 简单输入（使用 write 函数）
                self._simple_type(content, interval)

            if self.test_running:
                # 完成提示
                self._update_status("输入测试完成!", success=True)
                self._add_log("输入测试成功完成")
                self.parent.after(0, lambda: messagebox.showinfo("测试完成", "输入测试已完成"))
            else:
                self._add_log("测试已提前停止")

        except Exception as e:
            if self.test_running:
                error_msg = f"测试失败: {str(e)}"
                self._update_status(error_msg, error=True)
                self._add_log(f"错误: {error_msg}")
        finally:
            self.parent.after(0, lambda: self.start_btn.config(state="normal"))
            self.parent.after(0, lambda: self.stop_btn.config(state="disabled"))
            self.test_running = False

    def _simple_type(self, content, interval):
        """简单的输入方式（使用 keyboard.write）"""
        # keyboard.write 不支持 interval 参数，所以需要自己实现
        for char in content:
            if not self.test_running:
                break
            try:
                keyboard.write(char)
                time.sleep(interval)
            except Exception as e:
                if self.test_running:
                    self._add_log(f"输入字符 '{char}' 时出错: {str(e)}")
                    time.sleep(interval)

    def _type_with_special_chars(self, content, interval):
        """处理特殊字符的输入方式"""
        for char in content:
            if not self.test_running:
                break

            try:
                if char == '\n':
                    # 换行符
                    keyboard.press_and_release('enter')
                elif char == '\t':
                    # Tab 键
                    keyboard.press_and_release('tab')
                elif char == ' ':
                    # 空格键
                    keyboard.press_and_release('space')
                elif len(char) == 1 and ord(char) < 128:
                    # 普通 ASCII 字符
                    keyboard.write(char)
                else:
                    # 其他字符（如中文）
                    keyboard.write(char)

                time.sleep(interval)
            except Exception as e:
                if self.test_running:
                    self._add_log(f"输入字符 '{repr(char)}' 时出错: {str(e)}")
                    time.sleep(interval)

    def stop_test(self):
        """停止测试"""
        self.test_running = False
        self._update_status("正在停止测试...", warning=True)
        self._add_log("用户请求停止测试")

    def _update_status(self, message, success=False, error=False, warning=False):
        """更新状态显示（安全地在主线程中更新）"""

        def update():
            self.status_var.set(message)

        self.parent.after(0, update)

    def _add_log(self, message):
        """添加日志信息"""

        def update_log():
            self.log_text.config(state=tk.NORMAL)
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)  # 滚动到底部
            self.log_text.config(state=tk.DISABLED)

        self.parent.after(0, update_log)

    def clear_content(self):
        """清除文本框内容"""
        self.text_input.delete("1.0", tk.END)
        self._add_log("已清除输入内容")

    def on_closing(self):
        """窗口关闭时的处理"""
        # 停止正在进行的测试
        self.test_running = False
        time.sleep(0.1)  # 给线程一点时间响应
        self.dialog.destroy()


# 使用示例
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    dialog = TestInputDialog(root)
    root.mainloop()