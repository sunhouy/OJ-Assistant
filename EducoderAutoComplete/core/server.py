import asyncio
import threading
import websockets

from core.assistant import EducoderAssistant


class ServerManager:
    def __init__(self, gui):
        self.gui = gui
        self.server_running = False
        self.server_thread = None
        self.assistant = None

    def start(self):
        """启动服务器"""
        self.server_running = True
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        return True
        
    def stop(self):
        """停止服务器"""
        self.server_running = False
        
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
            self.assistant = EducoderAssistant(self.gui)
            
            server = await websockets.serve(
                self.assistant.server,
                "localhost",
                8000,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.gui.root.after(0, lambda: self.gui.update_server_status("服务器状态: 运行中 (localhost:8000)"))
            self.gui.root.after(0, lambda: self.gui.update_status("服务器运行中，等待连接..."))
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
            self.gui.root.after(0, lambda: self.gui.log(f"服务器启动失败: {str(e)}"))
            self.gui.root.after(0, lambda: self.gui.update_server_status("服务器状态: 启动失败"))
            self.gui.root.after(0, lambda: self.gui.update_status("服务器启动失败"))
            self.gui.root.after(0, lambda: self.gui.start_button.config(state="normal"))
            self.gui.root.after(0, lambda: self.gui.stop_button.config(state="disabled"))