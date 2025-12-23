"""
API接口测试工具
"""

import json

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


def display_menu():
    """显示主菜单"""
    print("\n" + "=" * 50)
    print("用户管理系统")
    print("=" * 50)
    print("1. 用户注册")
    print("2. 用户登录")
    print("3. 查询会员状态")
    print("4. 开通会员")
    print("5. 管理员登录")
    print("6. 管理员查询所有用户")
    print("7. 管理员添加授权码")
    print("0. 退出程序")
    print("=" * 50)


def print_result(result):
    """格式化打印结果"""
    print("\n" + "=" * 50)
    print("返回结果：")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("=" * 50)


def main():
    client = UserClient(BASE_URL)

    while True:
        display_menu()
        choice = input("\n请选择操作 (0-7): ").strip()

        if choice == "0":
            print("感谢使用，再见！")
            break

        elif choice == "1":
            print("\n=== 用户注册 ===")
            username = input("请输入用户名: ").strip()
            password = input("请输入密码: ").strip()
            confirm_password = input("请确认密码: ").strip()

            if password != confirm_password:
                print("错误：两次输入的密码不一致！")
                continue

            machine_code = input("请输入机器码: ").strip()
            invite_code = input("请输入邀请码（可选，直接回车跳过）: ").strip()
            invite_code = invite_code if invite_code else None

            print("\n正在注册...")
            result = client.register(username, password, machine_code, invite_code)
            print_result(result)

        elif choice == "2":
            print("\n=== 用户登录 ===")
            username = input("请输入用户名: ").strip()
            password = input("请输入密码: ").strip()
            machine_code = input("请输入机器码: ").strip()

            print("\n正在登录...")
            result = client.login(username, password, machine_code)
            print_result(result)

        elif choice == "3":
            print("\n=== 查询会员状态 ===")
            username = input("请输入用户名: ").strip()
            machine_code = input("请输入机器码: ").strip()

            print("\n正在查询...")
            result = client.check_member_status(username, machine_code)
            print_result(result)

        elif choice == "4":
            print("\n=== 开通会员 ===")
            username = input("请输入用户名: ").strip()
            code = input("请输入授权码: ").strip()

            print("\n正在开通会员...")
            result = client.activate_member(username, code)
            print_result(result)

        elif choice == "5":
            print("\n=== 管理员登录 ===")
            username = input("请输入管理员用户名: ").strip()
            password = input("请输入管理员密码: ").strip()

            print("\n正在登录...")
            result = client.admin_login(username, password)
            print_result(result)

        elif choice == "6":
            print("\n=== 管理员查询所有用户 ===")
            username = input("请输入管理员用户名: ").strip()
            password = input("请输入管理员密码: ").strip()

            print("\n正在查询...")
            result = client.admin_get_users(username, password)
            print_result(result)

        elif choice == "7":
            print("\n=== 管理员添加授权码 ===")
            admin_username = input("请输入管理员用户名: ").strip()
            admin_password = input("请输入管理员密码: ").strip()
            code = input("请输入授权码: ").strip()
            member_days = input("请输入会员天数: ").strip()

            try:
                member_days = int(member_days)
            except ValueError:
                print("错误：会员天数必须是数字！")
                continue

            print("\n正在添加授权码...")
            result = client.add_authorization_code(admin_username, admin_password, code, member_days)
            print_result(result)

        else:
            print("无效选择，请重新输入！")

        # 询问是否继续
        if choice != "0":
            continue_choice = input("\n是否继续操作？(y/n): ").strip().lower()
            if continue_choice not in ['y', 'yes', '是', '']:
                print("感谢使用，再见！")
                break


# 使用示例
if __name__ == '__main__':
    main()