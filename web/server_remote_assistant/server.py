#!/usr/bin/env python3
"""
WebSocket 聊天服务器
支持一次性密码验证和双向消息转发
允许一个OTP被多个网页客户端使用
"""

import asyncio
import json
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Set

from aiohttp import web
from websockets import WebSocketServerProtocol
from websockets.server import serve

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class OTPToken:
    """一次性密码令牌"""
    token: str
    client_id: str
    created_at: datetime
    expires_at: datetime
    # 注意：移除了 used 字段，允许多次使用


@dataclass
class ChatClient:
    """聊天客户端"""
    websocket: WebSocketServerProtocol
    client_id: str
    client_type: str  # 'python' 或 'web'
    connected_at: datetime
    otp_token: Optional[str] = None


class ChatServer:
    def __init__(self, host='0.0.0.0', ws_port=8765, http_port=8080):
        self.host = host
        self.ws_port = ws_port
        self.http_port = http_port

        # 存储数据结构
        self.otp_tokens: Dict[str, OTPToken] = {}  # token -> OTPToken
        self.clients: Dict[str, ChatClient] = {}  # client_id -> ChatClient
        # 修改为一对多映射：一个Python客户端可以对应多个网页客户端
        self.paired_clients: Dict[str, Set[str]] = {}  # python_client_id -> set of web_client_ids

        # HTTP 服务器用于提供网页
        self.http_app = web.Application()
        self.setup_http_routes()

    def setup_http_routes(self):
        """设置HTTP路由"""
        # 提供网页客户端
        self.http_app.router.add_get('/', self.serve_web_client)
        self.http_app.router.add_get('/web_client.html', self.serve_web_client)
        self.http_app.router.add_static('/static', 'static')

        # API 端点
        self.http_app.router.add_post('/api/validate-otp', self.validate_otp_api)
        self.http_app.router.add_get('/api/status', self.server_status_api)

    async def serve_web_client(self, request):
        """提供网页客户端"""
        with open('web_client.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return web.Response(text=content, content_type='text/html')

    async def validate_otp_api(self, request):
        """验证OTP的API端点"""
        try:
            data = await request.json()
            otp = data.get('otp', '').strip()

            if not otp:
                return web.json_response({'valid': False, 'error': '请输入OTP'})

            token_info = self.otp_tokens.get(otp)
            if not token_info:
                return web.json_response({'valid': False, 'error': 'OTP无效或不存在'})

            # 移除了对 used 状态的检查，允许重复使用
            # if token_info.used:
            #     return web.json_response({'valid': False, 'error': 'OTP已被使用'})

            if datetime.now() > token_info.expires_at:
                return web.json_response({'valid': False, 'error': 'OTP已过期'})

            # 不再标记为已使用
            # token_info.used = True

            return web.json_response({
                'valid': True,
                'client_id': token_info.client_id,
                'expires_at': token_info.expires_at.isoformat()
            })

        except Exception as e:
            logger.error(f"验证OTP时出错: {e}")
            return web.json_response({'valid': False, 'error': '服务器错误'})

    async def server_status_api(self, request):
        """服务器状态API"""
        return web.json_response({
            'status': 'running',
            'clients_connected': len(self.clients),
            'active_tokens': len([t for t in self.otp_tokens.values()]),
            'paired_sessions': sum(len(web_clients) for web_clients in self.paired_clients.values())
        })

    def generate_otp(self, client_id: str) -> str:
        """生成一次性密码"""
        # 生成6位数字OTP
        otp = ''.join(secrets.choice('0123456789') for _ in range(6))

        # 清理过期的令牌
        self.cleanup_expired_tokens()

        # 创建令牌记录
        now = datetime.now()
        token_info = OTPToken(
            token=otp,
            client_id=client_id,
            created_at=now,
            expires_at=now + timedelta(minutes=100)
        )

        self.otp_tokens[otp] = token_info
        logger.info(f"为客户端 {client_id} 生成OTP: {otp}")

        return otp

    def cleanup_expired_tokens(self):
        """清理过期的令牌"""
        now = datetime.now()
        expired_tokens = [
            token for token, info in self.otp_tokens.items()
            if now > info.expires_at
        ]

        for token in expired_tokens:
            del self.otp_tokens[token]

        if expired_tokens:
            logger.info(f"清理了 {len(expired_tokens)} 个过期令牌")

    async def handle_websocket(self, websocket: WebSocketServerProtocol, path: str):
        """处理WebSocket连接"""
        client_id = None

        try:
            # 等待客户端发送初始消息（包含客户端类型）
            initial_message = await websocket.recv()
            data = json.loads(initial_message)

            # 调试：打印收到的消息
            logger.debug(f"收到初始消息: {data}")

            # 兼容两种消息格式
            client_type = data.get('type')

            # 如果是网页客户端发送的 'register'，改为 'web'
            if client_type == 'register' and 'otp' in data:
                client_type = 'web'

            # 检查是否有 client_type 字段（旧版可能没有）
            if not client_type and 'client_type' in data:
                client_type = data.get('client_type')

            client_id = data.get('client_id')
            otp = data.get('otp', '').strip()

            # 如果没有 client_id，生成一个
            if not client_id:
                if client_type == 'web':
                    client_id = 'web-' + str(uuid.uuid4().hex[:8])
                else:
                    client_id = 'python-' + str(uuid.uuid4().hex[:8])

            if not client_type:
                await websocket.close(1008, "无效的客户端信息: 缺少type字段")
                return

            logger.info(f"新连接: {client_type} 客户端, ID: {client_id}")

            # Python 客户端注册
            if client_type == 'python':
                # 生成OTP并发送给客户端
                otp = self.generate_otp(client_id)

                # 创建客户端记录
                client = ChatClient(
                    websocket=websocket,
                    client_id=client_id,
                    client_type=client_type,
                    connected_at=datetime.now(),
                    otp_token=otp
                )

                self.clients[client_id] = client

                # 发送OTP给Python客户端
                await websocket.send(json.dumps({
                    'type': 'otp_generated',
                    'otp': otp,
                    'expires_in': 6000  # 100分钟
                }))

                logger.info(f"Python客户端 {client_id} 已注册，OTP: {otp}")

                # 初始化配对集合
                self.paired_clients[client_id] = set()

                # 等待配对
                await self.handle_python_client(client)

            # Web 客户端连接
            elif client_type == 'web':
                # 验证OTP
                token_info = self.otp_tokens.get(otp)

                if not token_info:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'OTP无效'
                    }))
                    await websocket.close(1008, "OTP无效")
                    return

                # 移除了对 used 状态的检查，允许重复使用
                # if token_info.used:
                #     await websocket.send(json.dumps({
                #         'type': 'error',
                #         'message': 'OTP已被使用'
                #     }))
                #     await websocket.close(1008, "OTP已被使用")
                #     return

                if datetime.now() > token_info.expires_at:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'OTP已过期'
                    }))
                    await websocket.close(1008, "OTP已过期")
                    return

                python_client_id = token_info.client_id
                python_client = self.clients.get(python_client_id)

                if not python_client:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': '对应的Python客户端未连接'
                    }))
                    await websocket.close(1008, "Python客户端未连接")
                    return

                # 创建Web客户端记录
                web_client = ChatClient(
                    websocket=websocket,
                    client_id=client_id,
                    client_type=client_type,
                    connected_at=datetime.now(),
                    otp_token=otp
                )

                self.clients[client_id] = web_client

                # 添加到配对集合中
                if python_client_id not in self.paired_clients:
                    self.paired_clients[python_client_id] = set()
                self.paired_clients[python_client_id].add(client_id)

                # 不再标记OTP为已使用
                # token_info.used = True

                # 通知双方配对成功
                await websocket.send(json.dumps({
                    'type': 'paired',
                    'python_client_id': python_client_id,
                    'message': '已连接到Python客户端'
                }))

                await python_client.websocket.send(json.dumps({
                    'type': 'paired',
                    'web_client_id': client_id,
                    'message': f'新的网页客户端已连接 (总连接数: {len(self.paired_clients[python_client_id])})'
                }))

                logger.info(f"Web客户端 {client_id} 已与Python客户端 {python_client_id} 配对")
                logger.info(
                    f"Python客户端 {python_client_id} 现在有 {len(self.paired_clients[python_client_id])} 个网页客户端连接")

                # 处理Web客户端消息
                await self.handle_web_client(web_client, python_client)

        except json.JSONDecodeError:
            logger.error("收到无效的JSON消息")
            await websocket.close(1007, "无效的消息格式")
        except Exception as e:
            logger.error(f"处理连接时出错: {e}")
            if client_id and client_id in self.clients:
                del self.clients[client_id]
            if websocket.open:
                await websocket.close(1011, "服务器内部错误")

    async def handle_python_client(self, client: ChatClient):
        """处理Python客户端连接"""
        try:
            async for message in client.websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get('type')

                    if message_type == 'message':
                        # 转发消息给所有配对的Web客户端
                        web_client_ids = self.paired_clients.get(client.client_id, set())
                        text = data.get('text', '')
                        timestamp = datetime.now().isoformat()

                        for web_client_id in web_client_ids:
                            web_client = self.clients.get(web_client_id)
                            if web_client and web_client.websocket.open:
                                await web_client.websocket.send(json.dumps({
                                    'type': 'message',
                                    'from': 'python',
                                    'text': text,
                                    'timestamp': timestamp
                                }))

                        logger.info(f"转发消息从Python到 {len(web_client_ids)} 个网页客户端: {text}")

                    elif message_type == 'status':
                        # 心跳或状态更新
                        await client.websocket.send(json.dumps({
                            'type': 'status_ack',
                            'timestamp': datetime.now().isoformat()
                        }))

                except json.JSONDecodeError:
                    logger.warning(f"从Python客户端收到无效JSON: {message}")

        except Exception as e:
            logger.error(f"处理Python客户端 {client.client_id} 时出错: {e}")

        finally:
            # 清理连接
            await self.cleanup_client(client.client_id)

    async def handle_web_client(self, web_client: ChatClient, python_client: ChatClient):
        """处理Web客户端连接"""
        try:
            async for message in web_client.websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get('type')

                    if message_type == 'message':
                        # 转发消息给Python客户端
                        await python_client.websocket.send(json.dumps({
                            'type': 'message',
                            'from': 'web',
                            'web_client_id': web_client.client_id,
                            'text': data.get('text', ''),
                            'timestamp': datetime.now().isoformat()
                        }))
                        logger.info(f"转发消息从Web客户端 {web_client.client_id} 到Python: {data.get('text')}")

                    elif message_type == 'typing':
                        # 转发输入状态给Python客户端
                        await python_client.websocket.send(json.dumps({
                            'type': 'typing',
                            'web_client_id': web_client.client_id,
                            'is_typing': data.get('is_typing', False)
                        }))

                except json.JSONDecodeError:
                    logger.warning(f"从Web客户端收到无效JSON: {message}")

        except Exception as e:
            logger.error(f"处理Web客户端 {web_client.client_id} 时出错: {e}")

        finally:
            # 清理连接
            await self.cleanup_client(web_client.client_id)

    async def cleanup_client(self, client_id: str):
        """清理客户端连接"""
        client = self.clients.get(client_id)
        if client:
            # 如果是Python客户端，断开所有配对的Web客户端
            if client.client_type == 'python':
                web_client_ids = self.paired_clients.get(client_id, set()).copy()
                for web_client_id in web_client_ids:
                    web_client = self.clients.get(web_client_id)
                    if web_client and web_client.websocket.open:
                        await web_client.websocket.send(json.dumps({
                            'type': 'disconnected',
                            'message': 'Python客户端已断开连接'
                        }))
                        await web_client.websocket.close(1000, "Python客户端断开")
                # 清空配对集合
                if client_id in self.paired_clients:
                    del self.paired_clients[client_id]

            # 如果是Web客户端，从配对集合中移除
            elif client.client_type == 'web':
                for py_id, web_client_ids in list(self.paired_clients.items()):
                    if client_id in web_client_ids:
                        web_client_ids.remove(client_id)
                        # 通知Python客户端有网页客户端断开
                        py_client = self.clients.get(py_id)
                        if py_client and py_client.websocket.open:
                            await py_client.websocket.send(json.dumps({
                                'type': 'disconnected',
                                'web_client_id': client_id,
                                'message': '一个网页客户端已断开连接',
                                'remaining_connections': len(web_client_ids)
                            }))
                        # 如果集合为空，可以删除该键（可选）
                        if not web_client_ids:
                            del self.paired_clients[py_id]
                        break

            # 从客户端列表中移除
            del self.clients[client_id]
            logger.info(f"客户端 {client_id} 已断开连接")

    async def start_http_server(self):
        """启动HTTP服务器"""
        runner = web.AppRunner(self.http_app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.http_port)
        await site.start()
        logger.info(f"HTTP服务器启动在 http://{self.host}:{self.http_port}")

    async def start_websocket_server(self):
        """启动WebSocket服务器"""
        async with serve(self.handle_websocket, self.host, self.ws_port):
            logger.info(f"WebSocket服务器启动在 ws://{self.host}:{self.ws_port}")
            await asyncio.Future()  # 永久运行

    async def start(self):
        """启动服务器"""
        # 启动HTTP服务器
        http_task = asyncio.create_task(self.start_http_server())

        # 启动WebSocket服务器
        ws_task = asyncio.create_task(self.start_websocket_server())

        # 等待所有任务
        await asyncio.gather(http_task, ws_task)


if __name__ == "__main__":
    # 从环境变量或命令行参数获取配置
    import os

    host = os.getenv('CHAT_HOST', '0.0.0.0')
    ws_port = int(os.getenv('CHAT_WS_PORT', 8765))
    http_port = int(os.getenv('CHAT_HTTP_PORT', 8080))

    server = ChatServer(host, ws_port, http_port)

    print(f"""
    === 聊天服务器启动 ===
    HTTP 服务器: http://{host}:{http_port}
    WebSocket 服务器: ws://{host}:{ws_port}

    访问 http://{host}:{http_port} 使用网页客户端
    运行 python_client.py 启动Python客户端

    注意：现在一个OTP可以被多个网页客户端使用
    每个Python客户端可以同时与多个网页客户端聊天
    """)

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("服务器关闭")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")