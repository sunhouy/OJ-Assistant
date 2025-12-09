import configparser
import hashlib
import json
import os
import platform
import subprocess
import uuid
from pathlib import Path
from typing import Optional

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
        self.machine_id_file = os.path.join(self.data_dir, 'machine_id.bin')

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

    def _get_encryption_password(self, username: Optional[str] = None) -> str:
        """
        获取加密密码
        使用机器特定信息生成密码，确保同一台机器可以解密
        """
        machine_code = self.get_machine_code()

        # 如果提供了用户名，将其包含在密码生成中
        if username:
            info_string = f"{machine_code}_{username}"
        else:
            info_string = machine_code

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

    def _get_stable_machine_info(self):
        """获取稳定的机器信息，避免使用可变信息"""
        machine_info = []

        # 1. 操作系统信息 (相对稳定)
        system_info = platform.system()
        machine_info.append(f"system:{system_info}")

        # 2. 系统版本
        release_info = platform.release()
        machine_info.append(f"release:{release_info}")

        # 3. 机器架构
        machine_arch = platform.machine()
        machine_info.append(f"arch:{machine_arch}")

        # 4. 处理器信息 (相对稳定)
        try:
            processor_info = platform.processor()
            if processor_info:
                machine_info.append(f"processor:{processor_info}")
        except:
            pass

        # 5. Windows特定：获取主板序列号（比MAC地址更稳定）
        if system_info == "Windows":
            try:
                # 尝试获取主板信息
                result = subprocess.run(
                    ['wmic', 'baseboard', 'get', 'serialnumber'],
                    capture_output=True, text=True, shell=True
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        serial = lines[1].strip()
                        if serial and serial.lower() not in ['to be filled by o.e.m.', 'none', '']:
                            machine_info.append(f"motherboard:{serial}")
            except:
                pass

            # 获取BIOS序列号作为备选
            try:
                result = subprocess.run(
                    ['wmic', 'bios', 'get', 'serialnumber'],
                    capture_output=True, text=True, shell=True
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        serial = lines[1].strip()
                        if serial and serial.lower() not in ['to be filled by o.e.m.', 'none', '']:
                            machine_info.append(f"bios:{serial}")
            except:
                pass

        # 6. 使用Python安装路径的哈希（相对稳定）
        try:
            python_path = sys.executable if 'sys' in globals() else ''
            if python_path:
                python_path_hash = hashlib.md5(python_path.encode()).hexdigest()[:8]
                machine_info.append(f"python_path:{python_path_hash}")
        except:
            pass

        # 7. 用户目录的哈希（相对稳定）
        try:
            user_path = str(Path.home())
            user_path_hash = hashlib.md5(user_path.encode()).hexdigest()[:8]
            machine_info.append(f"user_path:{user_path_hash}")
        except:
            pass

        return "_".join(machine_info)

    def _get_or_create_machine_id(self):
        """获取或创建持久化的机器ID"""
        try:
            # 尝试从文件中读取已有的机器ID
            if os.path.exists(self.machine_id_file):
                with open(self.machine_id_file, 'r', encoding='utf-8') as f:
                    machine_id = f.read().strip()
                if machine_id and len(machine_id) >= 32:
                    return machine_id

            # 如果文件不存在或内容无效，创建新的机器ID
            # 使用稳定的机器信息生成ID
            stable_info = self._get_stable_machine_info()

            # 添加时间戳确保唯一性，但只使用一次
            import time
            timestamp = str(int(time.time() * 1000))

            # 生成机器ID
            combined_info = f"{stable_info}_{timestamp}_{uuid.uuid4()}"
            machine_id = hashlib.sha256(combined_info.encode('utf-8')).hexdigest()

            # 保存到文件
            with open(self.machine_id_file, 'w', encoding='utf-8') as f:
                f.write(machine_id)

            # 同时备份到配置文件
            config = configparser.ConfigParser()
            if os.path.exists(self.config_file):
                config.read(self.config_file, encoding='utf-8')

            if 'MACHINE' not in config:
                config['MACHINE'] = {}

            config['MACHINE']['machine_id'] = machine_id
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)

            print(f"已生成新的机器ID: {machine_id[:16]}...")
            return machine_id

        except Exception as e:
            print(f"获取或创建机器ID失败: {e}")
            # 失败时返回基于基本信息的后备ID
            fallback_info = f"{platform.node()}_{platform.system()}_{platform.release()}"
            return hashlib.sha256(fallback_info.encode()).hexdigest()

    def get_machine_code(self):
        """获取机器码，确保同一台电脑每次获取都相同"""
        try:
            # 首先尝试从配置文件读取
            config = configparser.ConfigParser()
            machine_code = None

            if os.path.exists(self.config_file):
                config.read(self.config_file, encoding='utf-8')
                if 'MACHINE' in config and 'machine_code' in config['MACHINE']:
                    machine_code = config['MACHINE']['machine_code']

            # 如果有保存的机器码，直接返回
            if machine_code and len(machine_code) == 64:  # SHA256哈希长度
                return machine_code

            # 如果没有，使用持久化的机器ID生成机器码
            machine_id = self._get_or_create_machine_id()

            # 使用机器ID生成最终的机器码
            final_machine_code = hashlib.sha256(machine_id.encode('utf-8')).hexdigest()

            # 保存到配置文件
            if 'MACHINE' not in config:
                config['MACHINE'] = {}

            config['MACHINE']['machine_code'] = final_machine_code
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)

            print(f"已生成机器码: {final_machine_code[:16]}...")
            return final_machine_code

        except Exception as e:
            print(f"获取机器码失败: {e}")
            # 失败时返回基于基本信息的后备机器码
            fallback_info = f"{platform.node()}_{platform.system()}_{platform.release()}"
            return hashlib.sha256(fallback_info.encode()).hexdigest()

    def save_machine_code(self, machine_code):
        """保存机器码到配置文件中"""
        try:
            config = configparser.ConfigParser()
            if os.path.exists(self.config_file):
                config.read(self.config_file, encoding='utf-8')

            # 确保MACHINE部分存在
            if 'MACHINE' not in config:
                config['MACHINE'] = {}

            # 保存机器码
            config['MACHINE']['machine_code'] = machine_code

            # 写入配置文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)

            print(f"已保存机器码: {machine_code[:16]}...")
            return True

        except Exception as e:
            print(f"保存机器码失败: {e}")
            return False

    def clear_welcome_flag(self):
        """清除欢迎对话框显示标志"""
        try:
            config = configparser.ConfigParser()
            if os.path.exists(self.config_file):
                config.read(self.config_file, encoding='utf-8')

            # 确保SETTINGS部分存在
            if 'SETTINGS' not in config:
                config['SETTINGS'] = {}

            # 设置不再显示欢迎对话框
            config['SETTINGS']['show_welcome'] = 'False'

            # 写入配置文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)

            return True

        except Exception as e:
            print(f"清除欢迎对话框标志失败: {e}")
            return False

    def get_machine_fingerprint_debug(self):
        """获取机器指纹信息（用于调试）"""
        try:
            # 返回当前使用的机器ID和机器码
            machine_id = self._get_or_create_machine_id()
            machine_code = self.get_machine_code()

            return {
                "machine_id": machine_id,
                "machine_code": machine_code,
                "stable_info": self._get_stable_machine_info(),
                "config_file_exists": os.path.exists(self.config_file),
                "machine_id_file_exists": os.path.exists(self.machine_id_file)
            }
        except Exception as e:
            return f"获取机器指纹失败: {e}"

    def reset_machine_code(self):
        """重置机器码（用于测试或重新生成）"""
        try:
            # 删除机器ID文件
            if os.path.exists(self.machine_id_file):
                os.remove(self.machine_id_file)

            # 从配置文件中删除机器码
            config = configparser.ConfigParser()
            if os.path.exists(self.config_file):
                config.read(self.config_file, encoding='utf-8')
                if 'MACHINE' in config:
                    if 'machine_code' in config['MACHINE']:
                        del config['MACHINE']['machine_code']
                    if 'machine_id' in config['MACHINE']:
                        del config['MACHINE']['machine_id']

                with open(self.config_file, 'w', encoding='utf-8') as f:
                    config.write(f)

            print("机器码已重置，下次将重新生成")
            return True

        except Exception as e:
            print(f"重置机器码失败: {e}")
            return False


# 全局配置管理器实例
config_manager = ConfigManager()

if __name__ == "__main__":
    # 测试机器码生成
    import sys

    print("测试机器码生成...")
    machine_code = config_manager.get_machine_code()
    print(f"机器码: {machine_code}")

    # 再次获取，应该相同
    machine_code2 = config_manager.get_machine_code()
    print(f"再次获取机器码: {machine_code2}")

    # 验证是否相同
    if machine_code == machine_code2:
        print("✓ 机器码生成成功，两次获取相同")
    else:
        print("✗ 机器码生成失败，两次获取不同")

    # 显示调试信息
    debug_info = config_manager.get_machine_fingerprint_debug()
    print("\n调试信息:")
    print(json.dumps(debug_info, indent=2, ensure_ascii=False))