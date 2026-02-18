"""
远程协助服务器
处理一次性密码生成、验证和WebSocket连接
"""
import asyncio
import hashlib
import json
import os
import secrets
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

import aiohttp
from aiohttp import web
import websockets
from websockets.server import WebSocketServerProtocol


class RemoteAssistServer:
    def __init__(self, gui, input_simulator, port=8001):
        """
        初始化远程协助服务器
        :param gui: GUI对象
        :param input_simulator: 输入模拟器对象
        :param port: 服务器端口，默认8001
        """
        self.gui = gui
        self.input_simulator = input_simulator
        self.port = port
        self.server_running = False
        self.server_thread = None
        
        # 存储一次性密码和设备信息
        # 格式: {device_id: {password: str, expires_at: float, websocket: WebSocket}}
        self.device_sessions: Dict[str, Dict] = {}
        
        # 存储已登录的WebSocket连接
        # 格式: {device_id: WebSocket}
        self.active_connections: Dict[str, WebSocketServerProtocol] = {}
        
        # 密码永不过期（设置为None表示永不过期）
        self.password_expiry = None
        
        # HTTP服务器相关
        self.http_runner = None

    def start(self):
        """启动服务器"""
        try:
            self.server_running = True
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            self.gui.log(f"远程协助服务器已启动，监听端口 {self.port}")
            return True
        except Exception as e:
            self.gui.log(f"启动远程协助服务器失败: {e}")
            return False

    def stop(self):
        """停止服务器"""
        self.server_running = False
        # 关闭所有连接
        for device_id, ws in list(self.active_connections.items()):
            try:
                asyncio.run_coroutine_threadsafe(ws.close(), self.loop)
            except:
                pass
        self.active_connections.clear()
        self.device_sessions.clear()

    def _run_server(self):
        """运行服务器的主循环"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.loop = loop
            loop.run_until_complete(self._server_main())
        except Exception as e:
            self.gui.log(f"远程协助服务器运行错误: {str(e)}")

    async def handle_http_request(self, request):
        """
        处理HTTP请求，提供静态文件服务
        """
        try:
            # 获取web目录的绝对路径
            web_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'web'
            )
            
            # 获取请求路径
            path = request.path
            if path == '/':
                # 根路径映射到remote_assist.html
                file_path = os.path.join(web_dir, 'remote_assist.html')
            else:
                # 其他路径直接映射到文件
                file_path = os.path.join(web_dir, path.lstrip('/'))
            
            # 检查文件是否存在
            if os.path.exists(file_path) and os.path.isfile(file_path):
                # 获取文件扩展名以设置正确的Content-Type
                ext = os.path.splitext(file_path)[1].lower()
                content_type = {
                    '.html': 'text/html',
                    '.js': 'text/javascript',
                    '.css': 'text/css',
                    '.json': 'application/json',
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.svg': 'image/svg+xml'
                }.get(ext, 'application/octet-stream')
                
                # 读取并返回文件内容
                with open(file_path, 'rb') as f:
                    content = f.read()
                return web.Response(body=content, content_type=content_type)
            else:
                # 文件不存在，返回404
                return web.Response(text="File not found", status=404)
        except Exception as e:
            self.gui.log(f"HTTP请求处理错误: {e}")
            return web.Response(text="Internal server error", status=500)

    async def _server_main(self):
        """
        服务器主函数 - 同时启动WebSocket和HTTP服务器
        """
        try:
            # 创建事件循环
            loop = asyncio.get_event_loop()
            
            # 1. 启动WebSocket服务器
            ws_server = await websockets.serve(
                self.handle_client,
                "0.0.0.0",  # 监听所有接口
                self.port,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )

            # 2. 创建并配置HTTP服务器
            app = web.Application()
            app.router.add_get('/', self.handle_http_request)
            app.router.add_get('/{tail:.*}', self.handle_http_request)  # 处理所有其他路径
            
            # 启动HTTP服务器
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", self.port)
            await site.start()
            
            # 保存runner以便后续关闭
            self.http_runner = runner

            self.gui.root.after(0, lambda: self.gui.log(f"远程协助服务器运行中 (0.0.0.0:{self.port})"))
            self.gui.root.after(0, lambda: self.gui.log(f"静态文件服务已启动，可通过 http://0.0.0.0:{self.port}/ 访问"))

            # 保持服务器运行
            while self.server_running:
                await asyncio.sleep(1)

            # 关闭服务器
            ws_server.close()
            await ws_server.wait_closed()
            
            if self.http_runner:
                await self.http_runner.cleanup()

            self.gui.root.after(0, lambda: self.gui.log("远程协助服务器已停止"))

        except Exception as e:
            self.gui.root.after(0, lambda: self.gui.log(f"远程协助服务器启动失败: {str(e)}"))

    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """处理客户端连接"""
        device_id = None
        try:
            async for message in websocket:
                try:
                    if isinstance(message, str):
                        data = json.loads(message)
                        msg_type = data.get('type')

                        if msg_type == 'generate_password':
                            # 生成一次性密码
                            device_id = data.get('device_id')
                            if not device_id:
                                await websocket.send(json.dumps({
                                    'type': 'error',
                                    'message': '缺少设备ID'
                                }, ensure_ascii=False))
                                continue

                            password = self.generate_one_time_password(device_id)
                            await websocket.send(json.dumps({
                                'type': 'password_generated',
                                'password': password,
                                'expires_in': self.password_expiry
                            }, ensure_ascii=False))

                            self.gui.log(f"为设备 {device_id[:8]}... 生成一次性密码: {password}")

                        elif msg_type == 'login':
                            # 登录验证
                            password = data.get('password')
                            device_id = data.get('device_id')

                            if self.verify_password(device_id, password):
                                # 登录成功
                                self.active_connections[device_id] = websocket
                                
                                # 删除密码（一次性使用）
                                if device_id in self.device_sessions:
                                    del self.device_sessions[device_id]

                                await websocket.send(json.dumps({
                                    'type': 'login_success',
                                    'message': '登录成功'
                                }, ensure_ascii=False))

                                self.gui.log(f"设备 {device_id[:8]}... 登录成功")
                            else:
                                await websocket.send(json.dumps({
                                    'type': 'login_failed',
                                    'message': '密码错误或已过期'
                                }, ensure_ascii=False))

                        elif msg_type == 'send_text':
                            # 接收来自H5页面的文本输入
                            device_id = data.get('device_id')
                            text = data.get('text', '')

                            if device_id in self.active_connections:
                                # 模拟键盘输入
                                self.gui.root.after(0, lambda t=text: self._simulate_input(t))
                                
                                await websocket.send(json.dumps({
                                    'type': 'text_sent',
                                    'message': '文本已发送'
                                }, ensure_ascii=False))

                                self.gui.log(f"收到来自设备 {device_id[:8]}... 的文本输入: {len(text)} 字符")
                            else:
                                await websocket.send(json.dumps({
                                    'type': 'error',
                                    'message': '未登录或连接已断开'
                                }, ensure_ascii=False))

                        elif msg_type == 'ping':
                            # 心跳检测
                            await websocket.send(json.dumps({
                                'type': 'pong'
                            }, ensure_ascii=False))

                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': '无效的JSON格式'
                    }, ensure_ascii=False))
                except Exception as e:
                    self.gui.log(f"处理消息时出错: {e}")
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': str(e)
                    }, ensure_ascii=False))

        except websockets.ConnectionClosed:
            if device_id:
                self.gui.log(f"设备 {device_id[:8]}... 断开连接")
                if device_id in self.active_connections:
                    del self.active_connections[device_id]
        except Exception as e:
            self.gui.log(f"客户端连接错误: {e}")
            if device_id and device_id in self.active_connections:
                del self.active_connections[device_id]

    def generate_one_time_password(self, device_id: str) -> str:
        """
        为指定设备生成一次性密码
        :param device_id: 设备ID
        :return: 6位数字密码
        """
        # 生成6位随机数字密码
        password = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        
        # 存储密码（永不过期）
        self.device_sessions[device_id] = {
            'password': password,
            'created_at': time.time()
        }
        
        return password

    def verify_password(self, device_id: str, password: str) -> bool:
        """
        验证一次性密码（永不过期）
        :param device_id: 设备ID
        :param password: 密码
        :return: 验证是否成功
        """
        if device_id not in self.device_sessions:
            return False
        
        session = self.device_sessions[device_id]
        
        # 验证密码（永不过期，不需要检查过期时间）
        if session.get('password') == password:
            return True
        
        return False

    def send_question_to_device(self, device_id: str, question_content: dict):
        """
        向指定设备发送题目内容
        :param device_id: 设备ID
        :param question_content: 题目内容字典
        """
        if device_id in self.active_connections:
            websocket = self.active_connections[device_id]
            try:
                message = json.dumps({
                    'type': 'question_content',
                    'content': question_content,
                    'timestamp': datetime.now().isoformat()
                }, ensure_ascii=False)
                
                asyncio.run_coroutine_threadsafe(
                    websocket.send(message),
                    self.loop
                )
                
                self.gui.log(f"已向设备 {device_id[:8]}... 发送题目内容")
            except Exception as e:
                self.gui.log(f"发送题目内容失败: {e}")
        else:
            self.gui.log(f"设备 {device_id[:8]}... 未连接")

    def _simulate_input(self, text: str):
        """模拟键盘输入文本"""
        try:
            if self.input_simulator:
                # 使用输入模拟器输入文本
                # 将文本分成小块输入
                chunk_size = 50
                chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
                for i, chunk in enumerate(chunks):
                    self.input_simulator.simulate_typing(chunk, is_first_chunk=(i == 0))
        except Exception as e:
            self.gui.log(f"模拟输入失败: {e}")

    def get_device_password(self, device_id: str) -> Optional[str]:
        """
        获取设备的一次性密码（用于显示在GUI中）
        :param device_id: 设备ID
        :return: 密码字符串，如果不存在则返回None
        """
        if device_id in self.device_sessions:
            session = self.device_sessions[device_id]
            return session.get('password')
        return None

    def is_device_connected(self, device_id: str) -> bool:
        """
        检查设备是否已连接
        :param device_id: 设备ID
        :return: 是否已连接
        """
        return device_id in self.active_connections

