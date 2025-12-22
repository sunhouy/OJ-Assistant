"""
模型管理工具
"""

import json
import os
import sys

import requests

# API接口基础URL
BASE_URL = 'http://yhsun.cn/server/api_manager_interface.php'

# 管理员认证信息
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = '127127sun'

# 认证参数，用于需要认证的请求
auth = (ADMIN_USERNAME, ADMIN_PASSWORD)


def add_api_info(model, base_url, api_key):
    """添加API信息"""
    url = f'{BASE_URL}?path=add_api'
    data = {
        'model': model,
        'base_url': base_url,
        'api_key': api_key
    }
    response = requests.post(url, json=data)
    return response.json()


def set_preferred_model(model):
    """设置首选模型"""
    url = f'{BASE_URL}?path=set_preferred_model'
    data = {'model': model}
    response = requests.post(url, json=data, auth=auth)
    return response.json()


def get_preferred_model():
    """获取首选模型"""
    url = f'{BASE_URL}?path=preferred_model'
    response = requests.get(url, auth=auth)
    return response.json()


def get_preferred_model_config():
    """获取首选模型配置"""
    url = f'{BASE_URL}?path=preferred_model_config'
    response = requests.get(url, auth=auth)
    return response.json()


def get_all_models():
    """获取所有模型"""
    url = f'{BASE_URL}?path=models'
    response = requests.get(url, auth=auth)
    return response.json()


def get_models_with_index():
    """获取带序号的模型列表"""
    url = f'{BASE_URL}?path=get_models_with_index'
    response = requests.get(url, auth=auth)
    return response.json()


def delete_model_by_index(index):
    """通过序号删除模型"""
    url = f'{BASE_URL}?path=delete_model'
    data = {'index': index}
    response = requests.post(url, json=data, auth=auth)
    return response.json()


def delete_model_by_details(model, base_url, api_key):
    """通过模型详细信息删除模型"""
    url = f'{BASE_URL}?path=delete_model'
    data = {
        'model': model,
        'base_url': base_url,
        'api_key': api_key
    }
    response = requests.post(url, json=data, auth=auth)
    return response.json()


def clear_screen():
    """清空屏幕"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_menu():
    """打印主菜单"""
    clear_screen()
    print("=" * 60)
    print("模型管理工具 - 交互式控制台")
    print("=" * 60)
    print("1. 添加新的API模型")
    print("2. 查看所有可用模型")
    print("3. 查看带序号的模型列表")
    print("4. 设置首选模型")
    print("5. 查看当前首选模型")
    print("6. 查看首选模型配置")
    print("7. 通过序号删除模型")
    print("8. 通过详细信息删除模型")
    print("9. 测试连接")
    print("0. 退出程序")
    print("=" * 60)


def print_result(title, result):
    """格式化打印结果"""
    print(f"\n{'=' * 40}")
    print(f"{title}")
    print(f"{'=' * 40}")

    if isinstance(result, dict):
        # 美化打印JSON
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif isinstance(result, list):
        for i, item in enumerate(result, 1):
            if isinstance(item, dict):
                print(f"{i}. {json.dumps(item, indent=2, ensure_ascii=False)}")
            else:
                print(f"{i}. {item}")
    else:
        print(result)

    print(f"{'=' * 40}")


def add_model_interactive():
    """交互式添加模型"""
    print("\n[添加新的API模型]")
    print("请输入以下信息：")

    model = input("模型名称 (如: gpt-4o, claude-3-opus): ").strip()
    if not model:
        print("❌ 模型名称不能为空！")
        return

    base_url = input("API基础URL (如: https://api.openai.com/v1): ").strip()
    if not base_url:
        print("❌ API基础URL不能为空！")
        return

    # 修改为普通输入，不再使用getpass
    api_key = input("API密钥: ").strip()
    if not api_key:
        print("❌ API密钥不能为空！")
        return

    print(f"\n正在添加模型 '{model}'...")
    try:
        result = add_api_info(model, base_url, api_key)
        if result.get('success'):
            print(f"✅ 成功添加模型: {model}")
        else:
            print(f"❌ 添加失败: {result.get('message', '未知错误')}")
    except Exception as e:
        print(f"❌ 发生错误: {e}")

    input("\n按回车键继续...")


def view_all_models():
    """查看所有模型"""
    print("\n[所有可用模型]")
    try:
        result = get_all_models()
        if result:
            print_result("所有可用模型", result)
        else:
            print("⚠️ 没有找到任何模型")
    except Exception as e:
        print(f"❌ 发生错误: {e}")

    input("\n按回车键继续...")


def view_models_with_index():
    """查看带序号的模型列表"""
    print("\n[带序号的模型列表]")
    try:
        result = get_models_with_index()
        if result:
            print_result("带序号的模型列表", result)
        else:
            print("⚠️ 没有找到任何模型")
    except Exception as e:
        print(f"❌ 发生错误: {e}")

    input("\n按回车键继续...")


def set_preferred_model_interactive():
    """交互式设置首选模型"""
    print("\n[设置首选模型]")

    # 先获取所有模型
    try:
        models_result = get_all_models()
        if not models_result:
            print("⚠️ 没有可用的模型，请先添加模型")
            input("\n按回车键继续...")
            return

        print("当前可用模型:")
        for i, model in enumerate(models_result, 1):
            print(f"{i}. {model}")

        model_input = input("\n请输入要设为首选的模型名称或序号: ").strip()

        # 检查输入是否为数字（序号）
        if model_input.isdigit():
            index = int(model_input) - 1
            if 0 <= index < len(models_result):
                model_name = models_result[index]
            else:
                print("❌ 序号无效！")
                input("\n按回车键继续...")
                return
        else:
            model_name = model_input

        # 验证模型是否存在
        if model_name not in models_result:
            print(f"❌ 模型 '{model_name}' 不存在！")
            input("\n按回车键继续...")
            return

        print(f"\n正在将 '{model_name}' 设为首选模型...")
        result = set_preferred_model(model_name)

        if result.get('success'):
            print(f"✅ 成功设置 '{model_name}' 为首选模型")
        else:
            print(f"❌ 设置失败: {result.get('message', '未知错误')}")

    except Exception as e:
        print(f"❌ 发生错误: {e}")

    input("\n按回车键继续...")


def view_preferred_model():
    """查看当前首选模型"""
    print("\n[当前首选模型]")
    try:
        result = get_preferred_model()
        print_result("首选模型", result)
    except Exception as e:
        print(f"❌ 发生错误: {e}")

    input("\n按回车键继续...")


def view_preferred_model_config():
    """查看首选模型配置"""
    print("\n[首选模型配置]")
    try:
        result = get_preferred_model_config()
        print_result("首选模型配置", result)
    except Exception as e:
        print(f"❌ 发生错误: {e}")

    input("\n按回车键继续...")


def delete_model_by_index_interactive():
    """交互式通过序号删除模型"""
    print("\n[通过序号删除模型]")

    try:
        # 先获取带序号的模型列表
        models_result = get_models_with_index()
        if not models_result:
            print("⚠️ 没有可删除的模型")
            input("\n按回车键继续...")
            return

        print("当前可用模型:")
        print_result("带序号的模型列表", models_result)

        index_input = input("\n请输入要删除的模型序号: ").strip()

        if not index_input.isdigit():
            print("❌ 请输入有效的数字序号！")
            input("\n按回车键继续...")
            return

        index = int(index_input)

        # 确认删除
        confirm = input(f"⚠️ 确认删除序号 {index} 的模型吗？(y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ 删除操作已取消")
            input("\n按回车键继续...")
            return

        print(f"\n正在删除序号为 {index} 的模型...")
        result = delete_model_by_index(index)

        if result.get('success'):
            print("✅ 删除成功")
        else:
            print(f"❌ 删除失败: {result.get('message', '未知错误')}")

    except Exception as e:
        print(f"❌ 发生错误: {e}")

    input("\n按回车键继续...")


def delete_model_by_details_interactive():
    """交互式通过详细信息删除模型"""
    print("\n[通过详细信息删除模型]")

    try:
        # 先获取所有模型
        models_result = get_all_models()
        if not models_result:
            print("⚠️ 没有可删除的模型")
            input("\n按回车键继续...")
            return

        print("当前可用模型:")
        for i, model in enumerate(models_result, 1):
            print(f"{i}. {model}")

        print("\n请输入要删除的模型的详细信息：")
        model = input("模型名称: ").strip()
        base_url = input("API基础URL: ").strip()

        # 修改为普通输入，不再使用getpass
        api_key = input("API密钥: ").strip()

        if not all([model, base_url, api_key]):
            print("❌ 所有字段都必须填写！")
            input("\n按回车键继续...")
            return

        # 确认删除
        confirm = input(f"\n⚠️ 确认删除模型 '{model}' 吗？(y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ 删除操作已取消")
            input("\n按回车键继续...")
            return

        print(f"\n正在删除模型 '{model}'...")
        result = delete_model_by_details(model, base_url, api_key)

        if result.get('success'):
            print("✅ 删除成功")
        else:
            print(f"❌ 删除失败: {result.get('message', '未知错误')}")

    except Exception as e:
        print(f"❌ 发生错误: {e}")

    input("\n按回车键继续...")


def test_connection():
    """测试连接"""
    print("\n[测试连接]")

    try:
        print("1. 测试基础连接...")
        response = requests.get(BASE_URL)
        if response.status_code == 200:
            print("✅ 基础连接正常")
        else:
            print(f"❌ 基础连接失败: 状态码 {response.status_code}")

        print("\n2. 测试认证连接...")
        try:
            result = get_preferred_model()
            print("✅ 认证连接正常")
            print(f"   当前首选模型: {result}")
        except Exception as e:
            print(f"❌ 认证连接失败: {e}")

        print("\n3. 测试模型列表获取...")
        try:
            models = get_all_models()
            count = len(models) if models else 0
            print(f"✅ 成功获取模型列表 ({count} 个模型)")
        except Exception as e:
            print(f"❌ 获取模型列表失败: {e}")

    except Exception as e:
        print(f"❌ 连接测试失败: {e}")

    input("\n按回车键继续...")


def main():
    """主函数 - 交互式菜单"""
    print("模型管理工具已启动")
    print(f"服务器地址: {BASE_URL}")

    # 移除初始连接测试，直接进入菜单

    # 主循环
    while True:
        print_menu()

        choice = input("\n请选择操作 (0-9): ").strip()

        if choice == '0':
            print("\n感谢使用模型管理工具，再见！")
            break
        elif choice == '1':
            add_model_interactive()
        elif choice == '2':
            view_all_models()
        elif choice == '3':
            view_models_with_index()
        elif choice == '4':
            set_preferred_model_interactive()
        elif choice == '5':
            view_preferred_model()
        elif choice == '6':
            view_preferred_model_config()
        elif choice == '7':
            delete_model_by_index_interactive()
        elif choice == '8':
            delete_model_by_details_interactive()
        elif choice == '9':
            test_connection()
        else:
            print("❌ 无效选择，请重新输入")
            input("\n按回车键继续...")


def quick_start():
    """快速开始演示"""
    print("正在运行快速开始演示...\n")

    try:
        # 1. 查看当前状态
        print("1. 查看当前状态:")
        pref_model = get_preferred_model()
        print(f"   当前首选模型: {pref_model}")

        # 2. 查看所有模型
        print("\n2. 查看所有模型:")
        models = get_all_models()
        if models:
            print(f"   发现 {len(models)} 个模型:")
            for model in models:
                print(f"   - {model}")
        else:
            print("   没有找到任何模型")

        # 3. 查看带序号列表
        print("\n3. 查看带序号的模型列表:")
        models_with_index = get_models_with_index()
        if models_with_index:
            print(json.dumps(models_with_index, indent=2, ensure_ascii=False))
        else:
            print("   没有找到任何模型")

    except Exception as e:
        print(f"演示过程中发生错误: {e}")

    input("\n演示结束，按回车键进入主菜单...")


if __name__ == "__main__":
    try:
        # 检查是否提供了命令行参数
        if len(sys.argv) > 1:
            if sys.argv[1] == '--demo':
                quick_start()
            elif sys.argv[1] == '--help':
                print("""
模型管理工具 - 使用说明

用法:
  python script.py                  # 启动交互式菜单
  python script.py --demo          # 运行快速演示
  python script.py --help          # 显示此帮助信息

功能:
  - 添加和管理多个AI模型API
  - 设置和切换首选模型
  - 查看模型配置信息
  - 删除不需要的模型

配置:
  请在脚本开头修改以下配置:
    BASE_URL: API管理接口地址
    ADMIN_USERNAME: 管理员用户名
    ADMIN_PASSWORD: 管理员密码
                """)
                sys.exit(0)

        # 默认启动交互式菜单
        main()

    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"\n程序发生错误: {e}")
        input("\n按回车键退出...")