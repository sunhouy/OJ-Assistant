import json
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Tuple, Optional

from utils.config import ConfigManager


class LanguageManager:
    """语言管理器，负责管理编程语言列表"""

    # 标准语言列表
    STANDARD_LANGUAGES = [
        "Python", "C", "C++", "Java", "C#", "JavaScript", "Visual Basic", "SQL", "Perl",
        "R", "Delphi", "Object Pascal", "Fortran", "MATLAB", "Ada", "Go", "PHP", "Rust",
        "Assembly", "Kotlin", "COBOL", "Prolog", "Ruby", "Dart", "SAS", "Lisp", "Julia",
        "Objective-C", "Lua", "Haskell", "TypeScript", "Scala", "FoxPro", "ABAP", "PL/SQL",
        "VBScript", "Elixir", "Ladder Logic", "Solidity", "PowerShell", "Zig", "Bash",
        "Apex", "LabVIEW", "Wolfram", "Erlang", "ML", "RPG", "ActionScript", "Algol",
        "Alice", "Awk", "B4X", "Caml", "CLIPS", "Clojure", "Common Lisp", "Crystal",
        "D", "Elm", "F#", "Forth", "GAMS", "Groovy", "Hack", "Icon", "Inform", "Io",
        "J", "JScript", "Logo", "Maple", "Modula-2", "Mojo", "MQL5", "NATURAL", "Nim",
        "Oberon", "OCaml", "Occam", "OpenCL", "PL/I", "Q", "REXX", "S", "Scheme",
        "Simulink", "Smalltalk", "SPARK", "SPSS", "Stata", "SystemVerilog", "Tcl",
        "Transact-SQL", "V", "VHDL", "X++", "Xojo"
    ]

    # 内置语言列表
    BUILTIN_LANGUAGES = ["C", "C++", "Java", "Python", "JavaScript"]

    def __init__(self, config_manager: ConfigManager, log_callback=None):
        """
        初始化语言管理器
        :param config_manager: 配置管理器实例
        :param log_callback: 日志回调函数，用于记录日志
        """
        self.config_manager = config_manager
        self.log_callback = log_callback
        self.custom_languages = []
        self.load_custom_languages()

    def log(self, message):
        """记录日志"""
        if self.log_callback:
            self.log_callback(message)

    def _is_same_language(self, lang1: str, lang2: str) -> bool:
        """
        判断两个语言是否相同（不区分大小写）
        :param lang1: 语言1
        :param lang2: 语言2
        :return: 是否相同
        """
        return lang1.strip().lower() == lang2.strip().lower()

    def _is_builtin_language(self, lang: str) -> bool:
        """
        判断是否是内置语言（不区分大小写）
        :param lang: 语言名称
        :return: 是否是内置语言
        """
        lang_lower = lang.strip().lower()
        for builtin_lang in self.BUILTIN_LANGUAGES:
            if builtin_lang.lower() == lang_lower:
                return True
        return False

    def _language_exists(self, lang: str, language_list: list) -> bool:
        """
        检查语言是否已存在（不区分大小写）
        :param lang: 语言名称
        :param language_list: 语言列表
        :return: 是否存在
        """
        lang_lower = lang.strip().lower()
        for existing_lang in language_list:
            if existing_lang.strip().lower() == lang_lower:
                return True
        return False

    def _get_standard_language_name(self, lang: str) -> Optional[str]:
        """
        获取标准语言名称（如果输入的语言在标准列表中，返回标准大小写格式）
        :param lang: 输入的语言名称
        :return: 标准语言名称，如果不在标准列表中则返回None
        """
        lang_lower = lang.strip().lower()
        for standard_lang in self.STANDARD_LANGUAGES:
            if standard_lang.lower() == lang_lower:
                return standard_lang
        return None

    def _is_standard_language(self, lang: str) -> bool:
        """
        判断是否是标准语言（不区分大小写）
        :param lang: 语言名称
        :return: 是否在标准语言列表中
        """
        return self._get_standard_language_name(lang) is not None

    def load_custom_languages(self):
        """加载自定义语言"""
        try:
            custom_languages_str = self.config_manager.get_setting('custom_languages', '')
            if custom_languages_str:
                try:
                    custom_languages = json.loads(custom_languages_str)
                except json.JSONDecodeError:
                    custom_languages = []

                    # 尝试旧的加载方式
                    config = self.config_manager.get_config()
                    if 'custom_languages' in config:
                        old_custom_languages = config['custom_languages']
                        if isinstance(old_custom_languages, list):
                            custom_languages = old_custom_languages

                    # 将旧格式转换为新格式
                    if custom_languages:
                        custom_languages_json = json.dumps(custom_languages)
                        self.config_manager.set_setting('custom_languages', custom_languages_json)
            else:
                custom_languages = []

            # 过滤空值和重复项（不区分大小写）
            self.custom_languages = []
            seen_languages = set()
            for lang in custom_languages:
                lang_name = lang.strip()
                if lang_name:
                    lang_lower = lang_name.lower()
                    if lang_lower not in seen_languages:
                        seen_languages.add(lang_lower)
                        self.custom_languages.append(lang_name)

            self.log(f"加载了 {len(self.custom_languages)} 个自定义语言")
        except Exception as e:
            self.log(f"加载自定义语言时发生错误: {e}")
            self.custom_languages = []

    def save_custom_languages(self):
        """保存自定义语言到配置文件"""
        try:
            custom_languages_json = json.dumps(self.custom_languages)
            self.config_manager.set_setting('custom_languages', custom_languages_json)
            self.log(f"已保存 {len(self.custom_languages)} 个自定义语言")
        except Exception as e:
            self.log(f"保存自定义语言时发生错误: {e}")

    def get_language_list(self) -> list:
        """
        获取语言列表（内置+自定义），按首字母排序
        :return: 排序后的语言列表
        """
        # 合并内置语言和自定义语言
        all_languages = self.BUILTIN_LANGUAGES + self.custom_languages

        # 去重（不区分大小写）
        unique_languages = []
        seen_languages = set()
        for lang in all_languages:
            lang_lower = lang.strip().lower()
            if lang_lower not in seen_languages:
                seen_languages.add(lang_lower)
                unique_languages.append(lang.strip())

        # 按首字母排序（不区分大小写）
        unique_languages.sort(key=lambda x: x.lower())

        return unique_languages

    def add_language(self, lang: str) -> Tuple[bool, str]:
        """
        添加新语言
        :param lang: 语言名称
        :return: (是否成功, 错误消息)
        """
        new_lang = lang.strip()

        if not new_lang:
            return False, "请输入语言名称！"

        # 检查是否是内置语言（不区分大小写）
        if self._is_builtin_language(new_lang):
            return False, f"'{new_lang}' 是内置语言，无需添加！"

        # 检查是否已存在（不区分大小写）
        if self._language_exists(new_lang, self.custom_languages):
            return False, f"语言 '{new_lang}' 已存在！"

        # 检查是否是标准语言，并转换为正确的大小写
        standard_lang = self._get_standard_language_name(new_lang)
        if standard_lang:
            # 如果是标准语言，使用标准大小写格式
            new_lang = standard_lang
        else:
            # 如果不是标准语言，询问用户是否继续添加
            if not messagebox.askyesno("语言检查",
                                       f"您输入的编程语言 '{new_lang}' 似乎有误或不是常见的编程语言，是否继续添加？"):
                return False, "已取消添加"

        # 添加到列表
        self.custom_languages.append(new_lang)
        self.save_custom_languages()

        return True, f"已添加语言: {new_lang}"

    def delete_language(self, lang: str) -> Tuple[bool, str]:
        """
        删除语言
        :param lang: 语言名称
        :return: (是否成功, 错误消息)
        """
        if not lang:
            return False, "请先选择一个要删除的语言！"

        # 检查是否是内置语言（不区分大小写）
        if self._is_builtin_language(lang):
            return False, "不能删除内置语言！"

        # 查找并删除（不区分大小写）
        for i, custom_lang in enumerate(self.custom_languages):
            if self._is_same_language(custom_lang, lang):
                deleted_lang = self.custom_languages.pop(i)
                self.save_custom_languages()
                return True, f"已删除语言: {deleted_lang}"

        return False, f"语言 '{lang}' 不存在！"

    def edit_language(self, old_lang: str, new_lang: str) -> Tuple[bool, str]:
        """
        编辑语言名称
        :param old_lang: 旧语言名称
        :param new_lang: 新语言名称
        :return: (是否成功, 错误消息)
        """
        new_lang = new_lang.strip()

        if not new_lang:
            return False, "语言名称不能为空！"

        if self._is_same_language(old_lang, new_lang):
            return True, "语言名称未改变"

        # 检查是否是内置语言（不区分大小写）
        if self._is_builtin_language(new_lang):
            return False, f"'{new_lang}' 是内置语言，不能使用此名称！"

        # 检查新名称是否已存在（不区分大小写）
        if self._language_exists(new_lang, self.custom_languages):
            # 如果新名称和旧名称相同（不区分大小写），则允许
            if not self._is_same_language(old_lang, new_lang):
                return False, f"语言 '{new_lang}' 已存在！"

        # 检查是否是标准语言，并转换为正确的大小写
        standard_lang = self._get_standard_language_name(new_lang)
        if standard_lang:
            # 如果是标准语言，使用标准大小写格式
            new_lang = standard_lang

        # 查找并更新（不区分大小写）
        for i, custom_lang in enumerate(self.custom_languages):
            if self._is_same_language(custom_lang, old_lang):
                self.custom_languages[i] = new_lang
                self.save_custom_languages()
                return True, f"已修改语言: {old_lang} → {new_lang}"

        return False, f"语言 '{old_lang}' 不存在！"

    def open_custom_language_dialog(self, parent_window, update_callback=None):
        """
        打开自定义语言设置对话框
        :param parent_window: 父窗口
        :param update_callback: 更新回调函数，用于更新主窗口的语言下拉框
        """
        dialog = tk.Toplevel(parent_window)
        dialog.title("自定义编程语言")
        dialog.geometry("600x400")
        dialog.resizable(True, True)
        dialog.transient(parent_window)
        dialog.grab_set()

        # 设置窗口居中
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'{width}x{height}+{x}+{y}')

        # 创建主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 当前自定义语言列表标题
        ttk.Label(main_frame, text="当前自定义语言:", font=('TkDefaultFont', 11, 'bold')).pack(
            anchor=tk.W, pady=(0, 10)
        )

        # 自定义语言列表框
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 创建列表框和滚动条
        language_listbox = tk.Listbox(
            list_frame,
            height=8,
            selectmode=tk.SINGLE
        )

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=language_listbox.yview)
        language_listbox.config(yscrollcommand=scrollbar.set)

        language_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def refresh_listbox():
            """刷新列表框"""
            language_listbox.delete(0, tk.END)
            # 按首字母排序显示
            sorted_languages = sorted(self.custom_languages, key=lambda x: x.lower())
            for lang in sorted_languages:
                language_listbox.insert(tk.END, lang)

        # 初始化列表框
        refresh_listbox()

        def delete_language():
            """删除选中的语言"""
            selection = language_listbox.curselection()
            if not selection:
                messagebox.showwarning("选择错误", "请先选择一个要删除的语言！")
                return

            index = selection[0]
            language_to_delete = language_listbox.get(index)

            # 确认删除
            if not messagebox.askyesno("确认删除", f"确定要删除语言 '{language_to_delete}' 吗？"):
                return

            # 删除语言
            success, message = self.delete_language(language_to_delete)
            if success:
                # 更新列表框
                refresh_listbox()

                # 更新语言下拉框
                if update_callback:
                    update_callback()

                # 显示成功消息
                messagebox.showinfo("成功", message)
            else:
                messagebox.showwarning("删除失败", message)

        # 绑定Delete键删除
        def on_delete_key(event):
            """处理Delete键事件"""
            delete_language()

        language_listbox.bind('<Delete>', on_delete_key)
        language_listbox.bind('<KeyPress-Delete>', on_delete_key)

        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # 添加语言框架
        add_frame = ttk.Frame(main_frame)
        add_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(add_frame, text="添加新语言").pack(side=tk.LEFT, padx=(0, 5))

        new_language_var = tk.StringVar()
        new_language_entry = ttk.Entry(add_frame, textvariable=new_language_var, width=20)
        new_language_entry.pack(side=tk.LEFT, padx=(0, 10))
        new_language_entry.focus_set()

        def add_language():
            """添加新语言"""
            new_lang = new_language_var.get().strip()

            success, message = self.add_language(new_lang)
            if success:
                # 更新列表框
                refresh_listbox()

                # 更新语言下拉框
                if update_callback:
                    update_callback()

                # 清空输入框
                new_language_var.set("")

                # 显示成功消息
                messagebox.showinfo("成功", message)
            else:
                if message != "已取消添加":  # 不显示用户取消的消息
                    messagebox.showwarning("添加失败", message)

        def edit_language():
            """编辑选中的语言"""
            selection = language_listbox.curselection()
            if not selection:
                messagebox.showwarning("选择错误", "请先选择一个要编辑的语言！")
                return

            index = selection[0]
            old_language = language_listbox.get(index)

            # 创建编辑对话框
            edit_dialog = tk.Toplevel(dialog)
            edit_dialog.title("编辑语言")
            edit_dialog.geometry("300x200")
            edit_dialog.resizable(True, True)
            edit_dialog.transient(dialog)
            edit_dialog.grab_set()

            # 居中显示
            edit_dialog.update_idletasks()
            width = edit_dialog.winfo_width()
            height = edit_dialog.winfo_height()
            x = (edit_dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (edit_dialog.winfo_screenheight() // 2) - (height // 2)
            edit_dialog.geometry(f'{width}x{height}+{x}+{y}')

            # 主框架
            edit_frame = ttk.Frame(edit_dialog, padding="20")
            edit_frame.pack(fill=tk.BOTH, expand=True)

            ttk.Label(edit_frame, text="修改语言名称:").pack(anchor=tk.W, pady=(0, 10))

            edit_language_var = tk.StringVar(value=old_language)
            edit_language_entry = ttk.Entry(edit_frame, textvariable=edit_language_var, width=25)
            edit_language_entry.pack(fill=tk.X, pady=(0, 20))
            edit_language_entry.focus_set()
            edit_language_entry.select_range(0, tk.END)

            def save_edit():
                """保存编辑"""
                new_lang = edit_language_var.get().strip()

                success, message = self.edit_language(old_language, new_lang)
                if success:
                    # 更新列表框
                    refresh_listbox()

                    # 更新语言下拉框
                    if update_callback:
                        update_callback()

                    # 关闭编辑对话框
                    edit_dialog.destroy()

                    # 显示成功消息
                    messagebox.showinfo("成功", message)
                else:
                    messagebox.showwarning("编辑失败", message)

            def cancel_edit():
                """取消编辑"""
                edit_dialog.destroy()

            # 按钮区域
            edit_button_frame = ttk.Frame(edit_frame)
            edit_button_frame.pack(fill=tk.X)

            ttk.Button(edit_button_frame, text="保存", command=save_edit, width=10).pack(
                side=tk.LEFT, padx=(0, 10)
            )
            ttk.Button(edit_button_frame, text="取消", command=cancel_edit, width=10).pack(side=tk.LEFT)

            # 绑定回车键
            edit_dialog.bind('<Return>', lambda event: save_edit())

        def close_dialog():
            """关闭对话框"""
            dialog.destroy()

        # 添加按钮
        add_button = ttk.Button(button_frame, text="添加", command=add_language, width=10)
        add_button.pack(side=tk.LEFT, padx=(0, 10))

        edit_button = ttk.Button(button_frame, text="编辑", command=edit_language, width=10)
        edit_button.pack(side=tk.LEFT, padx=(0, 10))

        delete_button = ttk.Button(button_frame, text="删除", command=delete_language, width=10)
        delete_button.pack(side=tk.LEFT, padx=(0, 10))

        close_button = ttk.Button(button_frame, text="关闭", command=close_dialog, width=10)
        close_button.pack(side=tk.LEFT)

        # 绑定回车键到添加按钮
        new_language_entry.bind('<Return>', lambda event: add_language())

        # 窗口关闭事件
        def on_closing():
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_closing)