import asyncio
import tkinter as tk
from tkinter import ttk, messagebox
import websockets
import json
from openai import AsyncOpenAI
import re
from datetime import datetime

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
        self.current_language = gui.selected_language.get().lower()

        # 新增：保存测试失败信息和状态
        self.test_failures = []
        self.retry_count = 0
        self.max_retries = 3
        self.is_input_in_progress = False
        self.current_code = None
        self.current_progress = 0  # 当前进度

        self.gui.log(f"Assistant初始化，当前语言: {self.current_language.upper()}")

    def update_language(self, new_language):
        """更新当前语言设置"""
        self.current_language = new_language.lower()
        self.gui.log(f"Assistant语言已更新为: {self.current_language.upper()}")

    async def server(self, websocket):
        """WebSocket服务器处理函数"""
        self.gui.log(f"客户端连接: {websocket.remote_address}")
        self.gui.log(f"服务器当前语言: {self.current_language.upper()}")

        try:
            await websocket.send("欢迎使用Educoder助手，现在支持自动纠错功能")

            async for message in websocket:
                try:
                    if isinstance(message, str):
                        try:
                            data = json.loads(message)

                            if data.get('type') == 'educoder_content_auto_input':
                                await self.handle_educoder_content_auto_input(websocket, data)
                            elif data.get('type') == 'test_results':
                                await self.handle_test_results(websocket, data)
                            elif data.get('type') == 'ready_for_input':
                                await self.handle_ready_for_input(websocket, data)
                            elif data.get('type') == 'progress_request':
                                # 处理前端进度请求
                                await self.send_progress_update(websocket)
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
            # 重置输入状态
            self.is_input_in_progress = False
        except Exception as e:
            self.gui.log(f"服务器错误: {e}")
        finally:
            self.gui.log("连接关闭")

    async def send_progress_update(self, websocket):
        """发送当前进度到前端"""
        try:
            await websocket.send(json.dumps({
                "type": "progress_update",
                "progress": self.current_progress,
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False))
        except Exception as e:
            self.gui.log(f"发送进度更新失败: {e}")

    def update_progress(self, progress):
        """更新进度"""
        self.current_progress = max(0, min(100, progress))
        self.gui.log(f"进度更新: {self.current_progress}%")

        # 更新GUI状态
        self.gui.root.after(0, lambda: self.gui.update_status(f"进度: {self.current_progress}%"))

    async def handle_educoder_content_auto_input(self, websocket, data):
        """处理题目内容并自动输入"""
        try:
            self.gui.log("收到题目内容并开始自动输入")
            self.gui.log(f"当前使用语言: {self.current_language.upper()}")

            question_content = data.get('content', {})
            question_text = question_content.get('text', '')

            if question_text:
                # 保存题目内容供后续使用
                self.last_question = question_text
                # 重置状态
                self.retry_count = 0
                self.test_failures = []
                self.is_first_chunk = True
                self.typing_active = True
                self.input_simulator.reset()
                self.is_input_in_progress = True
                self.current_progress = 0  # 重置进度

                self.gui.log(f"题目内容长度: {len(question_text)} 字符")
                self.gui.root.after(0,
                                    lambda: self.gui.update_status(f"正在生成{self.current_language.upper()}代码..."))

                # 发送初始进度
                self.update_progress(5)
                await self.send_progress_update(websocket)

                await websocket.send(f"已收到题目内容，正在向DeepSeek请求{self.current_language.upper()}代码解决方案...")
                await websocket.send(f"当前编程语言: {self.current_language.upper()}")

                # 生成代码
                full_code = await self.get_complete_code_solution(question_text)

                if full_code:
                    self.current_code = full_code
                    self.update_progress(10)  # 代码生成完成
                    await self.send_progress_update(websocket)

                    await websocket.send("✅ 代码生成完成，准备开始自动输入...")

                    # 通知前端开始输入
                    await websocket.send(json.dumps({
                        "type": "code_solution",
                        "code": full_code,
                        "timestamp": datetime.now().isoformat()
                    }, ensure_ascii=False))

                    # 等待前端响应
                    self.gui.log("等待前端准备输入...")
                else:
                    await websocket.send("❌ 代码生成失败")
                    self.is_input_in_progress = False

            else:
                await websocket.send("未找到有效的题目内容")
                self.is_input_in_progress = False

        except Exception as e:
            self.gui.log(f"处理题目内容失败: {e}")
            await websocket.send(f"处理失败: {str(e)}")
            self.is_input_in_progress = False

    async def handle_test_results(self, websocket, data):
        """处理测试结果并智能纠错"""
        try:
            self.gui.log("收到测试结果")

            test_results = data.get('results', {})
            test_text = test_results.get('text', '')
            current_code = data.get('currentCode', '')
            has_error = data.get('has_error', False)  # 获取前端传来的错误标记

            # 直接使用前端传来的错误标记
            should_fix = has_error

            # 保存测试失败信息（直接使用test_results）
            self.test_failures = test_results

            if should_fix:
                self.gui.log(f"检测到测试失败，准备纠错")

                # 检查是否超过最大重试次数
                if self.retry_count >= self.max_retries:
                    await websocket.send(json.dumps({
                        "type": "test_results_response",
                        "success": True,
                        "has_failures": True,
                        "failure_count": 0,
                        "failures": [],
                        "test_results_text": test_text,
                        "message": f"已达到最大重试次数({self.max_retries}次)，请手动检查代码"
                    }, ensure_ascii=False))
                    return

                # 增加重试计数
                self.retry_count += 1

                # 更新进度
                self.update_progress(20 + (self.retry_count * 10))
                await self.send_progress_update(websocket)

                await websocket.send(f"检测到测试失败，开始第 {self.retry_count} 次纠错...")

                # 开始纠错流程
                revised_code = await self._generate_revised_code_with_failures(
                    self.last_question,
                    test_text,  # 直接使用test_text作为错误内容
                    current_code
                )

                if revised_code:
                    self.current_code = revised_code

                    # 更新进度
                    self.update_progress(50)
                    await self.send_progress_update(websocket)

                    # 发送修订代码给前端
                    await websocket.send(json.dumps({
                        "type": "code_revision",
                        "revised_code": revised_code,
                        "retry_count": self.retry_count,
                        "failure_count": 0,
                        "revision_notes": f"第{self.retry_count}次纠错，修正了测试失败",
                        "timestamp": datetime.now().isoformat()
                    }, ensure_ascii=False))

                    self.gui.root.after(0, lambda: self.gui.update_status(f"代码纠错完成 (第{self.retry_count}次)"))

                else:
                    await websocket.send(json.dumps({
                        "type": "test_results_response",
                        "success": False,
                        "message": "代码纠错失败",
                        "test_results_text": test_text
                    }, ensure_ascii=False))

            else:
                # 所有测试通过
                self.gui.log("所有测试通过！")
                self.gui.root.after(0, lambda: self.gui.update_status("代码正确！"))

                # 在Tk界面显示成功消息
                self.gui.root.after(0, lambda: messagebox.showinfo("测试结果", "所有测试通过！代码正确。"))

                await websocket.send(json.dumps({
                    "type": "test_results_response",
                    "success": True,
                    "has_failures": False,
                    "message": "所有测试通过！代码正确。",
                    "test_results_text": test_text
                }, ensure_ascii=False))

        except Exception as e:
            self.gui.log(f"处理测试结果失败: {e}")
            await websocket.send(json.dumps({
                "type": "test_results_response",
                "success": False,
                "message": f"处理测试结果失败: {str(e)}"
            }, ensure_ascii=False))

    async def handle_ready_for_input(self, websocket, data):
        """处理准备输入请求"""
        try:
            self.gui.log("收到准备输入请求")

            code = data.get('code', '')
            is_retry = data.get('is_retry', False)
            retry_count = data.get('retry_count', 0)

            if not code:
                await websocket.send("错误: 没有可输入的代码")
                return

            # 设置输入状态
            self.is_input_in_progress = True
            self.input_simulator.reset()

            # 更新进度
            self.update_progress(40 if is_retry else 50)
            await self.send_progress_update(websocket)

            if is_retry:
                await websocket.send(f"开始第 {retry_count} 次纠错输入...")
                self.gui.root.after(0, lambda: self.gui.update_status(f"正在输入纠错代码 (第{retry_count}次)..."))
            else:
                await websocket.send("开始自动输入代码...")
                self.gui.root.after(0, lambda: self.gui.update_status("正在输入代码..."))

            # 根据用户选择使用不同的输入方式
            if self.gui.use_copy_paste.get():
                await websocket.send("使用复制粘贴模式...")
                success = self.input_simulator.paste_code(code)

                if success:
                    # 更新进度
                    self.update_progress(100)
                    await self.send_progress_update(websocket)

                    await websocket.send("✅ 代码已通过复制粘贴完成输入")
                    self.gui.root.after(0,
                                        lambda: self.gui.update_status(f"{self.current_language.upper()}代码输入完成"))
                else:
                    if self.input_simulator.esc_pressed:
                        await websocket.send("❌ 用户按ESC键终止了代码输入")
                    else:
                        await websocket.send("❌ 代码粘贴失败")
            else:
                await websocket.send("使用流式输入模式...")
                await self._stream_input_code(websocket, code)

            # 输入完成
            self.is_input_in_progress = False

            # 显示完成消息
            if not self.input_simulator.esc_pressed:
                self.gui.root.after(0, lambda: self.input_simulator._show_completion_message())

        except Exception as e:
            self.gui.log(f"处理输入请求失败: {e}")
            await websocket.send(f"输入失败: {str(e)}")
            self.is_input_in_progress = False

    async def _stream_input_code(self, websocket, code):
        """流式输入代码"""
        full_code = ""
        self.is_first_chunk = True

        # 将代码分成小块进行输入
        chunks = self._split_code_into_chunks(code)

        for i, chunk in enumerate(chunks):
            # 检查ESC键是否被按下
            if self.input_simulator.esc_pressed:
                await websocket.send("❌ 用户按ESC键终止了代码输入")
                break

            full_code += chunk

            # 模拟输入
            input_success = self.input_simulator.simulate_typing(
                chunk,
                is_first_chunk=self.is_first_chunk
            )
            self.is_first_chunk = False

            # 计算进度
            progress = 60 + int((i + 1) / len(chunks) * 40)  # 从60%到100%
            self.update_progress(progress)

            # 发送JSON格式的进度消息
            await websocket.send(json.dumps({
                "type": "input_progress",
                "progress": progress,
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False))

            # 同时发送文本进度消息，兼容旧版本
            await websocket.send(f"输入进度: {progress}%")

            if not input_success:
                if self.input_simulator.esc_pressed:
                    await websocket.send("❌ 用户按ESC键终止了代码输入")
                else:
                    await websocket.send("❌ 代码输入出现错误")
                break

        # 只有在未按下ESC键的情况下才显示完成消息
        if not self.input_simulator.esc_pressed:
            # 更新最终进度
            self.update_progress(100)
            await self.send_progress_update(websocket)

            # 发送输入完成消息
            await websocket.send(json.dumps({
                "type": "input_complete",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False))
            await websocket.send("✅ 代码输入完成")

    def _split_code_into_chunks(self, code, max_chunk_size=50):
        """将代码分割成小块"""
        lines = code.split('\n')
        chunks = []
        current_chunk = ""

        for line in lines:
            if len(current_chunk) + len(line) + 1 > max_chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = line + '\n'
            else:
                current_chunk += line + '\n'

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    async def _generate_revised_code_with_failures(self, original_question, test_results_text, previous_code):
        """根据测试失败重新生成代码"""
        try:
            self.gui.log(f"根据测试失败重新生成{self.current_language.upper()}代码，第{self.retry_count}次重试")

            # 构建包含失败信息的提示词
            prompt = self._build_retry_prompt(original_question, test_results_text, previous_code)

            response = await self.client.chat.completions.create(
                model="qwen3-coder-plus",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_retry_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=8192,
                temperature=0.3,  # 稍高的温度以获得更多样化的解决方案
                stream=False
            )

            if response.choices and response.choices[0].message.content:
                full_code = response.choices[0].message.content
                cleaned_code = self.clean_code_response(full_code)
                self.gui.log(f"代码重新生成成功，长度: {len(cleaned_code)} 字符")
                return cleaned_code
            else:
                self.gui.log("代码重新生成失败")
                return None

        except Exception as e:
            self.gui.log(f"代码重新生成失败: {e}")
            return None

    def _build_retry_prompt(self, original_question, test_results_text, previous_code):
        """构建重试提示词"""
        language_mapping = {
            "C": "C语言",
            "C++": "C++",
            "Java": "Java",
            "Python": "Python",
            "Javascript": "JavaScript",
            "C#": "C#"
        }

        lang_name = language_mapping.get(self.current_language, self.current_language.upper())

        # 构建提示词
        prompt = f"""
原始题目要求：
{original_question}

之前的代码（可能有问题）：
{previous_code}

测试失败详情：
{test_results_text}

请根据以上信息，修复代码中的错误，生成新的{lang_name}代码。

特别注意：
1. 仔细分析测试失败的原因
2. 修正之前代码中的错误
3. 确保新代码能够通过所有测试用例
4. 只返回纯代码，不要有任何解释

请生成修复后的{lang_name}代码：
"""
        print(prompt)
        return prompt

    def _get_retry_system_prompt(self):
        """获取重试系统提示词"""
        language_mapping = {
            "C": "C语言",
            "C++": "C++",
            "Java": "Java",
            "Python": "Python",
            "Javascript": "JavaScript",
            "C#": "C#"
        }

        lang_name = language_mapping.get(self.current_language, self.current_language.upper())

        system_prompt = f"""你是一个专业的编程助手，负责根据测试失败信息修正{lang_name}代码。
重要规则：
1. 只返回纯代码，不要有任何解释、注释或额外文字
2. 绝对不要使用任何代码块标记
3. 代码必须完整且可运行
专注于修复已知的错误，确保代码通过所有测试。"""
        return system_prompt

    async def get_complete_code_solution(self, question_text):
        """获取完整代码解决方案（非流式）"""
        try:
            self.gui.log(f"获取完整{self.current_language.upper()}代码解决方案...")

            prompt = self._build_prompt(question_text)

            response = await self.client.chat.completions.create(
                model="qwen3-coder-plus",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=8192,
                temperature=0,
                stream=False
            )

            if response.choices and response.choices[0].message.content:
                full_code = response.choices[0].message.content
                cleaned_code = self.clean_code_response(full_code)
                self.gui.log(f"完整{self.current_language.upper()}代码解决方案获取成功，长度: {len(cleaned_code)} 字符")
                return cleaned_code
            else:
                self.gui.log(f"获取完整{self.current_language.upper()}代码解决方案失败")
                return None

        except Exception as e:
            self.gui.log(f"获取完整{self.current_language.upper()}代码解决方案失败: {e}")
            return None

    def _get_system_prompt(self):
        """根据当前语言获取系统提示词"""
        language_mapping = {
            "C": "C语言",
            "C++": "C++",
            "Java": "Java",
            "Python": "Python",
            "Javascript": "JavaScript",
            "C#": "C#"
        }

        lang_name = language_mapping.get(self.current_language, self.current_language.upper())

        system_prompt = f"""你是一个专业的编程助手，负责生成{lang_name}代码。
重要规则：
1. 只返回纯代码，不要有任何解释、注释或额外文字
2. 绝对不要使用任何代码块标记（如```或```{self.current_language}）
3. 代码必须完整且可运行
你的输出应该只包含代码，没有任何其他内容。"""
        return system_prompt

    def _build_prompt(self, question_text):
        """构建提示词"""
        language_mapping = {
            "C": "C语言",
            "C++": "C++",
            "Java": "Java",
            "Python": "Python",
            "Javascript": "JavaScript",
            "C#": "C#"
        }

        lang_name = language_mapping.get(self.current_language, self.current_language.upper())

        if self.current_language == "C":
            requirements = f"""
要求：
1. 代码应完整且可运行，必须包含头文件，主函数必须int main()形式
2. 只返回代码，不要有任何额外的文字说明
3. 使用标准库和常见的C语言编程实践
4. 不要添加return 0语句
            """
        elif self.current_language == "C++":
            requirements = f"""
要求：
1. 代码应完整且可运行，必须包含必要的头文件，主函数必须int main()形式
2. 只返回代码，不要有任何额外的文字说明
3. 使用C++标准库和现代的C++编程实践
4. 一定不要使用using namespace std。
            """
        elif self.current_language == "Java":
            requirements = f"""
要求：
1. 代码应完整且可运行，必须包含完整的类定义
2. 只返回代码，不要有任何额外的文字说明
3. 使用标准的Java编程规范和命名约定
4. 包含main方法作为程序入口
            """
        elif self.current_language == "Python":
            requirements = f"""
要求：
1. 代码应完整且可运行，使用Python 3语法
2. 只返回代码，不要有任何额外的文字说明
3. 遵循PEP 8编码规范
            """
        elif self.current_language == "Javascript":
            requirements = f"""
要求：
1. 代码应完整且可运行，使用标准的JavaScript语法
2. 只返回代码，不要有任何额外的文字说明
3. 可以在浏览器或Node.js环境中运行
            """
        elif self.current_language == "C#":
            requirements = f"""
要求：
1. 代码应完整且可运行，必须包含完整的命名空间和类定义
2. 只返回代码，不要有任何额外的文字说明
3. 使用标准的C#编程规范和命名约定
4. 包含Main方法作为程序入口
            """
        else:
            requirements = f"""
要求：
1. {lang_name}代码应完整且可运行
2. 只返回代码，不要有任何额外的文字说明
3. 使用标准的编程规范和最佳实践
            """

        return f"""
请根据以下编程题目要求，只提供完整的{lang_name}代码解决方案，不要包含任何解释、注释或其他文本。
{requirements}
题目内容：
{question_text}
"""

    def clean_code_response(self, response):
        """清理API响应，确保只包含代码"""

        lines = response.split('\n')
        cleaned_lines = []

        in_code_block = False
        for line in lines:
            stripped_line = line.strip()
            if stripped_line.startswith('```'):
                in_code_block = not in_code_block
                continue

            if not in_code_block:
                if self.current_language in ["C", "C++", "C#", "Java"]:
                    if stripped_line.startswith('//'):
                        continue
                    if stripped_line.startswith('/*'):
                        continue
                    if stripped_line.endswith('*/'):
                        continue
                elif self.current_language == "Python":
                    if stripped_line.startswith('#'):
                        continue
                elif self.current_language == "Javascript":
                    if stripped_line.startswith('//'):
                        continue
                    if stripped_line.startswith('/*'):
                        continue
                    if stripped_line.endswith('*/'):
                        continue

            cleaned_lines.append(line)

        cleaned_response = '\n'.join(cleaned_lines).strip()
        return cleaned_response if cleaned_response else response