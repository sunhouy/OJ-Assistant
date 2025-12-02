import os
import base64
import hashlib
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import secrets


class CryptoManager:
    def __init__(self):
        # 使用固定的盐值，这样每次加密结果相同
        # 也可以考虑将盐值与加密数据一起存储
        self.salt = b'educoder_assistant_salt_2024'
        
    def _derive_key(self, password: str) -> bytes:
        """从密码派生密钥"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(password.encode('utf-8'))
    
    def encrypt(self, plaintext: str, password: str) -> str:
        """
        加密文本
        
        Args:
            plaintext: 要加密的明文
            password: 加密密码
            
        Returns:
            Base64编码的加密数据
        """
        # 生成随机的IV
        iv = secrets.token_bytes(16)
        
        # 派生密钥
        key = self._derive_key(password)
        
        # 创建加密器
        cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # 加密数据
        plaintext_bytes = plaintext.encode('utf-8')
        ciphertext = encryptor.update(plaintext_bytes) + encryptor.finalize()
        
        # 组合IV和密文，并进行Base64编码
        combined = iv + ciphertext
        return base64.b64encode(combined).decode('utf-8')
    
    def decrypt(self, encrypted_data: str, password: str) -> str:
        """
        解密文本
        
        Args:
            encrypted_data: Base64编码的加密数据
            password: 解密密码
            
        Returns:
            解密后的明文
            
        Raises:
            ValueError: 当解密失败时
        """
        try:
            # 解码Base64数据
            combined = base64.b64decode(encrypted_data)
            
            # 提取IV和密文
            iv = combined[:16]
            ciphertext = combined[16:]
            
            # 派生密钥
            key = self._derive_key(password)
            
            # 创建解密器
            cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            
            # 解密数据
            plaintext_bytes = decryptor.update(ciphertext) + decryptor.finalize()
            return plaintext_bytes.decode('utf-8')
            
        except Exception as e:
            raise ValueError(f"解密失败: {str(e)}")
    
    def create_machine_specific_password(self) -> str:
        """
        创建基于机器特征的密码
        
        Returns:
            机器特定密码
        """
        # 使用机器相关信息生成密码
        import platform
        import socket
        
        machine_info = [
            platform.node(),  # 计算机名
            platform.system(),  # 操作系统
            platform.release(),  # 系统版本
        ]
        
        # 组合信息并生成哈希
        info_string = "_".join(machine_info)
        return hashlib.sha256(info_string.encode('utf-8')).hexdigest()[:16]


# 创建全局加密管理器实例
crypto_manager = CryptoManager()