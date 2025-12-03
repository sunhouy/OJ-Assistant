import os
import configparser
import hashlib
import json
import sys
from pathlib import Path

from utils.crypto import crypto_manager


class ConfigManager:
    def __init__(self):
        # 获取 AppData 目录
        self.appdata_dir = self._get_appdata_dir()

        # 确保数据目录存在
        self.data_dir = os.path.join(self.appdata_dir, "EducoderAssistant")
        os.makedirs(self.data_dir, exist_ok=True)

        # 文件路径
        self.config_file = os.path.join(self.data_dir, 'config.ini')
        self.credentials_file = os.path.join(self.data_dir, 'credentials.bin')
        self.session_file = os.path.join(self.data_dir, 'session.bin')

        self._ensure_config()

    def _get_appdata_dir(self):
        """获取 AppData 目录路径"""
        # 获取 AppData/Roaming 目录
        appdata = os.getenv('APPDATA')
        if not appdata:
            # 如果 APPDATA 环境变量不存在，使用备用路径
            home = Path.home()
            appdata = str(home / 'AppData' / 'Roaming')

        return appdata

    def _ensure_config(self):
        """确保配置文件存在"""
        if not os.path.exists(self.config_file):
            config = configparser.ConfigParser()
            config['SETTINGS'] = {
                'show_welcome': 'True'
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)

    def _get_encryption_password(self, username=None) -> str:
        """
        获取加密密码
        使用机器特定信息生成密码，确保同一台机器可以解密
        """
        import platform

        machine_info = [
            platform.node(),  # 计算机名
            platform.system(),  # 操作系统
            platform.release(),  # 系统版本
        ]

        # 如果提供了用户名，将其包含在密码生成中
        if username:
            machine_info.append(username)

        # 组合信息并生成哈希
        info_string = "_".join(machine_info)
        return hashlib.sha256(info_string.encode('utf-8')).hexdigest()[:16]

    def should_show_welcome(self):
        """检查是否应该显示欢迎对话框"""
        config = configparser.ConfigParser()
        show_welcome = True

        try:
            if os.path.exists(self.config_file):
                config.read(self.config_file, encoding='utf-8')
                if 'SETTINGS' in config and 'show_welcome' in config['SETTINGS']:
                    show_welcome = config['SETTINGS'].getboolean('show_welcome')
        except Exception as e:
            print(f"读取配置失败: {e}")

        return show_welcome

    def load_credentials(self):
        """加载并解密凭据"""
        try:
            if os.path.exists(self.credentials_file):
                with open(self.credentials_file, "r", encoding="utf-8") as f:
                    encrypted_data = f.read().strip()

                if encrypted_data:
                    password = self._get_encryption_password()
                    decrypted_data = crypto_manager.decrypt(encrypted_data, password)
                    return json.loads(decrypted_data)
        except Exception as e:
            print(f"加载或解密凭据失败: {str(e)}")
        return None

    def save_credentials(self, credentials):
        """加密并保存凭据"""
        try:
            password = self._get_encryption_password()
            json_data = json.dumps(credentials)
            encrypted_data = crypto_manager.encrypt(json_data, password)

            with open(self.credentials_file, "w", encoding="utf-8") as f:
                f.write(encrypted_data)
            return True
        except Exception as e:
            print(f"加密或保存凭据失败: {str(e)}")
            return False

    def load_user_session(self):
        """加载用户会话"""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, "r", encoding="utf-8") as f:
                    encrypted_data = f.read().strip()

                if encrypted_data:
                    password = self._get_encryption_password()
                    decrypted_data = crypto_manager.decrypt(encrypted_data, password)
                    return json.loads(decrypted_data)
        except Exception as e:
            print(f"加载或解密会话失败: {str(e)}")
        return None

    def save_user_session(self, session_data):
        """保存用户会话"""
        try:
            password = self._get_encryption_password()
            if session_data:
                json_data = json.dumps(session_data)
                encrypted_data = crypto_manager.encrypt(json_data, password)
            else:
                encrypted_data = ""  # 清空会话

            with open(self.session_file, "w", encoding="utf-8") as f:
                f.write(encrypted_data)
            return True
        except Exception as e:
            print(f"加密或保存会话失败: {str(e)}")
            return False

    def load_api_key(self, username):
        """加载并解密API Key"""
        try:
            api_key_file = os.path.join(self.data_dir, f'api_key_{username}.bin')
            if os.path.exists(api_key_file):
                with open(api_key_file, "r", encoding="utf-8") as f:
                    encrypted_data = f.read().strip()

                if encrypted_data:
                    password = self._get_encryption_password(username)
                    return crypto_manager.decrypt(encrypted_data, password)
        except Exception as e:
            print(f"加载或解密API Key失败: {str(e)}")
        return None

    def save_api_key(self, api_key, username):
        """加密并保存API Key"""
        try:
            password = self._get_encryption_password(username)
            encrypted_data = crypto_manager.encrypt(api_key, password)

            api_key_file = os.path.join(self.data_dir, f'api_key_{username}.bin')
            with open(api_key_file, "w", encoding="utf-8") as f:
                f.write(encrypted_data)
            return True
        except Exception as e:
            print(f"加密或保存API Key失败: {str(e)}")
            return False

    def clear_api_key(self, username):
        """清除保存的API Key"""
        try:
            api_key_file = os.path.join(self.data_dir, f'api_key_{username}.bin')
            if os.path.exists(api_key_file):
                os.remove(api_key_file)
                return True
        except Exception as e:
            print(f"清除API Key失败: {str(e)}")
            return False

    def get_data_dir(self):
        """获取数据目录路径"""
        return self.data_dir