#!/usr/bin/env python3
"""
Python聊天客户端
连接服务器后获取一次性密码，等待网页用户连接
支持远程协助功能，监听8003端口接收前端消息
"""

import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime
from typing import Optional, Set

import websockets
from colorama import init, Fore, Style

# 初始化颜色输出
init(autoreset=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PythonChatClient:
    def __init__(self, server_host='101.200.216.53', server_port=8765, client_name=None):
        # 注意：server_host 不应该包含 http:// 前缀
        self.server_host = server_host
        self.server_port = server_port
        self.client_name = client_name or f"PythonClient-{uuid.uuid4().hex[:8]}"
        self.client_id = f"python-{uuid.uuid4().hex}"

        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.otp: Optional[str] = None
        self.paired = False
        self.web_client_id: Optional[str] = None
        self.running = True

        # 新增：远程协助相关
        self.remote_server = None
        self.remote_clients: Set[websockets.WebSocketServerProtocol] = set()

    async def connect(self):
        """连接到服务器"""
        try:
            uri = f"ws://{self.server_host}:{self.server_port}"
            logger.info(f"正在连接到服务器: {uri}")

            # 设置更长的超时时间
            self.websocket = await websockets.connect(
                uri,
                ping_interval=20,
                ping_timeout=60,
                close_timeout=60
            )

            # 发送注册信息（注意：服务器期望 'type' 字段为 'python' 或 'web'）
            await self.websocket.send(json.dumps({
                'type': 'python',  # 关键：必须是 'python' 不是 'register'
                'client_id': self.client_id,
                'name': self.client_name
            }))

            print(Fore.GREEN + f"\n✓ 已连接到服务器")
            print(Fore.CYAN + f"客户端ID: {self.client_id}")
            print(Fore.CYAN + f"客户端名称: {self.client_name}")
            print(Fore.YELLOW + f"远程协助服务器监听端口: 8003")

            # 启动心跳任务
            heartbeat_task = asyncio.create_task(self.send_heartbeat())

            # 开始处理消息
            await self.handle_messages()

            # 清理任务
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

        except Exception as e:
            logger.error(f"连接失败: {e}")
            print(Fore.RED + f"连接失败: {e}")
            if hasattr(e, 'strerror') and e.strerror:
                print(Fore.RED + f"错误详情: {e.strerror}")

    async def handle_messages(self):
        """处理来自服务器的消息"""
        try:
            while self.running and self.websocket and self.websocket.open:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=1.0
                    )
                    await self.process_message(message)
                except asyncio.TimeoutError:
                    # 超时正常，继续循环
                    continue
                except asyncio.CancelledError:
                    break

        except websockets.exceptions.ConnectionClosed as e:
            print(Fore.RED + f"\n✗ 连接已断开 (代码: {e.code}, 原因: {e.reason})")
            logger.info(f"WebSocket连接已关闭: {e}")
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
            print(Fore.RED + f"处理消息出错: {e}")

    async def process_message(self, message: str):
        """处理单条消息"""
        try:
            data = json.loads(message)
            message_type = data.get('type')

            if message_type == 'otp_generated':
                # 收到OTP
                self.otp = data.get('otp')
                expires_in = data.get('expires_in', 600)

                print(Fore.YELLOW + "\n" + "=" * 50)
                print(Fore.GREEN + "✨ 一次性密码已生成 ✨")
                print(Fore.CYAN + f"OTP: {self.otp}")
                print(Fore.CYAN + f"有效期: {expires_in}秒")
                print(Fore.YELLOW + "\n请使用此OTP在网页端登录:")
                print(Fore.WHITE + f"http://{self.server_host}:8080")
                print(Fore.YELLOW + "=" * 50 + "\n")

                # 开始等待连接
                print(Fore.CYAN + "⏳ 等待网页用户连接...")

            elif message_type == 'paired':
                # 与Web客户端配对成功
                self.paired = True
                self.web_client_id = data.get('web_client_id')

                print(Fore.GREEN + f"\n✓ 已与网页客户端 {self.web_client_id} 配对成功!")
                print(Fore.CYAN + "现在可以开始聊天了")
                print(Fore.CYAN + "输入消息并按Enter发送")
                print(Fore.CYAN + "输入 '/quit' 退出\n")

                # 启动用户输入处理
                asyncio.create_task(self.handle_user_input())

            elif message_type == 'message':
                # 收到聊天消息
                from_client = data.get('from', 'unknown')
                text = data.get('text', '')
                timestamp = data.get('timestamp', '')

                if from_client == 'web':
                    # 显示消息
                    time_str = ""
                    if timestamp:
                        try:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            time_str = dt.strftime("%H:%M:%S")
                        except:
                            time_str = timestamp

                    print(Fore.MAGENTA + f"\n[{time_str}] 网页用户: {text}")
                    # 重新显示输入提示
                    print(Fore.CYAN + "你: ", end="", flush=True)

            elif message_type == 'typing':
                # 显示对方正在输入
                is_typing = data.get('is_typing', False)
                if is_typing:
                    print(Fore.YELLOW + "\n📝 网页用户正在输入...", end="\r")
                else:
                    print(" " * 30, end="\r")

            elif message_type == 'disconnected':
                # 对方断开连接
                reason = data.get('message', '未知原因')
                print(Fore.RED + f"\n✗ {reason}")
                print(Fore.CYAN + "等待重新连接...")
                self.paired = False

            elif message_type == 'error':
                # 错误消息
                error_msg = data.get('message', '未知错误')
                print(Fore.RED + f"错误: {error_msg}")

            elif message_type == 'status_ack':
                # 心跳确认
                pass

        except json.JSONDecodeError as e:
            logger.warning(f"收到无效JSON: {message}, 错误: {e}")
            print(Fore.YELLOW + f"收到无法解析的消息: {message}")

    async def handle_user_input(self):
        """处理用户输入"""
        try:
            while self.paired and self.websocket and self.websocket.open:
                try:
                    # 使用异步方式读取输入
                    loop = asyncio.get_event_loop()
                    message = await loop.run_in_executor(
                        None,
                        input,
                        f"{Fore.CYAN}你: {Style.RESET_ALL}"
                    )

                    if not message.strip():
                        continue

                    # 检查退出命令
                    if message.strip().lower() in ['/quit', '/exit', '/q']:
                        print(Fore.YELLOW + "正在断开连接...")
                        self.running = False
                        await self.websocket.close(1000, "用户退出")
                        break

                    # 发送消息
                    if self.paired and self.websocket.open:
                        await self.websocket.send(json.dumps({
                            'type': 'message',
                            'text': message.strip()
                        }))

                except (EOFError, KeyboardInterrupt):
                    print(Fore.YELLOW + "\n正在断开连接...")
                    self.running = False
                    if self.websocket and self.websocket.open:
                        await self.websocket.close(1000, "用户退出")
                    break

        except Exception as e:
            logger.error(f"处理用户输入时出错: {e}")

    async def send_heartbeat(self):
        """发送心跳保持连接"""
        while self.running and self.websocket and self.websocket.open:
            try:
                await asyncio.sleep(30)  # 每30秒发送一次
                if self.websocket and self.websocket.open:
                    await self.websocket.send(json.dumps({
                        'type': 'status',
                        'status': 'alive',
                        'client_id': self.client_id
                    }))
                    logger.debug("发送心跳")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"发送心跳失败: {e}")
                break

    # 新增：远程协助相关方法
    async def start_remote_server(self, host='localhost', port=8003):
        """启动远程协助服务器"""

        async def handle_remote_client(websocket, path):
            """处理远程协助客户端连接"""
            self.remote_clients.add(websocket)
            client_address = websocket.remote_address
            print(Fore.GREEN + f"\n✓ 远程协助客户端已连接: {client_address}")

            try:
                # 发送确认消息
                await websocket.send(json.dumps({
                    'type': 'acknowledge',
                    'message': '远程协助连接成功',
                    'timestamp': datetime.now().isoformat()
                }))

                # 监听客户端消息
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        message_type = data.get('type')

                        # 根据消息类型处理
                        if message_type == 'question_content':
                            content = data.get('content', {})
                            print(Fore.YELLOW + "\n" + "=" * 50)
                            print(Fore.GREEN + "📝 收到题目内容")
                            print(Fore.CYAN + f"URL: {content.get('url', '未知')}")
                            print(Fore.CYAN + f"元素数量: {content.get('element_count', 0)}")
                            print(Fore.CYAN + f"字符数: {content.get('char_count', 0)}")
                            print(Fore.WHITE + f"内容预览:\n{content.get('text_preview', '')}")
                            print(Fore.YELLOW + "=" * 50)

                            # 转发给聊天服务器
                            if self.websocket and self.websocket.open:
                                await self.websocket.send(json.dumps({
                                    'type': 'message',
                                    'text': f"📝 收到题目内容：{content.get('text_preview', '')[:50000]}..."
                                }))

                        elif message_type == 'test_results':
                            results = data.get('results', {})
                            print(Fore.YELLOW + "\n" + "=" * 50)
                            print(Fore.RED + "⚠️ 收到测试结果")
                            print(Fore.CYAN + f"元素数量: {results.get('element_count', 0)}")
                            print(Fore.CYAN + f"字符数: {results.get('char_count', 0)}")
                            print(Fore.WHITE + f"结果预览:\n{results.get('text_preview', '')[:500]}")
                            print(Fore.YELLOW + "=" * 50)

                            # 转发给聊天服务器
                            if self.websocket and self.websocket.open:
                                await self.websocket.send(json.dumps({
                                    'type': 'message',
                                    'text': f"⚠️ 收到测试结果：{results.get('text_preview', '')[:50000]}..."
                                }))

                        elif message_type == 'test_failures':
                            print(Fore.YELLOW + "\n" + "=" * 50)
                            print(Fore.RED + "❌ 收到测试失败信息")
                            print(Fore.CYAN + f"失败数量: {data.get('failure_count', 0)}")
                            print(Fore.WHITE + f"失败预览:\n{data.get('failures_preview', '')[:500]}")
                            print(Fore.YELLOW + "=" * 50)

                        elif message_type == 'test_success':
                            print(Fore.YELLOW + "\n" + "=" * 50)
                            print(Fore.GREEN + "✅ 所有测试通过")
                            print(Fore.YELLOW + "=" * 50)

                        elif message_type == 'code_generated':
                            print(Fore.YELLOW + "\n" + "=" * 50)
                            print(Fore.GREEN + "💾 代码已生成")
                            print(Fore.WHITE + f"代码预览:\n{data.get('code', '')[:500]}")
                            print(Fore.YELLOW + "=" * 50)

                        elif message_type == 'code_revised':
                            print(Fore.YELLOW + "\n" + "=" * 50)
                            print(Fore.BLUE + "🔄 代码已修正")
                            print(Fore.CYAN + f"重试次数: {data.get('retry_count', 0)}")
                            print(Fore.WHITE + f"代码预览:\n{data.get('code_preview', '')[:500]}")
                            print(Fore.YELLOW + "=" * 50)

                        elif message_type == 'input_complete':
                            print(Fore.YELLOW + "\n" + "=" * 50)
                            print(Fore.GREEN + "✅ 代码输入完成")
                            print(Fore.YELLOW + "=" * 50)

                        elif message_type == 'input_cancelled':
                            print(Fore.YELLOW + "\n" + "=" * 50)
                            print(Fore.RED + "❌ 代码输入已取消")
                            print(Fore.CYAN + f"原因: {data.get('reason', '未知')}")
                            print(Fore.YELLOW + "=" * 50)

                        elif message_type == 'input_error':
                            print(Fore.YELLOW + "\n" + "=" * 50)
                            print(Fore.RED + "❌ 代码输入错误")
                            print(Fore.CYAN + f"错误: {data.get('message', '未知')}")
                            print(Fore.YELLOW + "=" * 50)

                        else:
                            print(Fore.CYAN + f"\n收到远程消息: {data}")

                    except json.JSONDecodeError:
                        print(Fore.YELLOW + f"\n收到非JSON远程消息: {message}")

            except websockets.exceptions.ConnectionClosed:
                print(Fore.RED + f"\n✗ 远程协助客户端断开: {client_address}")
            except Exception as e:
                print(Fore.RED + f"\n处理远程客户端时出错: {e}")
            finally:
                self.remote_clients.remove(websocket)

        # 启动远程协助服务器
        try:
            self.remote_server = await websockets.serve(
                handle_remote_client,
                host,
                port
            )
            print(Fore.GREEN + f"远程协助服务器已启动，监听 {host}:{port}")
            return self.remote_server
        except Exception as e:
            print(Fore.RED + f"启动远程协助服务器失败: {e}")
            return None

    async def broadcast_to_remote_clients(self, message):
        """向所有远程协助客户端广播消息"""
        if not self.remote_clients:
            return

        disconnected_clients = set()
        for client in self.remote_clients:
            try:
                await client.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                print(Fore.RED + f"向远程客户端发送消息失败: {e}")
                disconnected_clients.add(client)

        # 移除断开连接的客户端
        for client in disconnected_clients:
            self.remote_clients.remove(client)

    async def run(self):
        """运行客户端"""
        try:
            print(Fore.BLUE + """
    ====================================
        Python 聊天客户端（带远程协助）
    ====================================
            """)

            print(Fore.CYAN + f"服务器: {self.server_host}:{self.server_port}")
            print(Fore.CYAN + f"客户端ID: {self.client_id}")
            print(Fore.CYAN + f"客户端名称: {self.client_name}")

            # 启动远程协助服务器
            remote_server_task = asyncio.create_task(self.start_remote_server())

            print(Fore.YELLOW + "\n正在连接到服务器...")

            # 连接服务器
            await self.connect()

            # 等待远程服务器关闭（理论上不会发生，除非出错）
            await remote_server_task

        except KeyboardInterrupt:
            print(Fore.YELLOW + "\n客户端关闭")
        except Exception as e:
            logger.error(f"客户端运行失败: {e}")
            print(Fore.RED + f"错误: {e}")
        finally:
            self.running = False

            # 关闭远程协助服务器
            if self.remote_server:
                self.remote_server.close()
                await self.remote_server.wait_closed()

            # 关闭所有远程客户端连接
            for client in self.remote_clients:
                await client.close()

            # 关闭主连接
            if self.websocket and not self.websocket.closed:
                await self.websocket.close()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='Python聊天客户端（带远程协助）')
    parser.add_argument('--host', default='101.200.216.53', help='服务器地址')
    parser.add_argument('--port', type=int, default=8765, help='服务器端口')
    parser.add_argument('--name', help='客户端名称')
    parser.add_argument('--remote-port', type=int, default=8003, help='远程协助端口')

    args = parser.parse_args()

    # 清理主机地址（移除可能的协议前缀）
    host = args.host.strip()
    if host.startswith('http://'):
        host = host[7:]
    elif host.startswith('https://'):
        host = host[8:]
    if host.endswith('/'):
        host = host[:-1]

    client = PythonChatClient(
        server_host=host,  # 使用清理后的主机地址
        server_port=args.port,
        client_name=args.name
    )

    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n已退出")
    except Exception as e:
        print(Fore.RED + f"运行错误: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())