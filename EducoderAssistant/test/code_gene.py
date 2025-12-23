"""
授权码在线注册工具
"""

import random
import string
import time
from typing import List, Dict

import requests

# API基础URL
BASE_URL = 'http://yhsun.cn/server/index.php'


class UserClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def register(self, username, password, machine_code, invite_code=None):
        """
        用户注册
        :param username: 用户名
        :param password: 密码
        :param machine_code: 机器码
        :param invite_code: 邀请码（可选）
        :return: 响应结果
        """
        url = f'{self.base_url}?action=register'
        data = {
            'username': username,
            'password': password,
            'machine_code': machine_code
        }
        if invite_code:
            data['invite_code'] = invite_code
        try:
            response = requests.post(url, json=data)
            return response.json()
        except Exception as e:
            return {
                'code': 500,
                'message': '请求失败',
                'error': str(e)
            }

    def login(self, username, password, machine_code):
        """
        用户登录
        :param username: 用户名
        :param password: 密码
        :param machine_code: 机器码
        :return: 响应结果
        """
        url = f'{self.base_url}?action=login'
        data = {
            'username': username,
            'password': password,
            'machine_code': machine_code
        }
        try:
            response = requests.post(url, json=data)
            return response.json()
        except Exception as e:
            return {
                'code': 500,
                'message': '请求失败',
                'error': str(e)
            }

    def check_member_status(self, username, machine_code):
        """
        查询会员状态
        :param username: 用户名
        :param machine_code: 机器码
        :return: 响应结果
        """
        url = f'{self.base_url}?action=check_member'
        data = {
            'username': username,
            'machine_code': machine_code
        }
        try:
            response = requests.post(url, json=data)
            return response.json()
        except Exception as e:
            return {
                'code': 500,
                'message': '请求失败',
                'error': str(e)
            }

    def admin_login(self, username, password):
        """
        管理员登录
        :param username: 管理员用户名
        :param password: 管理员密码
        :return: 响应结果
        """
        url = f'{self.base_url}?action=admin_login'
        data = {
            'username': username,
            'password': password
        }
        try:
            response = requests.post(url, json=data)
            return response.json()
        except Exception as e:
            return {
                'code': 500,
                'message': '请求失败',
                'error': str(e)
            }

    def admin_get_users(self, username, password):
        """
        管理员查询所有用户
        :param username: 管理员用户名
        :param password: 管理员密码
        :return: 响应结果
        """
        url = f'{self.base_url}?action=admin_get_users'
        data = {
            'username': username,
            'password': password
        }
        try:
            response = requests.post(url, json=data)
            return response.json()
        except Exception as e:
            return {
                'code': 500,
                'message': '请求失败',
                'error': str(e)
            }

    def add_authorization_code(self, admin_username, admin_password, code, member_days):
        """
        添加授权码（管理员功能）
        :param admin_username: 管理员用户名
        :param admin_password: 管理员密码
        :param code: 授权码
        :param member_days: 会员天数
        :return: 响应结果
        """
        url = f'{self.base_url}?action=add_auth_code'
        data = {
            'username': admin_username,
            'password': admin_password,
            'code': code,
            'member_days': member_days
        }
        try:
            response = requests.post(url, json=data)
            return response.json()
        except Exception as e:
            return {
                'code': 500,
                'message': '请求失败',
                'error': str(e)
            }

    def activate_member(self, username, code):
        """
        开通会员
        :param username: 用户名
        :param code: 授权码
        :return: 响应结果
        """
        url = f'{self.base_url}?action=activate_member'
        data = {
            'username': username,
            'code': code
        }
        try:
            response = requests.post(url, json=data)
            return response.json()
        except Exception as e:
            return {
                'code': 500,
                'message': '请求失败',
                'error': str(e)
            }


class AuthorizationCodeGenerator:
    """授权码生成器"""

    def __init__(self, client: UserClient):
        self.client = client

    def generate_code(self, length: int = 12) -> str:
        """
        生成随机授权码
        :param length: 授权码长度
        :return: 生成的授权码
        """
        # 使用大写字母和数字生成授权码
        chars = string.ascii_uppercase + string.digits
        # 避免使用容易混淆的字符 (0/O, 1/I等)
        chars = chars.replace('O', '').replace('0', '').replace('1', '').replace('I', '')

        # 生成授权码
        code = ''.join(random.choices(chars, k=length))
        return code

    def batch_generate_and_submit(self, admin_username: str, admin_password: str,
                                  count: int, member_days: int,
                                  code_prefix: str = "", code_length: int = 12) -> List[Dict]:
        """
        批量生成授权码并提交
        :param admin_username: 管理员用户名
        :param admin_password: 管理员密码
        :param count: 生成数量
        :param member_days: 会员天数
        :param code_prefix: 授权码前缀
        :param code_length: 授权码长度
        :return: 生成结果列表
        """
        results = []

        print(f"开始批量生成授权码...")
        print(f"生成数量: {count}")
        print(f"会员天数: {member_days}")
        print("-" * 50)

        for i in range(count):
            # 生成授权码
            if code_prefix:
                random_part = self.generate_code(code_length - len(code_prefix))
                code = f"{code_prefix}{random_part}"
            else:
                code = self.generate_code(code_length)

            # 提交到服务器
            print(f"正在生成第 {i + 1}/{count} 个授权码: {code}")
            result = self.client.add_authorization_code(
                admin_username,
                admin_password,
                code,
                member_days
            )

            # 记录结果
            result_info = {
                "code": code,
                "status": result.get('code', 500),
                "message": result.get('message', '未知错误'),
                "raw_response": result
            }
            results.append(result_info)

            # 添加短暂延迟，避免请求过于频繁
            if i < count - 1:
                time.sleep(0.5)

        return results

    def display_results(self, results: List[Dict]):
        """
        显示生成结果
        :param results: 生成结果列表
        """
        print("\n" + "=" * 50)
        print("授权码生成结果:")
        print("=" * 50)

        success_count = 0
        fail_count = 0

        for result in results:
            if result['status'] == 200:
                print(f"✓ {result['code']} - 成功")
                success_count += 1
            else:
                print(f"✗ {result['code']} - 失败: {result['message']}")
                fail_count += 1

        print("-" * 50)
        print(f"总计: {len(results)} 个")
        print(f"成功: {success_count} 个")
        print(f"失败: {fail_count} 个")

        # 导出成功的授权码
        if success_count > 0:
            self.export_successful_codes(results)

    def export_successful_codes(self, results: List[Dict]):
        """
        导出成功的授权码到文件
        :param results: 生成结果列表
        """
        successful_codes = [result['code'] for result in results if result['status'] == 200]

        if not successful_codes:
            return

        # 导出到文件
        filename = f"authorization_codes_{int(time.time())}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            for code in successful_codes:
                f.write(f"{code}\n")

        print(f"\n成功的授权码已导出到文件: {filename}")

        # 控制台输出
        print("\n所有生成的授权码（每行一个）:")
        print("-" * 30)
        for code in successful_codes:
            print(code)


def get_user_input() -> tuple:
    """
    获取用户输入
    :return: (管理员用户名, 管理员密码, 生成数量, 会员天数, 授权码前缀, 授权码长度)
    """
    print("批量授权码生成工具")
    print("=" * 40)

    # 获取管理员凭据
    admin_username = input("请输入管理员用户名: ").strip()
    admin_password = input("请输入管理员密码: ").strip()

    # 获取生成参数
    while True:
        try:
            count = int(input("请输入要生成的授权码数量: ").strip())
            if count <= 0:
                print("数量必须大于0，请重新输入！")
                continue
            break
        except ValueError:
            print("请输入有效的数字！")

    while True:
        try:
            member_days = int(input("请输入会员天数: ").strip())
            if member_days <= 0:
                print("天数必须大于0，请重新输入！")
                continue
            break
        except ValueError:
            print("请输入有效的数字！")

    # 可选：授权码前缀
    use_prefix = input("是否使用授权码前缀? (y/n, 默认n): ").strip().lower()
    code_prefix = ""
    if use_prefix == 'y':
        code_prefix = input("请输入授权码前缀: ").strip().upper()

    # 可选：授权码长度
    custom_length = input("是否自定义授权码长度? (y/n, 默认12): ").strip().lower()
    code_length = 12
    if custom_length == 'y':
        while True:
            try:
                code_length = int(input("请输入授权码长度: ").strip())
                if code_length < 6:
                    print("授权码长度至少6位，请重新输入！")
                    continue
                break
            except ValueError:
                print("请输入有效的数字！")

    return admin_username, admin_password, count, member_days, code_prefix, code_length


def main():
    """主函数"""
    # 创建客户端
    client = UserClient(BASE_URL)

    # 获取用户输入
    admin_username, admin_password, count, member_days, code_prefix, code_length = get_user_input()

    # 确认信息
    print(f"\n确认生成信息:")
    print(f"管理员: {admin_username}")
    print(f"生成数量: {count}")
    print(f"会员天数: {member_days}")
    if code_prefix:
        print(f"授权码前缀: {code_prefix}")
    print(f"授权码长度: {code_length}")

    confirm = input("\n确认开始生成? (y/n): ").strip().lower()
    if confirm != 'y':
        print("操作已取消")
        return

    # 创建生成器
    generator = AuthorizationCodeGenerator(client)

    # 批量生成
    try:
        results = generator.batch_generate_and_submit(
            admin_username, admin_password,
            count, member_days,
            code_prefix, code_length
        )

        # 显示结果
        generator.display_results(results)

    except KeyboardInterrupt:
        print("\n\n用户中断操作")
    except Exception as e:
        print(f"\n生成过程中发生错误: {str(e)}")

    input("\n按Enter键退出...")


if __name__ == '__main__':
    main()