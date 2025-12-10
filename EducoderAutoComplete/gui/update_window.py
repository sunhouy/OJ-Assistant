import os
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from urllib.parse import urlparse

import requests

# 导入配置管理器
from utils.config import config_manager


class UpdateWindow:
    def __init__(self, root, update_data, current_version, on_update_complete=None):
        self.root = root
        self.update_data = update_data
        self.current_version = current_version
        self.on_update_complete = on_update_complete

        self.download_path = None
        self.is_downloading = False
        self.download_thread = None
        self.total_size = 0
        self.downloaded_size = 0
        self.download_start_time = 0

        # 获取数据目录并创建下载目录
        self.data_dir = config_manager.get_data_dir()
        self.downloads_dir = os.path.join(self.data_dir, "downloads")
        os.makedirs(self.downloads_dir, exist_ok=True)

        self.setup_ui()

    def setup_ui(self):
        """设置更新界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(
            main_frame,
            text="软件更新",
            font=("微软雅黑", 16, "bold")
        )
        title_label.pack(pady=(0, 20))

        # 版本信息框架
        info_frame = ttk.LabelFrame(main_frame, text="版本信息", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 15))

        # 当前版本
        ttk.Label(
            info_frame,
            text=f"当前版本: {self.current_version}",
            font=("微软雅黑", 10)
        ).pack(anchor=tk.W, pady=(0, 5))

        # 最新版本
        ttk.Label(
            info_frame,
            text=f"最新版本: {self.update_data.get('latest_version', '未知')}",
            font=("微软雅黑", 10, "bold")
        ).pack(anchor=tk.W, pady=(0, 10))

        # 更新内容
        update_content = self.update_data.get('update_content', '无更新内容')
        content_label = ttk.Label(
            info_frame,
            text=f"更新内容:\n{update_content}",
            font=("微软雅黑", 9),
            justify=tk.LEFT,
            wraplength=400
        )
        content_label.pack(anchor=tk.W, fill=tk.X)

        # 下载信息框架
        download_frame = ttk.LabelFrame(main_frame, text="下载进度", padding="10")
        download_frame.pack(fill=tk.X, pady=(0, 15))

        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            download_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))

        # 进度标签
        self.progress_label = ttk.Label(
            download_frame,
            text="准备下载...",
            font=("微软雅黑", 9)
        )
        self.progress_label.pack()

        # 文件大小信息
        self.size_label = ttk.Label(
            download_frame,
            text="文件大小: 计算中...",
            font=("微软雅黑", 9)
        )
        self.size_label.pack()

        # 下载速度信息
        self.speed_label = ttk.Label(
            download_frame,
            text="速度: 0 KB/s",
            font=("微软雅黑", 9)
        )
        self.speed_label.pack()

        # 下载目录信息
        ttk.Label(
            download_frame,
            text=f"下载目录: {self.downloads_dir}",
            font=("微软雅黑", 8),
            foreground="gray"
        ).pack(pady=(5, 0))

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        # 下载按钮
        self.download_button = ttk.Button(
            button_frame,
            text="开始下载",
            command=self.start_download,
            width=15
        )
        self.download_button.pack(side=tk.LEFT, padx=(0, 10))

        # 运行按钮（初始禁用）
        self.run_button = ttk.Button(
            button_frame,
            text="运行更新程序",
            command=self.run_update,
            width=15,
            state="disabled"
        )
        self.run_button.pack(side=tk.LEFT)

        # 打开下载目录按钮
        self.open_dir_button = ttk.Button(
            button_frame,
            text="打开下载目录",
            command=self.open_downloads_dir,
            width=15
        )
        self.open_dir_button.pack(side=tk.LEFT, padx=(10, 0))

        # 强制更新提示
        if self.update_data.get('force_update', 0) == 1:
            warning_label = ttk.Label(
                main_frame,
                text="⚠ 此为强制更新，必须更新后才能继续使用软件",
                font=("微软雅黑", 10, "bold"),
                foreground="red"
            )
            warning_label.pack(pady=(15, 0))

        # 开始获取文件大小
        threading.Thread(target=self.get_file_size, daemon=True).start()

    def get_file_size(self):
        """获取文件大小"""
        download_url = self.update_data.get('download_url')
        if not download_url:
            print("[ERROR] 下载地址为空")
            self.root.after(0, lambda: self.size_label.config(text="文件大小: 未知"))
            return

        try:
            print(f"[INFO] 开始获取文件大小: {download_url}")
            response = requests.head(download_url, timeout=10)
            print(f"[INFO] 文件大小响应状态码: {response.status_code}")

            if response.status_code == 200:
                size = response.headers.get('Content-Length')
                if size:
                    self.total_size = int(size)
                    size_mb = self.total_size / (1024 * 1024)
                    print(f"[INFO] 文件大小: {size_mb:.2f} MB ({self.total_size} bytes)")
                    self.root.after(0, lambda: self.size_label.config(
                        text=f"文件大小: {size_mb:.2f} MB"
                    ))
                else:
                    print("[WARN] 无法获取文件大小: Content-Length 为空")
                    self.root.after(0, lambda: self.size_label.config(
                        text="文件大小: 未知"
                    ))
            else:
                print(f"[ERROR] 获取文件大小失败，状态码: {response.status_code}")
                self.root.after(0, lambda: self.size_label.config(
                    text="文件大小: 获取失败"
                ))
        except requests.exceptions.Timeout:
            print("[ERROR] 获取文件大小超时")
            self.root.after(0, lambda: self.size_label.config(
                text="文件大小: 获取超时"
            ))
        except requests.exceptions.ConnectionError:
            print("[ERROR] 获取文件大小连接错误")
            self.root.after(0, lambda: self.size_label.config(
                text="文件大小: 连接错误"
            ))
        except Exception as e:
            print(f"[ERROR] 获取文件大小异常: {str(e)}")
            self.root.after(0, lambda: self.size_label.config(
                text=f"文件大小: 获取失败 ({str(e)})"
            ))

    def start_download(self):
        """开始下载更新文件"""
        if self.is_downloading:
            print("[WARN] 下载正在进行中")
            return

        download_url = self.update_data.get('download_url')
        if not download_url:
            print("[ERROR] 下载地址无效")
            messagebox.showerror("错误", "下载地址无效")
            return

        # 解析文件名
        parsed_url = urlparse(download_url)
        filename = os.path.basename(parsed_url.path)
        if not filename:
            filename = "update_win64.exe"

        # 设置下载路径（使用数据目录下的downloads子目录）
        self.download_path = os.path.join(self.downloads_dir, filename)
        print(f"[INFO] 下载路径: {self.download_path}")

        # 如果文件已存在，询问是否覆盖
        if os.path.exists(self.download_path):
            response = messagebox.askyesno("文件已存在",
                f"文件 '{filename}' 已存在，是否覆盖？\n\n路径: {self.download_path}")
            if not response:
                print("[INFO] 用户取消覆盖，重新生成文件名")
                # 生成带时间戳的新文件名
                name, ext = os.path.splitext(filename)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"{name}_{timestamp}{ext}"
                self.download_path = os.path.join(self.downloads_dir, filename)
                print(f"[INFO] 新下载路径: {self.download_path}")

        # 禁用下载按钮
        self.download_button.config(state="disabled")
        self.is_downloading = True
        self.downloaded_size = 0
        self.download_start_time = time.time()

        # 重置进度条
        self.progress_var.set(0)

        # 在新线程中下载
        self.download_thread = threading.Thread(target=self.download_file, args=(download_url,), daemon=True)
        self.download_thread.start()
        print("[INFO] 开始下载线程")

    def download_file(self, url):
        """下载文件"""
        last_update_time = time.time()
        last_downloaded = 0

        try:
            print(f"[INFO] 开始下载: {url}")
            self.root.after(0, lambda: self.progress_label.config(text="正在连接服务器..."))

            # 设置超时参数
            timeout_config = (10, 30)  # 连接超时10秒，读取超时30秒
            response = requests.get(url, stream=True, timeout=timeout_config)
            response.raise_for_status()

            print(f"[INFO] 连接成功，状态码: {response.status_code}")

            # 获取文件总大小
            content_length = response.headers.get('content-length')
            if content_length:
                self.total_size = int(content_length)
                print(f"[INFO] 文件总大小: {self.total_size} bytes")

            # 创建文件
            with open(self.download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not self.is_downloading:
                        print("[INFO] 下载被用户取消")
                        break

                    if chunk:
                        f.write(chunk)
                        self.downloaded_size += len(chunk)

                        # 每秒更新一次UI，避免过于频繁
                        current_time = time.time()
                        if current_time - last_update_time >= 0.1:  # 每0.1秒更新一次
                            # 计算下载速度
                            speed = (self.downloaded_size - last_downloaded) / (current_time - last_update_time)
                            last_downloaded = self.downloaded_size
                            last_update_time = current_time

                            # 更新进度
                            self.root.after(0, lambda: self.update_progress(self.downloaded_size, speed))

            if self.is_downloading:
                # 下载完成
                print("[INFO] 下载完成")
                self.root.after(0, self.on_download_complete)
            else:
                # 下载被取消
                print("[INFO] 下载已取消")
                self.root.after(0, lambda: self.on_download_cancelled())

        except requests.exceptions.Timeout:
            error_msg = "下载超时，请检查网络连接"
            print(f"[ERROR] {error_msg}")
            self.root.after(0, lambda: self.on_download_error(error_msg))
        except requests.exceptions.ConnectionError as e:
            error_msg = f"网络连接错误: {str(e)}"
            print(f"[ERROR] {error_msg}")
            self.root.after(0, lambda: self.on_download_error(error_msg))
        except requests.exceptions.RequestException as e:
            error_msg = f"下载请求失败: {str(e)}"
            print(f"[ERROR] {error_msg}")
            self.root.after(0, lambda: self.on_download_error(error_msg))
        except Exception as e:
            error_msg = f"下载失败: {str(e)}"
            print(f"[ERROR] {error_msg}")
            self.root.after(0, lambda: self.on_download_error(error_msg))

    def update_progress(self, downloaded, speed):
        """更新下载进度"""
        if self.total_size > 0:
            progress = (downloaded / self.total_size) * 100
            self.progress_var.set(progress)

            # 格式化大小显示
            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = self.total_size / (1024 * 1024)

            # 格式化速度显示
            if speed >= 1024 * 1024:
                speed_str = f"{speed / (1024 * 1024):.1f} MB/s"
            elif speed >= 1024:
                speed_str = f"{speed / 1024:.1f} KB/s"
            else:
                speed_str = f"{speed:.0f} B/s"

            # 计算剩余时间
            if speed > 0 and self.total_size > downloaded:
                remaining_bytes = self.total_size - downloaded
                remaining_seconds = remaining_bytes / speed

                if remaining_seconds >= 3600:
                    remaining_str = f"{remaining_seconds / 3600:.1f} 小时"
                elif remaining_seconds >= 60:
                    remaining_str = f"{remaining_seconds / 60:.1f} 分钟"
                else:
                    remaining_str = f"{remaining_seconds:.0f} 秒"

                progress_text = f"下载中: {progress:.1f}% ({downloaded_mb:.1f} MB / {total_mb:.1f} MB)\n速度: {speed_str} | 剩余时间: {remaining_str}"
            else:
                progress_text = f"下载中: {progress:.1f}% ({downloaded_mb:.1f} MB / {total_mb:.1f} MB)"

            self.progress_label.config(text=progress_text)
            self.speed_label.config(text=f"速度: {speed_str}")
        else:
            # 无法获取总大小的情况
            downloaded_mb = downloaded / (1024 * 1024)
            self.progress_label.config(text=f"已下载: {downloaded_mb:.1f} MB")

    def on_download_complete(self):
        """下载完成处理"""
        self.is_downloading = False

        # 确保进度条显示100%
        if self.total_size > 0:
            self.progress_var.set(100)

        self.progress_label.config(text="下载完成！")
        self.speed_label.config(text="速度: 完成")

        # 启用运行按钮
        self.run_button.config(state="normal")

        # 显示完成消息
        messagebox.showinfo("下载完成",
            f"更新文件下载完成！\n\n文件位置: {self.download_path}\n\n请点击'运行更新程序'进行安装。")

        print(f"[INFO] 下载完成，文件已保存到: {self.download_path}")

    def on_download_cancelled(self):
        """下载取消处理"""
        self.is_downloading = False
        self.progress_label.config(text="下载已取消")
        self.speed_label.config(text="速度: 已取消")

        # 重新启用下载按钮
        self.download_button.config(state="normal")

        print("[INFO] 下载已取消")

    def on_download_error(self, error_msg):
        """下载错误处理"""
        self.is_downloading = False
        self.progress_label.config(text="下载失败")
        self.speed_label.config(text="速度: 失败")

        # 重新启用下载按钮
        self.download_button.config(state="normal")

        # 显示错误消息
        messagebox.showerror("下载失败", error_msg)

        print(f"[ERROR] 下载失败: {error_msg}")

    def cancel_download(self):
        """取消下载"""
        if self.is_downloading:
            self.is_downloading = False
            print("[INFO] 正在取消下载...")

    def run_update(self):
        """运行更新程序"""
        if not self.download_path or not os.path.exists(self.download_path):
            print(f"[ERROR] 更新文件不存在: {self.download_path}")
            messagebox.showerror("错误", "更新文件不存在，请重新下载")
            return

        try:
            print(f"[INFO] 运行更新程序: {self.download_path}")
            # 运行更新程序
            subprocess.Popen([self.download_path], shell=True)
            print("[INFO] 更新程序已启动")

            # 执行更新完成回调
            if self.on_update_complete:
                print("[INFO] 调用更新完成回调")
                self.on_update_complete()
            else:
                messagebox.showinfo("成功", "更新程序已启动，请按照提示完成更新。")
                print("[INFO] 更新程序已启动，等待用户操作")

        except FileNotFoundError:
            error_msg = f"找不到文件: {self.download_path}"
            print(f"[ERROR] {error_msg}")
            messagebox.showerror("错误", error_msg)
        except PermissionError:
            error_msg = f"没有权限执行文件: {self.download_path}"
            print(f"[ERROR] {error_msg}")
            messagebox.showerror("错误", error_msg)
        except Exception as e:
            error_msg = f"运行更新程序失败: {str(e)}"
            print(f"[ERROR] {error_msg}")
            messagebox.showerror("错误", error_msg)

    def open_downloads_dir(self):
        """打开下载目录"""
        try:
            if os.path.exists(self.downloads_dir):
                if platform.system() == "Windows":
                    os.startfile(self.downloads_dir)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.Popen(["open", self.downloads_dir])
                else:  # Linux
                    subprocess.Popen(["xdg-open", self.downloads_dir])
                print(f"[INFO] 已打开下载目录: {self.downloads_dir}")
            else:
                messagebox.showinfo("提示", f"下载目录不存在: {self.downloads_dir}")
        except Exception as e:
            print(f"[ERROR] 打开下载目录失败: {str(e)}")
            messagebox.showerror("错误", f"打开下载目录失败: {str(e)}")


# 添加platform模块导入用于打开目录功能
import platform