import json
import os
import sys
import time
import uuid

import keyboard
import pyautogui
import requests

# 引入配置管理
from utils.config import ConfigManager


class ScreenshotClient:
    def __init__(self):
        self.base_url = "http://yhsun.cn/server/index.php"

        # 初始化配置管理器
        self.config_manager = ConfigManager()

        # 创建截图保存目录
        self.screenshots_dir = os.path.join(self.config_manager.get_data_dir(), "screenshots")
        os.makedirs(self.screenshots_dir, exist_ok=True)

        # 从配置文件加载用户会话
        self.user_session = self.config_manager.load_user_session()

        # 初始化用户信息
        self.username = ""
        self.machine_code = ""
        self.token = ""

        # 如果用户会话存在，提取用户信息
        if self.user_session:
            self.username = self.user_session.get('username', '')
            self.machine_code = self.user_session.get('machine_code', '')
            self.token = self.user_session.get('token', '')

        # 检查用户是否已登录
        if not self.username or not self.machine_code:
            print("错误：未检测到用户登录信息，请先运行主程序并登录")
            print("按任意键退出...")
            input()
            sys.exit(1)

    def take_screenshot(self):
        """
        截取当前屏幕
        :return: 截图文件路径
        """
        try:
            # 生成唯一文件名
            filename = f'screenshot_{uuid.uuid4()}.png'
            screenshot_path = os.path.join(self.screenshots_dir, filename)

            # 截取整个屏幕
            screenshot = pyautogui.screenshot()

            # 保存截图到用户数据目录
            screenshot.save(screenshot_path)

            print(f"截图已保存到: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            print(f"截图失败: {str(e)}")
            return None

    def upload_screenshot(self, screenshot_path):
        """
        上传截图到服务器
        :param screenshot_path: 截图文件路径
        :return: 上传结果
        """
        try:
            if not os.path.exists(screenshot_path):
                print("截图文件不存在")
                return False

            url = f'{self.base_url}?action=upload_screenshot'

            # 获取文件大小
            file_size = os.path.getsize(screenshot_path)
            print(f"文件大小: {file_size} bytes")

            # 读取文件内容到内存
            try:
                with open(screenshot_path, 'rb') as file:
                    file_content = file.read()
            except Exception as e:
                print(f"读取文件失败: {e}")
                return False

            # 准备上传数据
            files = {
                'screenshot': (os.path.basename(screenshot_path), file_content, 'application/octet-stream')
            }

            data = {
                'username': self.username,
                'machine_code': self.machine_code,
                # 'token': self.token  # 暂时注释掉token，因为服务器端可能不处理这个参数
            }

            # 打印调试信息
            print(f"上传URL: {url}")
            print(f"用户名: {self.username}")
            print(f"机器码: {self.machine_code}")

            # 发送上传请求
            response = requests.post(url, files=files, data=data, timeout=30)

            # 打印原始响应以便调试
            print(f"状态码: {response.status_code}")
            print(f"响应头: {response.headers}")
            print(f"原始响应内容: {response.text[:500]}...")  # 只打印前500字符

            # 尝试解析JSON
            try:
                result = response.json()
                print(f"解析后的JSON: {json.dumps(result, ensure_ascii=False)[:200]}")
            except json.JSONDecodeError as e:
                print(f"JSON解析失败: {e}")
                print(f"完整响应内容: {response.text}")
                return False

            if result.get('code') == 200:
                print(f"截图上传成功！文件URL: {result['data']['file_url']}")

                # 删除本地临时截图文件
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        os.remove(screenshot_path)
                        print("已删除本地临时文件")
                        break
                    except PermissionError as e:
                        if retry < max_retries - 1:
                            print(f"删除文件失败，重试中... ({retry + 1}/{max_retries})")
                            time.sleep(0.5)
                        else:
                            print(f"无法删除文件，文件可能被占用: {e}")
                            # 尝试重命名文件，标记为待删除
                            try:
                                temp_name = f"{screenshot_path}.deleted"
                                os.rename(screenshot_path, temp_name)
                                print(f"已重命名文件为: {temp_name}")
                            except Exception as rename_error:
                                print(f"重命名文件也失败: {rename_error}")
                    except Exception as e:
                        print(f"删除本地文件失败: {e}")
                        break

                return True
            else:
                error_msg = result.get('message', '未知错误')
                print(f"截图上传失败: {error_msg}")

                # 检查是否需要重新登录
                if result.get('code') == 401:  # 未授权
                    print("用户会话已过期，请重新登录")

                return False

        except requests.exceptions.Timeout:
            print("上传请求超时，请检查网络连接")
            return False
        except requests.exceptions.ConnectionError:
            print("网络连接错误，请检查网络连接")
            return False
        except Exception as e:
            print(f"上传请求失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def cleanup_old_screenshots(self, max_age_hours=24):
        """
        清理旧的截图文件
        :param max_age_hours: 最大保留时间（小时）
        """
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600

            for filename in os.listdir(self.screenshots_dir):
                filepath = os.path.join(self.screenshots_dir, filename)

                # 跳过目录和.deleted文件
                if os.path.isdir(filepath) or filename.endswith('.deleted'):
                    continue

                try:
                    # 获取文件创建时间
                    file_age = current_time - os.path.getctime(filepath)

                    # 如果文件超过指定时间，尝试删除
                    if file_age > max_age_seconds:
                        try:
                            os.remove(filepath)
                            print(f"已清理旧文件: {filename}")
                        except PermissionError:
                            # 如果无法删除，重命名为.deleted
                            os.rename(filepath, f"{filepath}.deleted")
                            print(f"重命名旧文件为: {filename}.deleted")
                except Exception as e:
                    print(f"处理文件 {filename} 时出错: {e}")
        except Exception as e:
            print(f"清理旧截图时出错: {e}")

    def on_shortcut_pressed(self):
        """
        快捷键被按下时的处理函数
        """
        print("检测到快捷键 Ctrl+Q，正在截图...")

        # 截图
        screenshot_path = self.take_screenshot()
        if screenshot_path:
            # 上传截图
            success = self.upload_screenshot(screenshot_path)
            if success:
                print("截图上传完成！")
            else:
                print("截图上传失败，文件已保存在本地")
        else:
            print("截图失败")

    def start_listening(self):
        """
        开始监听全局快捷键
        """
        print(f"截图客户端已启动，用户: {self.username}")
        print(f"截图保存目录: {self.screenshots_dir}")

        # 启动时清理旧文件
        self.cleanup_old_screenshots()

        print("按下 Ctrl+Q 进行截图并上传")
        print("按 Ctrl+C 退出程序")

        try:
            # 注册全局快捷键 Ctrl+Q
            keyboard.add_hotkey('ctrl+q', self.on_shortcut_pressed)

            # 保持程序运行
            keyboard.wait('ctrl+c')
        except KeyboardInterrupt:
            print("\n截图客户端已退出")
        except Exception as e:
            print(f"监听快捷键失败: {str(e)}")


if __name__ == '__main__':
    # 创建截图客户端实例
    client = ScreenshotClient()

    # 开始监听快捷键
    client.start_listening()