class EducoderFloatingAssistant {
    constructor() {
        this.socket = null;
        this.isVisible = false;
        this.isMinimized = false;
        this.generatedCode = null;
        this.dragging = false;
        this.dragOffset = { x: 0, y: 0 };
        this.autoConnectAttempted = false;
        this.currentQuestionContent = null;
        this.testFailures = [];
        this.retryCount = 0;
        this.isInputInProgress = false;
        this.isSmartFixInProgress = false;
        this.topTipOverlay = null;
        this.progressBar = null;

        // 进度同步相关
        this.virtualProgressInterval = null;
        this.virtualProgress = 0;
        this.progressDuration = 60000; // 60秒完成
        this.lastProgressUpdateTime = 0;
        this.serverProgress = 0; // 服务器端的进度
        this.isServerProgressActive = false; // 是否使用服务器进度
        this.progressUpdateInterval = null; // 进度更新轮询

        this.init();
    }

    async init() {
        this.createTopTipOverlay();
        this.createFloatingWindow();
        this.attachEventListeners();
        await this.loadSettings();
        this.extractPageContent();

        await this.autoConnect();
    }

    createTopTipOverlay() {
        // 创建顶部提示条
        this.topTipOverlay = document.createElement('div');
        this.topTipOverlay.id = 'ea-top-tip-overlay';
        this.topTipOverlay.className = 'ea-top-tip-overlay';
        this.topTipOverlay.style.display = 'none';

        this.topTipOverlay.innerHTML = `
            <div class="ea-top-tip-content">
                <div class="ea-top-tip-left">
                    <span class="ea-top-tip-icon">⌨️</span>
                    <div class="ea-top-tip-text">
                        <div class="ea-top-tip-title">代码正在输入中...</div>
                        <div class="ea-top-tip-subtitle">请保持页面焦点，请勿触碰鼠标和键盘</div>
                    </div>
                </div>
                <div class="ea-top-tip-right">
                    <div class="ea-top-progress-container">
                        <div class="ea-top-progress-bar" id="eaTopProgressBar"></div>
                        <div class="ea-top-progress-text" id="eaTopProgressText">0%</div>
                    </div>
                    <div class="ea-top-tip-actions">
                        <span class="ea-top-tip-hint">按ESC可随时终止</span>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(this.topTipOverlay);

        this.progressBar = document.getElementById('eaTopProgressBar');
        this.progressText = document.getElementById('eaTopProgressText');
    }

    // 显示顶部提示条
    showTopTipOverlay(initialProgress = 0, title = '代码正在输入中...') {
        if (this.topTipOverlay) {
            // 更新标题
            const titleElement = this.topTipOverlay.querySelector('.ea-top-tip-title');
            if (titleElement) {
                titleElement.textContent = title;
            }

            this.topTipOverlay.style.display = 'block';
            this.topTipOverlay.style.zIndex = '99999';

            // 重置进度状态
            this.virtualProgress = initialProgress;
            this.serverProgress = initialProgress;
            this.isServerProgressActive = false;
            this.updateTopTipProgress(initialProgress);
            this.lastProgressUpdateTime = Date.now();

            // 开始虚拟进度更新（作为后备）
            this.startVirtualProgress();

            // 开始轮询服务器进度
            this.startProgressPolling();
        }
    }

    // 开始轮询服务器进度
    startProgressPolling() {
        // 清除之前的轮询
        if (this.progressUpdateInterval) {
            clearInterval(this.progressUpdateInterval);
            this.progressUpdateInterval = null;
        }

        // 每500毫秒请求一次服务器进度
        this.progressUpdateInterval = setInterval(() => {
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                this.requestServerProgress();
            }
        }, 500);
    }

    // 请求服务器进度
    requestServerProgress() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'progress_request',
                timestamp: new Date().toISOString()
            }));
        }
    }

    // 停止进度轮询
    stopProgressPolling() {
        if (this.progressUpdateInterval) {
            clearInterval(this.progressUpdateInterval);
            this.progressUpdateInterval = null;
        }
    }

    // 虚拟进度作为后备
    startVirtualProgress() {
        // 清除之前的定时器
        if (this.virtualProgressInterval) {
            clearInterval(this.virtualProgressInterval);
            this.virtualProgressInterval = null;
        }

        // 如果服务器进度不活跃，使用虚拟进度
        if (!this.isServerProgressActive) {
            this.virtualProgressInterval = setInterval(() => {
                const now = Date.now();
                const elapsed = now - this.lastProgressUpdateTime;

                // 缓慢增加虚拟进度（仅在服务器没有提供进度时）
                if (this.virtualProgress < 90 && !this.isServerProgressActive) {
                    const increment = elapsed / 60000; // 60秒到90%
                    this.virtualProgress = Math.min(90, this.virtualProgress + increment);
                    this.updateTopTipProgress(this.virtualProgress);
                }

                this.lastProgressUpdateTime = now;
            }, 1000);
        }
    }

    // 更新进度条
    updateTopTipProgress(progress) {
        if (this.progressBar && this.progressText) {
            progress = Math.min(100, Math.max(0, progress));

            // 使用平滑过渡
            this.progressBar.style.transition = 'width 0.3s ease-in-out';
            this.progressBar.style.width = `${progress}%`;
            this.progressText.textContent = `${Math.round(progress)}%`;
        }
    }

    // 隐藏顶部提示条
    hideTopTipOverlay() {
        if (this.topTipOverlay) {
            this.topTipOverlay.style.display = 'none';
        }

        // 清除所有定时器
        this.stopAllTimers();
    }

    // 停止所有定时器
    stopAllTimers() {
        if (this.virtualProgressInterval) {
            clearInterval(this.virtualProgressInterval);
            this.virtualProgressInterval = null;
        }

        if (this.progressUpdateInterval) {
            clearInterval(this.progressUpdateInterval);
            this.progressUpdateInterval = null;
        }

        this.virtualProgress = 0;
        this.serverProgress = 0;
        this.lastProgressUpdateTime = 0;
        this.isServerProgressActive = false;
    }

    createFloatingWindow() {
        this.container = document.createElement('div');
        this.container.id = 'educoder-assistant-floating';
        this.container.className = 'educoder-assistant';

        this.container.innerHTML = `
            <div class="ea-header">
                <div class="ea-title">
                    <span class="ea-icon"></span>
                    <span>Educoder 助手
                    <br>
                    <span class = 'fast-show'>(显示/隐藏快捷键Ctrl+shift+E)</span>
                    </span>
                </div>
                <div class="ea-controls">
                    <button class="ea-btn" id = "minimizeBtn" title="最小化">−</button>
                    <button class="ea-btn" id = "closeBtn" title="关闭">×</button>
                </div>
            </div>

            <div class="ea-body">
                <!-- 连接状态 -->
                <div class="ea-status">
                    <div class="ea-status-item">
                        <span>服务器:</span>
                        <span class="ea-status-value" id="eaServerStatus">未连接</span>
                        <div class="ea-status-indicator" id="eaStatusIndicator"></div>
                    </div>
                    <div class="ea-status-item">
                        <span>页面:</span>
                        <span class="ea-status-value" id="eaPageStatus">就绪</span>
                    </div>
                </div>

                <!-- 连接配置 -->
                <div class="ea-section">
                    <div class="ea-input-group">
                        <label for="eaServerUrl">服务器地址：</label>
                        <input type="text" id="eaServerUrl" placeholder="ws://localhost:8000"
                               class="ea-input">
                    </div>
                    <div class="ea-button-group">
                        <button id="eaConnectBtn" class="ea-btn ea-primary">连接</button>
                        <button id="eaDisconnectBtn" class="ea-btn ea-secondary" disabled>断开</button>
                    </div>
                </div>

                <!-- 内容操作 -->
                <div class="ea-section">
                    <h4>题目处理</h4>
                    <div class="ea-button-group">
                        <button id="eaGetContentBtn" class="ea-btn ea-primary" disabled>
                            获取题目并开始输入
                        </button>
                        <button id="eaSmartFixBtn" class="ea-btn ea-success" disabled>
                            智能纠错
                        </button>
                    </div>

                    <div class="ea-preview-section">
                        <div class="ea-preview">
                            <div class="ea-preview-header">
                                <span>题目内容</span>
                                <span class="ea-preview-count" id="eaContentCount">0 字符</span>
                            </div>
                            <div id="eaContentPreview" class="ea-preview-content">
                                <div class="ea-placeholder">点击"获取题目并开始输入"后题目内容将显示在这里。</div>
                            </div>
                        </div>

                        <div class="ea-preview">
                            <div class="ea-preview-header">
                                <span>测试结果</span>
                                <span class="ea-preview-count" id="eaTestResultCount">0 字符</span>
                            </div>
                            <div id="eaTestResultPreview" class="ea-preview-content">
                                <textarea id="eaTestResultTextarea" class="ea-testresult-textarea"
                                          placeholder="运行测试后，测试结果将自动显示在这里..."
                                          readonly></textarea>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 操作日志 -->
                <div class="ea-section">
                    <div class="ea-log-header">
                        <h4>操作日志</h4>
                        <button id="eaClearLogsBtn" class="ea-btn ea-small">清空</button>
                    </div>
                    <div id="eaMessagesContainer" class="ea-log-container">
                        <div class="ea-placeholder">暂无操作记录</div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(this.container);
        this.initializeElements();
        this.show();
    }

    initializeElements() {
        this.serverUrlInput = document.getElementById('eaServerUrl');
        this.connectBtn = document.getElementById('eaConnectBtn');
        this.disconnectBtn = document.getElementById('eaDisconnectBtn');
        this.header = this.container.querySelector('.ea-header');

        this.getContentBtn = document.getElementById('eaGetContentBtn');
        this.smartFixBtn = document.getElementById('eaSmartFixBtn');
        this.clearLogsBtn = document.getElementById('eaClearLogsBtn');

        this.contentPreview = document.getElementById('eaContentPreview');
        this.contentCount = document.getElementById('eaContentCount');
        this.testResultCount = document.getElementById('eaTestResultCount');
        this.testResultTextarea = document.getElementById('eaTestResultTextarea');

        this.serverStatus = document.getElementById('eaServerStatus');
        this.pageStatus = document.getElementById('eaPageStatus');
        this.statusIndicator = document.getElementById('eaStatusIndicator');

        this.messagesContainer = document.getElementById('eaMessagesContainer');

        this.minimizeBtn = this.container.querySelector('#minimizeBtn');
        this.closeBtn = this.container.querySelector('#closeBtn');
    }

    attachEventListeners() {
        this.connectBtn.addEventListener('click', () => {
            this.showMessage('正在手动连接服务器...', 'system');
            this.connect();
        });
        this.disconnectBtn.addEventListener('click', () => this.disconnect());

        this.getContentBtn.addEventListener('click', () => this.getEducoderContent());
        this.smartFixBtn.addEventListener('click', () => this.smartFix());
        this.clearLogsBtn.addEventListener('click', () => this.clearLogs());

        this.minimizeBtn.addEventListener('click', () => {
            if (this.isMinimized) {
                this.restore();
            } else {
                this.minimize();
            }
        });
        this.closeBtn.addEventListener('click', () => this.hide());

        this.serverUrlInput.addEventListener('change', () => {
            this.saveSettings();
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                this.showMessage('服务器地址已更新，正在重新连接...', 'system');
                setTimeout(() => this.connect(), 500);
            }
        });

        this.attachDragEvents();

        // 监听ESC键
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && (this.isInputInProgress || this.isSmartFixInProgress)) {
                this.showMessage('用户按ESC键终止了代码输入', 'system');
                this.hideTopTipOverlay();
                this.resetInputButtons();
                this.resetSmartFixButton();
            }
        });
    }

    attachDragEvents() {
        this.header.addEventListener('mousedown', (e) => {
            if (e.target.closest('.ea-controls')) return;

            this.dragging = true;
            const rect = this.container.getBoundingClientRect();
            this.dragOffset.x = e.clientX - rect.left;
            this.dragOffset.y = e.clientY - rect.top;

            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!this.dragging) return;

            const x = e.clientX - this.dragOffset.x;
            const y = e.clientY - this.dragOffset.y;

            const maxX = window.innerWidth - this.container.offsetWidth;
            const maxY = window.innerHeight - this.container.offsetHeight;

            this.container.style.left = Math.max(0, Math.min(x, maxX)) + 'px';
            this.container.style.top = Math.max(0, Math.min(y, maxY)) + 'px';
        });

        document.addEventListener('mouseup', (e) => {
            if (!this.dragging) return;

            this.dragging = false;
            this.autoSnapToEdge();
        });
    }

    autoSnapToEdge() {
        const rect = this.container.getBoundingClientRect();
        const windowWidth = window.innerWidth;
        const windowHeight = window.innerHeight;
        const containerWidth = this.container.offsetWidth;
        const containerHeight = this.container.offsetHeight;

        const containerCenterX = rect.left + containerWidth / 2;
        const screenCenterX = windowWidth / 2;

        let newX = rect.left;
        let newY = rect.top;

        if (containerCenterX < screenCenterX) {
            newX = 0;
        } else {
            newX = windowWidth - containerWidth;
        }

        newY = Math.max(0, Math.min(newY, windowHeight - containerHeight));

        this.container.style.left = newX + 'px';
        this.container.style.top = newY + 'px';

        this.saveSettings();
    }

    async loadSettings() {
        try {
            const result = await chrome.storage.local.get(['serverUrl', 'windowPosition']);
            if (result.serverUrl && this.serverUrlInput) {
                this.serverUrlInput.value = result.serverUrl;
            }
            if (result.windowPosition && this.container) {
                this.container.style.left = result.windowPosition.x + 'px';
                this.container.style.top = result.windowPosition.y + 'px';

                setTimeout(() => this.autoSnapToEdge(), 100);
            }
            return result;
        } catch (error) {
            this.showMessage(`加载设置失败: ${error.message}`, 'error');
            return {};
        }
    }

    saveSettings() {
        const rect = this.container.getBoundingClientRect();
        chrome.storage.local.set({
            serverUrl: this.serverUrlInput.value,
            windowPosition: { x: rect.left, y: rect.top }
        });
    }

    async autoConnect() {
        const url = this.serverUrlInput.value.trim();

        if (!url) {
            this.showMessage('未配置服务器地址，请手动连接', 'system');
            return;
        }

        if (this.autoConnectAttempted) {
            return;
        }

        this.autoConnectAttempted = true;
        this.showMessage('正在自动连接服务器...', 'system');

        try {
            await this.connectWebSocket(url);
        } catch (error) {
            this.showMessage(`自动连接失败: ${error.message}`, 'error');
            this.updateConnectionState('CLOSED');
        }
    }

    connectWebSocket(url) {
        return new Promise((resolve, reject) => {
            if (!url) {
                reject(new Error('服务器地址为空'));
                return;
            }

            try {
                this.socket = new WebSocket(url);
                this.updateConnectionState('CONNECTING');

                this.socket.onopen = (event) => {
                    this.updateConnectionState('OPEN');
                    this.showMessage('✅ 连接服务器成功', 'system');
                    resolve(event);
                };

                this.socket.onmessage = (event) => {
                    this.handleServerMessage(event.data);
                };

                this.socket.onerror = (error) => {
                    this.updateConnectionState('CLOSED');
                    this.showMessage('❌ 连接错误', 'error');
                    reject(error);
                };

                this.socket.onclose = (event) => {
                    this.updateConnectionState('CLOSED');
                    const reason = event.code === 1000 ? '正常关闭' : `异常关闭 (代码: ${event.code})`;
                    this.showMessage(`连接关闭: ${reason}`, 'system');

                    // 停止所有进度相关定时器
                    this.stopAllTimers();

                    if (event.code !== 1000 && this.autoConnectAttempted) {
                        setTimeout(() => {
                            this.showMessage('尝试重新连接...', 'system');
                            this.autoConnect();
                        }, 3000);
                    }
                };

            } catch (error) {
                reject(error);
            }
        });
    }

    connect() {
        const url = this.serverUrlInput.value.trim();

        if (!url) {
            this.showMessage('请输入服务器地址', 'error');
            return;
        }

        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.close(1000, '重新连接');
        }

        this.connectWebSocket(url).catch(error => {
            this.showMessage(`手动连接失败: ${error.message}`, 'error');
        });
    }

    handleServerMessage(message) {
        try {
            const data = JSON.parse(message);

            if (data.type === 'code_solution') {
                this.handleCodeSolution(data);
            } else if (data.type === 'code_revision') {
                this.handleCodeRevision(data);
            } else if (data.type === 'ready_for_input') {
                this.handleReadyForInput(data);
            } else if (data.type === 'test_results_response') {
                this.handleTestResultsResponse(data);
            } else if (data.type === 'input_progress') {
                this.handleInputProgress(data);
            } else if (data.type === 'input_complete') {
                this.handleInputComplete(data);
            } else if (data.type === 'input_error') {
                this.handleInputError(data);
            } else if (data.type === 'progress_update') {
                this.handleProgressUpdate(data);
            } else {
                this.showMessage(`服务器: ${JSON.stringify(data)}`, 'received');
            }

        } catch (e) {
            // 处理非JSON消息
            if (typeof message === 'string') {
                this.checkMessageForProgress(message);
                this.showMessage(`服务器: ${message}`, 'received');
            }
        }
    }

    // 处理服务器进度更新
    handleProgressUpdate(data) {
        const progress = data.progress || 0;
        if (progress > 0) {
            this.isServerProgressActive = true;
            this.serverProgress = progress;
            this.updateTopTipProgress(progress);
        }
    }

    checkMessageForProgress(message) {
        // 提取进度百分比
        const progressMatch = message.match(/输入进度:\s*(\d+)%/);
        if (progressMatch) {
            const progress = parseInt(progressMatch[1]);
            this.isServerProgressActive = true;
            this.updateTopTipProgress(progress);
        }
    }

    handleCodeSolution(data) {
        this.generatedCode = data.code;
        this.showMessage('✅ 代码生成完成，准备自动输入...', 'system');

        // 切换到服务器进度
        this.isServerProgressActive = true;
        this.updateTopTipProgress(30);

        // 发送准备输入的消息
        this.startAutoInput();
    }

    handleCodeRevision(data) {
        this.generatedCode = data.revised_code;
        this.retryCount = data.retry_count;

        // 更新智能纠错按钮文字
        this.updateSmartFixButton();

        // 切换到服务器进度
        this.isServerProgressActive = true;
        this.updateTopTipProgress(15);

        // 发送准备输入的消息
        this.startAutoInput();
    }

    handleReadyForInput(data) {
        this.showMessage('✅ 代码已准备就绪，开始自动输入...', 'system');

        // 切换到服务器进度
        this.isServerProgressActive = true;
        this.updateTopTipProgress(45);
    }

    handleTestResultsResponse(data) {
        if (data.success) {
            if (data.has_failures) {
                this.testFailures = data.failures || [];
                this.retryCount = 0;
                this.updateSmartFixButton();

                // 显示测试失败信息
                let failureText = `检测到 ${data.failure_count} 个测试失败：\n\n`;
                data.failures.forEach((failure, index) => {
                    failureText += `失败 ${index + 1}: 测试集 ${failure.test_set_number}\n`;
                    failureText += `错误类型: ${failure.error_type}\n`;
                    if (failure.test_input) {
                        failureText += `测试输入: ${failure.test_input.substring(0, 100)}${failure.test_input.length > 100 ? '...' : ''}\n`;
                    }
                    if (failure.expected_output) {
                        failureText += `预期输出: ${failure.expected_output.substring(0, 100)}${failure.expected_output.length > 100 ? '...' : ''}\n`;
                    }
                    if (failure.actual_output) {
                        failureText += `实际输出: ${failure.actual_output.substring(0, 100)}${failure.actual_output.length > 100 ? '...' : ''}\n`;
                    }
                    failureText += '\n';
                });

                this.showMessage(failureText, 'error');

                // 显示在测试结果文本框中
                if (data.test_results_text) {
                    this.testResultTextarea.value = data.test_results_text;
                    const charCount = data.test_results_text.length;
                    const lineCount = data.test_results_text.split('\n').length;
                    this.testResultCount.textContent = `${charCount} 字符, ${lineCount} 行`;
                }

                this.showMessage(`检测到 ${data.failure_count} 个测试失败，开始纠错...`, 'system');

            } else {
                this.testFailures = [];
                this.updateSmartFixButton();
                this.showMessage('✅ 所有测试通过！代码正确。', 'system');

                // 显示测试结果
                if (data.test_results_text) {
                    this.testResultTextarea.value = data.test_results_text;
                    const charCount = data.test_results_text.length;
                    const lineCount = data.test_results_text.split('\n').length;
                    this.testResultCount.textContent = `${charCount} 字符, ${lineCount} 行`;
                }
            }
        } else {
            this.showMessage('获取测试结果失败', 'error');
        }
    }

    handleInputProgress(data) {
        const progress = data.progress || 0;
        this.isServerProgressActive = true;
        this.updateTopTipProgress(progress);
    }

    handleInputComplete(data) {
        if (data.success) {
            this.showMessage('✅ 代码输入完成', 'system');
            // 设置进度为100%
            this.updateTopTipProgress(100);

            // 延迟1.5秒后隐藏
            setTimeout(() => {
                this.hideTopTipOverlay();
            }, 1500);
        } else if (data.userCancelled) {
            this.showMessage('❌ 用户终止了代码输入', 'system');
            this.hideTopTipOverlay();
        } else {
            this.showMessage('❌ 代码输入失败', 'error');
            this.hideTopTipOverlay();
        }

        // 恢复按钮状态
        this.resetInputButtons();

        // 如果是智能纠错，恢复智能纠错按钮
        if (this.isSmartFixInProgress) {
            this.isSmartFixInProgress = false;
            this.updateSmartFixButton();
        }
    }

    handleInputError(data) {
        this.showMessage(`❌ 输入错误: ${data.message}`, 'error');
        this.hideTopTipOverlay();
        this.resetInputButtons();

        if (this.isSmartFixInProgress) {
            this.isSmartFixInProgress = false;
            this.updateSmartFixButton();
        }
    }

    disconnect() {
        if (this.socket) {
            if (this.socket.readyState === WebSocket.OPEN) {
                this.socket.close(1000, '用户主动断开');
            }
            this.socket = null;
        }
        this.updateConnectionState('CLOSED');
        this.showMessage('已断开服务器连接', 'system');

        // 停止所有定时器
        this.stopAllTimers();
    }

    // 在getEducoderContent函数中立即显示顶部提示条
    async getEducoderContent() {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            this.showMessage('请先建立服务器连接', 'error');
            return;
        }

        if (this.isInputInProgress) {
            this.showMessage('正在输入中，请稍候...', 'warning');
            return;
        }

        try {
            // 更新按钮状态
            this.isInputInProgress = true;
            this.getContentBtn.disabled = true;
            this.getContentBtn.textContent = '输入中...';

            this.showMessage('正在获取题目内容...', 'system');

            // 立即显示顶部提示条，从0%开始
            this.showTopTipOverlay(0, '正在获取题目并生成代码...');

            const content = this.extractPageContent();
            this.currentQuestionContent = content;

            if (content.text) {
                this.showContentPreview(content);

                // 发送题目内容到服务器，并请求自动输入
                const messageData = {
                    type: 'educoder_content_auto_input',
                    timestamp: new Date().toISOString(),
                    url: window.location.href,
                    content: content,
                    auto_input: true
                };

                this.socket.send(JSON.stringify(messageData, null, 2));
                this.showMessage('题目内容已发送到服务器，开始生成并输入代码...', 'sent');

            } else {
                this.showMessage('未找到题目内容', 'error');
                this.clearContentPreview();

                // 恢复按钮状态
                this.resetInputButtons();
                this.hideTopTipOverlay();
            }

        } catch (error) {
            this.showMessage(`获取内容失败: ${error.message}`, 'error');
            console.error('获取内容错误:', error);

            // 恢复按钮状态
            this.resetInputButtons();
            this.hideTopTipOverlay();
        }
    }

    extractPageContent() {
        const targetSelectors = [
            '.tab-panel-body___iueV_.markdown-body.mdBody___raKXb',
            '.markdown-body',
            '.tab-panel-body',
            '.problem-content',
            '.question-content',
            '.problem-description',
            '.shixun-content'
        ];

        let elements = [];
        let allText = '';

        for (const selector of targetSelectors) {
            const foundElements = document.querySelectorAll(selector);
            if (foundElements.length > 0) {
                elements = Array.from(foundElements);
                break;
            }
        }

        if (elements.length === 0) {
            const possibleElements = document.querySelectorAll('div, section, article');
            elements = Array.from(possibleElements).filter(el => {
                const text = el.textContent || '';
                const hasContent = text.length > 200 &&
                    (text.includes('题目') ||
                        text.includes('要求') ||
                        text.includes('编程') ||
                        text.includes('代码') ||
                        text.includes('function') ||
                        text.includes('def ') ||
                        text.includes('public'));
                return hasContent;
            });
        }

        if (elements.length > 0) {
            allText = elements.map(el => {
                let text = el.textContent || '';
                text = text.replace(/\s+/g, ' ').trim();
                return text;
            }).join('\n\n');
        }

        return {
            elements: elements.map(el => ({
                tagName: el.tagName,
                className: el.className,
                textLength: (el.textContent || '').length
            })),
            text: allText,
            timestamp: new Date().toISOString(),
            url: window.location.href
        };
    }

    // 智能纠错函数
    async smartFix() {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            this.showMessage('请先建立服务器连接', 'error');
            return;
        }

        if (this.isInputInProgress) {
            this.showMessage('正在输入中，请稍候...', 'warning');
            return;
        }

        try {
            // 更新按钮状态
            this.isSmartFixInProgress = true;
            this.isInputInProgress = true;
            this.smartFixBtn.disabled = true;
            this.smartFixBtn.textContent = '正在纠错...';

            this.showMessage('正在获取测试结果...', 'system');

            // 立即显示顶部提示条，从0%开始
            this.showTopTipOverlay(0, '正在分析测试结果并纠错...');

            const testResults = this.extractTestResults();

            if (!testResults || !testResults.text) {
                this.showMessage('未找到测试结果，请先运行测试', 'warning');
                this.resetInputButtons();
                this.resetSmartFixButton();
                this.hideTopTipOverlay();
                return;
            }

            // 显示测试结果
            this.testResultTextarea.value = testResults.text;
            const charCount = testResults.text.length;
            const lineCount = testResults.text.split('\n').length;
            this.testResultCount.textContent = `${charCount} 字符, ${lineCount} 行`;

            this.showMessage('正在分析测试结果并进行纠错...', 'system');

            // 发送测试结果到服务器
            const testData = {
                type: 'test_results',
                timestamp: new Date().toISOString(),
                url: window.location.href,
                results: testResults,
                currentCode: this.generatedCode,
                // 始终设置 has_error 为 true，确保服务器进行纠错
                has_error: true
            };

            this.socket.send(JSON.stringify(testData, null, 2));
            this.showMessage('测试结果已发送到服务器，正在进行纠错...', 'sent');

        } catch (error) {
            this.showMessage(`智能纠错失败: ${error.message}`, 'error');
            console.error('智能纠错错误:', error);

            // 恢复按钮状态
            this.resetInputButtons();
            this.resetSmartFixButton();
            this.hideTopTipOverlay();
        }
    }

    extractTestResults() {
        const testResultSelectors = [
            '.judge-result',
            '.test-result',
            '.result-panel',
            '.case-item',
            '.judge-detail',
            '.test-case',
            '.case-content',
            '.run-result',
            '.score-board',
            '.pass-rate',
            '.submit-result',
            '.ant-table-row',
            '.result-table',
            '.test-output',
            '.output-panel',
            '.ant-table-container',
            '.ant-table-tbody',
            '.ant-table-cell'
        ];

        let testElements = [];

        // 先尝试通过选择器查找
        for (const selector of testResultSelectors) {
            const found = document.querySelectorAll(selector);
            if (found.length > 0) {
                testElements = Array.from(found);
                break;
            }
        }

        // 如果没找到，尝试查找包含测试关键信息的元素
        if (testElements.length === 0) {
            const allElements = document.querySelectorAll('div, tr, td, li, span, pre, code, table');
            testElements = Array.from(allElements).filter(el => {
                const text = el.textContent || '';
                const html = el.innerHTML || '';

                const hasTestKeywords = text.includes('测试集1') ||
                                      text.includes('测试输入') ||
                                      text.includes('预期输出') ||
                                      text.includes('实际输出') ||
                                      text.includes('编译失败') ||
                                      text.includes('—— 预期输出 ——') ||
                                      text.includes('—— 实际输出 ——');

                const hasTestStructure = /测试集\d+/.test(text) ||
                                       /测试输入\s*[:：]/.test(text) ||
                                       /预期输出\s*[:：]/.test(text) ||
                                       /实际输出\s*[:：]/.test(text) ||
                                       /消耗内存\s*[:：]\s*\d+\.?\d*MB/.test(text);

                const hasFailureMarkers = html.includes('×') ||
                                        html.includes('✗') ||
                                        html.includes('fail') ||
                                        html.includes('error') ||
                                        html.includes('不正确') ||
                                        html.includes('未通过') ||
                                        html.includes('失败');

                return hasTestKeywords || hasTestStructure || hasFailureMarkers;
            });
        }

        // 如果还没找到，尝试查找结果容器
        if (testElements.length === 0) {
            // 查找常见的结果容器
            const resultContainers = document.querySelectorAll('.ant-table-container, .ant-table-body, table, .result-container, .test-results');
            for (const container of resultContainers) {
                const containerText = container.textContent || '';
                if (containerText.includes('测试集') ||
                    containerText.includes('测试结果') ||
                    containerText.includes('测试输入') ||
                    containerText.includes('预期输出')) {
                    testElements = [container];
                    break;
                }
            }
        }

        if (testElements.length === 0) {
            // 最后尝试：查找所有包含测试信息的文本
            const bodyText = document.body.textContent || '';
            const testPatterns = [
                /测试集\d+[\s\S]*?消耗内存\s*[:：]\s*[\d.]+MB[\s\S]*?测试输入\s*[:：][\s\S]*?—— 预期输出 ——[\s\S]*?—— 实际输出 ——/g,
                /测试集\d+[\s\S]*?测试输入\s*[:：][\s\S]*?预期输出\s*[:：][\s\S]*?实际输出\s*[:：]/g,
                /测试集\d+[\s\S]{1,500}/g
            ];

            for (const pattern of testPatterns) {
                const matches = bodyText.match(pattern);
                if (matches && matches.length > 0) {
                    const tempDiv = document.createElement('div');
                    tempDiv.textContent = matches.join('\n\n');
                    testElements = [tempDiv];
                    break;
                }
            }
        }

        if (testElements.length === 0) {
            // 如果还是没找到，返回null
            return null;
        }

        // 提取关键测试结果信息
        const testResultTexts = testElements.map(el => {
            const text = el.textContent?.trim() || '';
            const html = el.innerHTML?.trim() || '';

            // 清理文本：移除多余空格，保留格式
            let cleanedText = text
                .replace(/\s+/g, ' ')
                .replace(/\s*[:：]\s*/g, ': ')
                .replace(/测试集\s*(\d+)/g, '测试集$1')
                .trim();

            // 提取特定格式的测试结果
            if (text.includes('—— 预期输出 ——') && text.includes('—— 实际输出 ——')) {
                // 保留原始格式
                cleanedText = text;
            }

            // 限制长度，但保留关键信息
            if (cleanedText.length > 3000) {
                // 提取关键段落
                const lines = cleanedText.split('\n');
                const relevantLines = lines.filter(line => {
                    return line.includes('测试集') ||
                           line.includes('测试输入') ||
                           line.includes('预期输出') ||
                           line.includes('实际输出') ||
                           line.includes('消耗内存') ||
                           line.includes('编译失败') ||
                           line.includes('未通过') ||
                           line.includes('失败') ||
                           line.includes('错误') ||
                           /测试集\d+/.test(line);
                });

                cleanedText = relevantLines.join('\n');

                // 如果相关行数太少，返回前1500个字符
                if (cleanedText.length < 200 && text.length > 1500) {
                    cleanedText = text.substring(0, 1500) + '...';
                }
            }

            return {
                text: cleanedText,
                html: html,
                element: el,
                className: el.className,
                tagName: el.tagName
            };
        });

        // 去重和过滤
        const mergedTexts = [];
        for (const result of testResultTexts) {
            const isDuplicate = mergedTexts.some(existing => {
                const similarity = this.calculateTextSimilarity(existing.text, result.text);
                return similarity > 0.8;
            });

            if (!isDuplicate && result.text.length > 20) {
                mergedTexts.push(result);
            }
        }

        // 合并文本，保留重要信息
        let fullText = '';

        // 首先提取包含关键信息的文本
        const keySections = [];

        for (const result of mergedTexts) {
            const text = result.text;

            // 分割文本以提取测试集信息
            const sections = text.split(/(?=测试集\d+)/);

            for (const section of sections) {
                if (section.trim() &&
                    (section.includes('测试集') ||
                     section.includes('测试输入') ||
                     section.includes('预期输出') ||
                     section.includes('实际输出'))) {
                    keySections.push(section.trim());
                }
            }
        }

        // 合并关键部分
        fullText = keySections.join('\n\n');

        // 如果没有关键部分，使用原始文本
        if (!fullText.trim()) {
            fullText = mergedTexts.map(r => r.text).join('\n\n');
        }

        // 如果总文本太长，限制长度
        if (fullText.length > 10000) {
            // 保留最重要的部分（前8000字符）
            fullText = fullText.substring(0, 8000) + '\n...\n[测试结果过长，已截断]';
        }

        return {
            text: fullText,
            rawHtml: mergedTexts.map(r => r.html).join('\n'),
            elements: mergedTexts.map(r => ({
                text: r.text.substring(0, 300),
                className: r.className,
                tagName: r.tagName
            })),
            elementsCount: mergedTexts.length,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            source: 'test_elements'
        };
    }

    startAutoInput() {
        if (!this.generatedCode) {
            this.showMessage('没有可输入的代码', 'warning');
            this.hideTopTipOverlay();
            this.resetInputButtons();
            return;
        }

        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'ready_for_input',
                code: this.generatedCode,
                is_retry: this.retryCount > 0,
                retry_count: this.retryCount
            }));
        }
    }

    updateSmartFixButton() {
        if (this.testFailures.length > 0) {
            this.smartFixBtn.disabled = false;
            this.smartFixBtn.textContent = `开始纠错 (${this.retryCount + 1}/3)`;
            this.smartFixBtn.classList.add('ea-danger');
            this.smartFixBtn.classList.remove('ea-success');
        } else {
            this.smartFixBtn.disabled = false;
            this.smartFixBtn.textContent = '智能纠错';
            this.smartFixBtn.classList.remove('ea-danger');
            this.smartFixBtn.classList.add('ea-success');
        }
    }

    resetSmartFixButton() {
        this.isSmartFixInProgress = false;
        this.updateSmartFixButton();
    }

    resetInputButtons() {
        this.isInputInProgress = false;
        this.getContentBtn.disabled = false;
        this.getContentBtn.textContent = '获取题目并开始输入';

        // 只有在不是智能纠错过程中才恢复智能纠错按钮
        if (!this.isSmartFixInProgress) {
            this.smartFixBtn.disabled = false;
        }
    }

    showContentPreview(content) {
        const charCount = content.text.length;
        const lineCount = content.text.split('\n').length;

        this.contentPreview.innerHTML = `
            <div class="ea-preview-meta">${content.elements.length}个元素, ${charCount}字符, ${lineCount}行</div>
            <div class="ea-preview-text">${this.escapeHtml(content.text.substring(0, 300))}${charCount > 300 ? '...' : ''}</div>
        `;
        this.contentCount.textContent = `${charCount} 字符`;
    }

    clearContentPreview() {
        this.contentPreview.innerHTML = '<div class="ea-placeholder">点击"获取题目"加载内容...</div>';
        this.contentCount.textContent = '0 字符';
    }

    clearLogs() {
        this.messagesContainer.innerHTML = '<div class="ea-placeholder">暂无操作记录</div>';
    }

    updateConnectionState(state) {
        const stateTexts = {
            'CONNECTING': '连接中...',
            'OPEN': '已连接',
            'CLOSING': '关闭中...',
            'CLOSED': '未连接'
        };

        this.serverStatus.textContent = stateTexts[state] || state;

        this.statusIndicator.className = 'ea-status-indicator';
        if (state === 'OPEN') {
            this.statusIndicator.classList.add('ea-connected');
            this.connectBtn.textContent = '已连接';
        } else if (state === 'CONNECTING') {
            this.statusIndicator.classList.add('ea-connecting');
            this.connectBtn.textContent = '连接中...';
        } else {
            this.statusIndicator.classList.add('ea-disconnected');
            this.connectBtn.textContent = '连接';
        }

        const isConnected = state === 'OPEN';
        this.connectBtn.disabled = isConnected;
        this.disconnectBtn.disabled = !isConnected;
        this.getContentBtn.disabled = !isConnected || this.isInputInProgress;
        this.smartFixBtn.disabled = !isConnected || this.isInputInProgress;
    }

    showMessage(text, type = 'system') {
        const messageElement = document.createElement('div');
        messageElement.className = `ea-log-item ea-${type}`;

        const timestamp = new Date().toLocaleTimeString();
        messageElement.innerHTML = `
            <div class="ea-log-time">[${timestamp}]</div>
            <div class="ea-log-text">${this.escapeHtml(text)}</div>
        `;

        const placeholder = this.messagesContainer.querySelector('.ea-placeholder');
        if (placeholder) {
            placeholder.remove();
        }

        this.messagesContainer.appendChild(messageElement);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    show() {
        this.container.classList.add('ea-visible');
        this.isVisible = true;
        this.isMinimized = false;

        setTimeout(() => this.autoSnapToEdge(), 100);
    }

    hide() {
        this.container.classList.remove('ea-visible');
        this.isVisible = false;
    }

    minimize() {
        this.container.style.resize = 'none'
        this.container.classList.add('ea-minimized-state');
        this.isMinimized = true;
        this.minimizeBtn.setAttribute('title', '恢复');
        this.minimizeBtn.textContent = '↗';
        this.currentStyle = [this.container.style.width, this.container.style.height];
        this.container.style.height = '52px';
    }

    restore() {
        this.container.style.resize = 'both'
        this.container.classList.remove('ea-minimized-state');
        this.isMinimized = false;
        this.minimizeBtn.setAttribute('title', '最小化');
        this.minimizeBtn.textContent = '-';
        this.container.style.height = this.currentStyle[1];
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    calculateTextSimilarity(text1, text2) {
        if (!text1 || !text2) return 0;

        const words1 = text1.toLowerCase().split(/\s+/);
        const words2 = text2.toLowerCase().split(/\s+/);

        const set1 = new Set(words1);
        const set2 = new Set(words2);

        const intersection = new Set([...set1].filter(x => set2.has(x)));
        const union = new Set([...set1, ...set2]);

        return intersection.size / union.size;
    }
}

let assistant;

function initAssistant() {
    if (document.getElementById('educoder-assistant-floating')) {
        return;
    }

    assistant = new EducoderFloatingAssistant();

    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.shiftKey && e.key === 'E') {
            e.preventDefault();
            if (assistant.isVisible) {
                assistant.hide();
            } else {
                assistant.show();
            }
        }
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAssistant);
} else {
    initAssistant();
}