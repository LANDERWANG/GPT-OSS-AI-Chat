/**
 * GPT-OSS 前端应用主逻辑
 * 处理WebSocket连接、消息收发、UI交互等
 */

class GPTOSSChat {
    constructor() {
        this.ws = null;
        this.currentSessionId = null;
        this.isConnected = false;
        this.isGenerating = false;
        this.settings = {
            apiUrl: 'localhost:8000',
            maxHistory: 10,
            autoSave: true
        };
        
        this.models = [];
        this.generationStyles = [];
        
        this.init();
    }
    
    async init() {
        this.loadSettings();
        await this.loadModelsAndStyles();
        this.setupEventListeners();
        this.createNewSession();
        this.autoResizeTextarea();
    }
    
    // 加载设置
    loadSettings() {
        const saved = localStorage.getItem('gpt-oss-settings');
        if (saved) {
            this.settings = { ...this.settings, ...JSON.parse(saved) };
        }
        
        // 更新UI
        const apiUrlInput = document.getElementById('api-url');
        const maxHistoryInput = document.getElementById('max-history');
        const autoSaveInput = document.getElementById('auto-save');
        
        if (apiUrlInput) apiUrlInput.value = this.settings.apiUrl;
        if (maxHistoryInput) maxHistoryInput.value = this.settings.maxHistory;
        if (autoSaveInput) autoSaveInput.checked = this.settings.autoSave;
    }
    
    // 保存设置
    saveSettings() {
        this.settings.apiUrl = document.getElementById('api-url').value;
        this.settings.maxHistory = parseInt(document.getElementById('max-history').value);
        this.settings.autoSave = document.getElementById('auto-save').checked;
        
        localStorage.setItem('gpt-oss-settings', JSON.stringify(this.settings));
        this.showNotification('设置已保存');
        this.toggleSettings();
    }
    
    // 加载模型和生成风格
    async loadModelsAndStyles() {
        try {
            // 构建HTTP URL
            let baseUrl = this.settings.apiUrl;
            if (!baseUrl.startsWith('http://') && !baseUrl.startsWith('https://')) {
                baseUrl = 'http://' + baseUrl;
            }
            
            console.log('加载配置从:', baseUrl);
            
            // 获取模型列表
            const modelsResponse = await fetch(`${baseUrl}/models`);
            if (modelsResponse.ok) {
                this.models = await modelsResponse.json();
                this.updateModelSelect();
                console.log('模型列表加载成功:', this.models);
            }
            
            // 获取生成风格
            const stylesResponse = await fetch(`${baseUrl}/generation-styles`);
            if (stylesResponse.ok) {
                this.generationStyles = await stylesResponse.json();
                this.updateStyleSelect();
                console.log('生成风格加载成功:', this.generationStyles);
            }
            
        } catch (error) {
            console.warn('无法加载模型配置，使用默认配置:', error);
            // 使用默认配置
            this.models = [
                { name: "GPT_OSS", model_id: "openai/gpt-oss-20b", description: "大型对话模型" }
            ];
            this.generationStyles = [
                { name: "conservative", settings: {} },
                { name: "creative", settings: {} },
                { name: "focused", settings: {} }
            ];
            this.updateModelSelect();
            this.updateStyleSelect();
        }
    }
    
    updateModelSelect() {
        const select = document.getElementById('model-select');
        select.innerHTML = '';
        
        this.models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.name;
            option.textContent = `${model.name} (${model.model_id})`;
            select.appendChild(option);
        });
    }
    
    updateStyleSelect() {
        const select = document.getElementById('style-select');
        select.innerHTML = '';
        
        this.generationStyles.forEach(style => {
            const option = document.createElement('option');
            option.value = style.name;
            option.textContent = this.getStyleDisplayName(style.name);
            select.appendChild(option);
        });
    }
    
    getStyleDisplayName(styleName) {
        const names = {
            'conservative': '保守',
            'creative': '创意',
            'focused': '专注'
        };
        return names[styleName] || styleName;
    }
    
    // 设置事件监听器
    setupEventListeners() {
        const input = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');
        
        // 输入框变化事件
        input.addEventListener('input', () => {
            this.autoResizeTextarea();
            sendBtn.disabled = !input.value.trim() || this.isGenerating;
        });
        
        // 全局键盘事件
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isGenerating) {
                this.stopGeneration();
            }
        });
        
        // 窗口关闭事件
        window.addEventListener('beforeunload', () => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.close();
            }
        });
    }
    
    // 自动调整输入框高度
    autoResizeTextarea() {
        const textarea = document.getElementById('message-input');
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
    
    // 创建新会话
    createNewSession() {
        this.currentSessionId = this.generateSessionId();
        this.clearChat();
        this.connect();
        this.addSessionToHistory(this.currentSessionId);
    }
    
    generateSessionId() {
        return 'session-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    }
    
    // WebSocket连接
    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.close();
        }
        
        // 修复WebSocket URL构建
        let wsUrl = this.settings.apiUrl;
        if (wsUrl.startsWith('http://')) {
            wsUrl = wsUrl.replace('http://', 'ws://');
        } else if (wsUrl.startsWith('https://')) {
            wsUrl = wsUrl.replace('https://', 'wss://');
        } else if (!wsUrl.startsWith('ws://') && !wsUrl.startsWith('wss://')) {
            wsUrl = 'ws://' + wsUrl;
        }
        
        const fullWsUrl = `${wsUrl}/ws/${this.currentSessionId}`;
        console.log('连接WebSocket:', fullWsUrl);
        this.ws = new WebSocket(fullWsUrl);
        
        this.ws.onopen = () => {
            this.isConnected = true;
            this.updateConnectionStatus('在线', true);
            console.log('WebSocket连接已建立');
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket错误:', error);
            this.updateConnectionStatus('连接错误', false);
        };
        
        this.ws.onclose = () => {
            this.isConnected = false;
            this.updateConnectionStatus('离线', false);
            console.log('WebSocket连接已关闭');
            
            // 自动重连
            setTimeout(() => {
                if (!this.isConnected) {
                    this.connect();
                }
            }, 3000);
        };
    }
    
    // 处理收到的消息
    handleMessage(data) {
        switch (data.type) {
            case 'user_message':
                // 用户消息确认，通常不需要处理
                break;
                
            case 'ai_response':
                this.hideTypingIndicator();
                this.addMessage(data.message, 'ai', data.timestamp);
                this.setGenerating(false);
                break;
                
            case 'generation_start':
                this.showTypingIndicator();
                this.setGenerating(true);
                break;
                
            case 'generation_end':
                this.hideTypingIndicator();
                this.setGenerating(false);
                break;
                
            case 'generation_interrupted':
                this.hideTypingIndicator();
                this.addMessage('生成已被中断', 'system', data.timestamp);
                this.setGenerating(false);
                break;
                
            case 'error':
                this.hideTypingIndicator();
                this.addMessage(`错误: ${data.message}`, 'error', data.timestamp);
                this.setGenerating(false);
                break;
                
            case 'system':
                this.addMessage(data.message, 'system', data.timestamp);
                break;
        }
    }
    
    // 发送消息
    sendMessage() {
        const input = document.getElementById('message-input');
        const message = input.value.trim();
        
        if (!message || this.isGenerating || !this.isConnected) {
            return;
        }
        
        // 添加用户消息到界面
        this.addMessage(message, 'user');
        
        // 发送到服务器
        const messageData = {
            type: 'chat',
            message: message,
            model_name: document.getElementById('model-select').value,
            generation_style: document.getElementById('style-select').value
        };
        
        this.ws.send(JSON.stringify(messageData));
        
        // 清空输入框
        input.value = '';
        this.autoResizeTextarea();
        document.getElementById('send-btn').disabled = true;
        
        // 隐藏欢迎界面
        this.hideWelcomeScreen();
    }
    
    // 停止生成
    stopGeneration() {
        if (this.isGenerating && this.ws && this.ws.readyState === WebSocket.OPEN) {
            const interruptData = {
                type: 'interrupt'
            };
            this.ws.send(JSON.stringify(interruptData));
            this.setGenerating(false);
        }
    }
    
    // 添加消息到界面
    addMessage(content, type = 'user', timestamp = null) {
        const chatMessages = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.textContent = content;
        
        const messageMeta = document.createElement('div');
        messageMeta.className = 'message-meta';
        const time = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
        messageMeta.textContent = time;
        
        messageDiv.appendChild(messageContent);
        messageDiv.appendChild(messageMeta);
        
        chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    // 显示打字指示器
    showTypingIndicator() {
        const existing = document.querySelector('.typing-indicator');
        if (existing) return;
        
        const chatMessages = document.getElementById('chat-messages');
        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator';
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.className = 'typing-dot';
            indicator.appendChild(dot);
        }
        
        chatMessages.appendChild(indicator);
        this.scrollToBottom();
    }
    
    // 隐藏打字指示器
    hideTypingIndicator() {
        const indicator = document.querySelector('.typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    // 设置生成状态
    setGenerating(generating) {
        this.isGenerating = generating;
        
        const sendBtn = document.getElementById('send-btn');
        const stopBtn = document.getElementById('stop-btn');
        const input = document.getElementById('message-input');
        
        if (generating) {
            sendBtn.style.display = 'none';
            stopBtn.style.display = 'flex';
            input.disabled = true;
        } else {
            sendBtn.style.display = 'flex';
            stopBtn.style.display = 'none';
            input.disabled = false;
            sendBtn.disabled = !input.value.trim();
        }
    }
    
    // 更新连接状态
    updateConnectionStatus(status, isOnline) {
        const statusElement = document.getElementById('connection-status');
        const dot = statusElement.querySelector('.status-dot');
        const text = statusElement.querySelector('span:last-child');
        
        dot.className = `status-dot ${isOnline ? 'online' : 'offline'}`;
        text.textContent = status;
    }
    
    // 滚动到底部
    scrollToBottom() {
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // 清空聊天
    clearChat() {
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.innerHTML = `
            <div class="welcome-screen" id="welcome-screen">
                <div class="welcome-icon">🤖</div>
                <h2>欢迎使用 GPT-OSS 智能交互系统</h2>
                <p>基于 openai/gpt-oss-20b 模型的智能对话系统</p>
            </div>
        `;
    }
    
    // 隐藏欢迎界面
    hideWelcomeScreen() {
        const welcomeScreen = document.getElementById('welcome-screen');
        if (welcomeScreen) {
            welcomeScreen.style.display = 'none';
        }
    }
    
    // 添加会话到历史
    addSessionToHistory(sessionId) {
        const sessionList = document.getElementById('today-sessions');
        
        // 检查是否已存在
        const existingSession = document.querySelector(`[data-session-id="${sessionId}"]`);
        if (existingSession) {
            existingSession.classList.add('active');
            return;
        }
        
        // 移除其他active状态
        sessionList.querySelectorAll('.session-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // 创建新会话项
        const sessionItem = document.createElement('div');
        sessionItem.className = 'session-item active';
        sessionItem.dataset.sessionId = sessionId;
        sessionItem.textContent = `新对话 ${new Date().toLocaleTimeString()}`;
        
        sessionItem.addEventListener('click', () => {
            this.switchToSession(sessionId);
        });
        
        sessionList.insertBefore(sessionItem, sessionList.firstChild);
    }
    
    // 切换到指定会话
    switchToSession(sessionId) {
        if (sessionId === this.currentSessionId) return;
        
        this.currentSessionId = sessionId;
        this.clearChat();
        this.connect();
        
        // 更新UI状态
        document.querySelectorAll('.session-item').forEach(item => {
            item.classList.toggle('active', item.dataset.sessionId === sessionId);
        });
    }
    
    // 显示通知
    showNotification(message) {
        // 创建简单的通知
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #28a745;
            color: white;
            padding: 12px 20px;
            border-radius: 6px;
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

// 全局函数（供HTML调用）
let chatApp;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    chatApp = new GPTOSSChat();
});

// HTML调用的全局函数
function startNewChat() {
    chatApp.createNewSession();
}

function sendMessage() {
    chatApp.sendMessage();
}

function stopGeneration() {
    chatApp.stopGeneration();
}

function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function updateModel() {
    // 模型更新逻辑，如果需要的话
    console.log('模型已更新:', document.getElementById('model-select').value);
}

function updateGenerationStyle() {
    // 生成风格更新逻辑
    console.log('生成风格已更新:', document.getElementById('style-select').value);
}

function toggleSettings() {
    const panel = document.getElementById('settings-panel');
    panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
}

function saveSettings() {
    chatApp.saveSettings();
}

// 添加CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);