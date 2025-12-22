import asyncio
import threading

import websockets

from core.assistant import EducoderAssistant


class ServerManager:
    def __init__(self, gui, model_info=None):
        """
        初始化服务器管理器
        :param gui: GUI对象
        :param model_info: 模型信息字典，包含model、base_url、api_key
        """
        self.gui = gui
        self.model_info = model_info  # 保存模型信息
        self.server_running = False
        self.server_thread = None
        self.assistant = None

    def start(self):
        """启动服务器"""
        try:
            # 检查模型信息是否有效
            if not self.model_info or not self.model_info.get('api_key'):
                self.gui.log("启动服务器失败：模型信息不完整")
                self.gui.root.after(0, lambda: self.gui.update_status("启动失败：模型信息不完整"))
                return False

            self.server_running = True
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()

            # 记录使用的模型信息
            model_name = self.model_info.get('model', '未知模型')
            self.gui.log(f"正在使用模型: {model_name}")

            return True
        except Exception as e:
            self.gui.log(f"启动服务器时发生错误: {e}")
            self.gui.root.after(0, lambda: self.gui.update_status(f"启动失败: {e}"))
            return False

    def stop(self):
        """停止服务器"""
        self.server_running = False
        if self.assistant:
            # 重置assistant的一些状态
            self.assistant.is_input_in_progress = False
            self.assistant.input_simulator.reset()

    def _run_server(self):
        """运行服务器的主循环"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._server_main())
        except Exception as e:
            self.gui.log(f"服务器运行错误: {str(e)}")

    async def _server_main(self):
        """服务器主函数"""
        try:
            # 创建assistant时传入模型信息
            self.assistant = EducoderAssistant(self.gui, self.model_info)

            # 记录模型信息
            model_name = self.model_info.get('model', '未知模型')
            self.gui.log(f"初始化AI助手，使用模型: {model_name}")

            server = await websockets.serve(
                self.assistant.server,
                "localhost",
                8000,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )

            self.gui.root.after(0, lambda: self.gui.update_server_status("服务器状态: 运行中 (localhost:8000)"))
            self.gui.root.after(0, lambda: self.gui.update_status(f"服务器运行中，使用模型: {model_name}"))
            self.gui.log("WebSocket服务器已启动，监听 localhost:8000")

            # 保持服务器运行
            while self.server_running:
                await asyncio.sleep(1)

            server.close()
            await server.wait_closed()

            self.gui.root.after(0, lambda: self.gui.update_server_status("服务器状态: 已停止"))
            self.gui.root.after(0, lambda: self.gui.update_status("服务器已停止"))
            self.gui.log("服务器已停止")

        except Exception as e:
            self.gui.root.after(0, lambda: self.gui.log(f"服务器启动失败: {str(e)}，请检查是否已有Educoder助手正在运行"))
            self.gui.root.after(0, lambda: self.gui.update_server_status(
                "服务器状态: 启动失败，请检查是否已有Educoder助手正在运行"))
            self.gui.root.after(0, lambda: self.gui.update_status("服务器启动失败，请检查是否已有Educoder助手正在运行"))
            self.gui.root.after(0, lambda: self.gui.start_button.config(state="normal"))
            self.gui.root.after(0, lambda: self.gui.stop_button.config(state="disabled"))