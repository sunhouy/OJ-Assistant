# -*- coding: utf-8 -*-
# @Author : 小红牛
# 微信公众号：WdPython
import tkinter as tk
from tkinter import ttk

def create_demo_widgets(parent):
    """创建一组ttk组件用于演示主题效果"""
    frame = ttk.Frame(parent, padding=10)
    frame.pack(padx=10, pady=10, fill='both', expand=True)

    # 标签
    ttk.Label(frame, text='这是一个标签:').grid(row=0, column=0, sticky='w')
    # 输入框
    ttk.Entry(frame, width=15).grid(row=0, column=1, padx=5)
    # 按钮
    ttk.Button(frame, text='按钮', command=lambda: print("点击按钮")).grid(row=0, column=2, padx=5)
    # 复选框
    ttk.Checkbutton(frame, text='复选框').grid(row=1, column=0, sticky='w', pady=5)
    # 单选框
    radio_var = tk.StringVar()
    ttk.Radiobutton(frame, text='选项1', variable=radio_var, value='1').grid(row=2, column=0, sticky='w')
    ttk.Radiobutton(frame, text='选项2', variable=radio_var, value='2').grid(row=3, column=0, sticky='w')
    # 下拉框
    combo = ttk.Combobox(frame, values=["选项1", "选项2", "选项3"], state='readonly')
    combo.current(0)
    combo.grid(row=1, column=1, pady=5)
    # 进度条
    progress = ttk.Progressbar(frame, orient='horizontal', length=100, mode='determinate')
    progress.grid(row=1, column=2)
    progress.start(10)
    # 树状视图
    tree = ttk.Treeview(frame, columns=('名称', '值'), show='headings', height=2)
    tree.heading('名称', text='名称')
    tree.heading('值', text='值')
    tree.insert('', 'end', values=('项目1', 100))
    tree.insert('', 'end', values=('项目2', 200))
    tree.grid(row=4, column=0, columnspan=3, pady=5)
    # 分隔线
    ttk.Separator(frame, orient='horizontal').grid(row=5, columnspan=3, sticky='ew', pady=5)
    # 笔记本（选项卡）
    notebook = ttk.Notebook(frame)
    tab1 = ttk.Frame(notebook)
    tab2 = ttk.Frame(notebook)
    notebook.add(tab1, text='选项卡1')
    notebook.add(tab2, text='选项卡2')
    notebook.grid(row=6, columnspan=3, sticky='ew')

    return frame

def change_theme(theme):
    """切换主题并更新界面"""
    style.theme_use(theme)
    print(f"当前主题: {theme}")

# 创建主窗口
root = tk.Tk()
root.title('ttk主题样式演示')

# 初始化样式对象
style = ttk.Style()
available_themes = style.theme_names()
current_theme = style.theme_use()
print("可用内置主题:", available_themes)

# 创建主题选择控件
theme_frame = ttk.Frame(root, padding=(10,5))
theme_frame.pack(fill='x')

ttk.Label(theme_frame, text="选择主题:").pack(side='left', padx=5)
theme_combobox = ttk.Combobox(
    theme_frame,
    values=list(available_themes),
    state='readonly'
)
theme_combobox.set(current_theme)
theme_combobox.pack(side='left', padx=5)
theme_combobox.bind('<<ComboboxSelected>>',
                   lambda e: change_theme(theme_combobox.get()))

# 创建演示组件
demo_frame = create_demo_widgets(root)

# 启动主循环
root.mainloop()
