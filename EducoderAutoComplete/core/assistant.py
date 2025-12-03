import asyncio
import websockets
import json
from openai import AsyncOpenAI

from utils.input_simulator import InputSimulator


class EducoderAssistant:
    def __init__(self, gui):
        self.gui = gui
        self.client = AsyncOpenAI(
            api_key=gui.api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.last_question = None
        self.is_first_chunk = True
        self.typing_active = True
        self.input_simulator = InputSimulator(gui)

    async def server(self, websocket):
        """WebSocket服务器处理函数"""
        self.gui.log(f"客户端连接: {websocket.remote_address}")

        try:
            await websocket.send("欢迎使用Educoder助手")

            async for message in websocket:
                try:
                    if isinstance(message, str):
                        try:
                            data = json.loads(message)

                            if data.get('type') == 'educoder_content':
                                await self.handle_educoder_content(websocket, data)
                            else:
                                self.gui.log(f"收到消息: {message}")
                                await websocket.send(f"服务器回复: {message}")

                        except json.JSONDecodeError:
                            self.gui.log(f"收到文本: {message}")
                            await websocket.send(f"服务器回复: {message}")

                    elif isinstance(message, bytes):
                        self.gui.log(f"收到二进制数据: {len(message)} 字节")
                        await websocket.send(message[::-1])

                except Exception as e:
                    self.gui.log(f"处理消息时出错: {e}")
                    await websocket.send(f"错误: {str(e)}")

        except websockets.ConnectionClosed:
            self.gui.log("客户端断开连接")
        except Exception as e:
            self.gui.log(f"服务器错误: {e}")
        finally:
            self.gui.log("连接关闭")

    async def handle_educoder_content(self, websocket, data):
        """处理题目内容"""
        self.gui.log("收到题目内容")

        question_text = data.get('content', {}).get('text', '')
        if question_text:
            # 重置状态
            self.is_first_chunk = True
            self.typing_active = True
            self.input_simulator.reset()

            self.gui.log(f"题目内容长度: {len(question_text)} 字符")
            self.gui.root.after(0, lambda: self.gui.update_status("正在生成代码..."))

            await websocket.send("已收到题目内容，正在向DeepSeek请求代码解决方案...")

            # 根据用户选择使用不同的输入方式
            if self.gui.use_copy_paste.get():
                await websocket.send("使用复制粘贴模式...")
                await self.handle_copy_paste_mode(websocket, question_text)
            else:
                await websocket.send("使用流式输入模式...")
                await self.handle_stream_mode(websocket, question_text)

            self.gui.log("代码生成和输入流程完成")
        else:
            await websocket.send("未找到有效的题目内容")

    async def handle_copy_paste_mode(self, websocket, question_text):
        """处理复制粘贴模式"""
        try:
            # 获取完整代码
            full_code = await self.get_complete_code_solution(question_text)

            if full_code:
                await websocket.send("代码生成完成，准备粘贴到编辑器...")

                success = self.input_simulator.paste_code(full_code)
                if success:
                    await websocket.send("✅ 代码已通过复制粘贴完成输入")
                    self.gui.root.after(0, lambda: self.gui.update_status("代码生成完成"))
                else:
                    if self.input_simulator.esc_pressed:
                        await websocket.send("❌ 用户按ESC键终止了代码输入")
                    else:
                        await websocket.send("❌ 代码粘贴失败")
            else:
                await websocket.send("❌ 代码生成失败")

        except Exception as e:
            self.gui.log(f"复制粘贴模式失败: {e}")
            await websocket.send(f"复制粘贴模式失败: {str(e)}")

    async def handle_stream_mode(self, websocket, question_text):
        """处理流式输入模式"""
        await websocket.send("开始实时输入代码到编辑器...")

        # 获取代码解决方案并实时输入
        full_code = ""
        async for code_response in self.get_code_solution(question_text):
            # 检查ESC键是否被按下
            if self.input_simulator.esc_pressed:
                await websocket.send("❌ 用户按ESC键终止了代码输入")
                break

            await websocket.send(json.dumps(code_response, ensure_ascii=False))

            if code_response.get("type") == "code_chunk":
                chunk = code_response.get("chunk", "")
                full_code += chunk

                input_success = self.input_simulator.simulate_typing(
                    chunk,
                    is_first_chunk=self.is_first_chunk
                )
                self.is_first_chunk = False

                # 如果输入失败，检查是否是ESC键导致的
                if not input_success:
                    if self.input_simulator.esc_pressed:
                        await websocket.send("❌ 用户按ESC键终止了代码输入")
                    else:
                        await websocket.send("❌ 代码输入出现错误")
                    break

            elif code_response.get("type") == "code_complete":
                full_code = code_response.get("full_code", full_code)

                # 只有在未按下ESC键的情况下才显示完成消息
                if not self.input_simulator.esc_pressed:
                    await websocket.send("✅ 代码输入完成")
                    self.gui.root.after(0, lambda: self.gui.update_status("代码生成完成"))
                    # 显示完成提示
                    self.gui.root.after(0, lambda: self.input_simulator._show_completion_message())

        # 如果ESC键被按下，确保显示终止消息
        if self.input_simulator.esc_pressed:
            # 确保移除ESC键监听
            import keyboard
            keyboard.unhook_all()

    async def get_complete_code_solution(self, question_text):
        """获取完整代码解决方案（非流式）"""
        try:
            self.gui.log("获取完整代码解决方案...")

            prompt = self._build_prompt(question_text)

            response = await self.client.chat.completions.create(
                model="qwen3-coder-plus",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的编程助手，只返回代码，不包含任何解释或注释。尤其注意代码前一定不要有```c的标记，代码最后也不要有```的标记。一定不要return 0这一行。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=8192,
                temperature=0,
                stream=False  # 非流式输出
            )

            if response.choices and response.choices[0].message.content:
                full_code = response.choices[0].message.content
                cleaned_code = self.clean_code_response(full_code)
                self.gui.log(f"完整代码解决方案获取成功，长度: {len(cleaned_code)} 字符")
                return cleaned_code
            else:
                self.gui.log("获取完整代码解决方案失败")
                return None

        except Exception as e:
            self.gui.log(f"获取完整代码解决方案失败: {e}")
            return None

    async def get_code_solution(self, question_text):
        """使用DeepSeek API获取代码解决方案（流式输出）"""
        try:
            self.gui.log("向DeepSeek发送请求获取代码解决方案...")

            prompt = self._build_prompt(question_text)

            response = await self.client.chat.completions.create(
                model="qwen3-coder-plus",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的编程助手，只返回代码，不包含任何解释或注释。尤其注意代码前一定不要有```c的标记，代码最后也不要有```的标记。一定不要return 0这一行。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=8192,
                temperature=0,
                stream=True
            )

            full_code = ""
            self.is_first_chunk = True

            async for chunk in response:
                # 检查ESC键是否被按下
                if self.input_simulator.esc_pressed:
                    break

                if chunk.choices and chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_code += content

                    yield {
                        "type": "code_chunk",
                        "chunk": content,
                        "is_complete": False
                    }

            # 只有在未按下ESC键的情况下才返回完整代码
            if not self.input_simulator.esc_pressed:
                self.gui.log(f"代码解决方案流式传输完成，总长度: {len(full_code)} 字符")

                cleaned_code = self.clean_code_response(full_code)

                yield {
                    "type": "code_complete",
                    "full_code": cleaned_code,
                    "is_complete": True
                }

        except Exception as e:
            self.gui.log(f"获取DeepSeek响应失败: {e}")
            yield {
                "type": "error",
                "message": f"获取代码解决方案失败: {str(e)}",
                "is_complete": True
            }

    def _build_prompt(self, question_text):
        """构建提示词"""
        return f"""
请根据以下编程题目要求，只提供完整的代码解决方案，不要包含任何解释、注释或其他文本。
题目内容：
{question_text}

要求：
1. 代码应完整且可运行,必须包含头文件,主函数必须int main()形式
2. 只返回代码，不要有任何额外的文字说明
3. 使用标准库和常见的编程实践
4. 所有的代码都是C语言

请直接返回代码：
"""

    def clean_code_response(self, response):
        """清理API响应，确保只包含代码"""
        lines = response.split('\n')
        cleaned_lines = []

        in_code_block = False
        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue

            if in_code_block or (
                    line.strip() and not line.strip().startswith('//') and not line.strip().startswith('#')):
                cleaned_lines.append(line)

        cleaned_response = '\n'.join(cleaned_lines).strip()
        return cleaned_response if cleaned_response else response