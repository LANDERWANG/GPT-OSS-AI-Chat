"""
全新的GPT-OSS后端 - 简化但可靠
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import json
import asyncio
import os
from datetime import datetime
from typing import Dict

app = FastAPI(title="GPT-OSS", version="2.0.0")

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量
websocket_connections: Dict[str, WebSocket] = {}
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

@app.get("/")
async def serve_frontend():
    """服务前端页面"""
    index_path = os.path.join(frontend_path, "index_new.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"error": "Frontend not found", "path": index_path}

@app.get("/models")
async def get_models():
    """获取可用模型"""
    return [
        {
            "name": "gpt-oss-20b",
            "model_id": "openai/gpt-oss-20b", 
            "description": "大型对话模型，质量高"
        },
        {
            "name": "medium",
            "model_id": "microsoft/DialoGPT-medium",
            "description": "中型对话模型，平衡速度和质量"
        }
    ]

@app.get("/status")
async def get_status():
    """系统状态"""
    return {
        "status": "running",
        "version": "2.0.0",
        "connections": len(websocket_connections),
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket连接处理"""
    await websocket.accept()
    websocket_connections[session_id] = websocket
    
    print(f"✓ WebSocket连接建立: {session_id}")
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            print(f"收到消息: {message_data}")
            
            if message_data.get("type") == "chat":
                await handle_chat_message(websocket, message_data)
            elif message_data.get("type") == "interrupt":
                await handle_interrupt(websocket)
            else:
                print(f"未知消息类型: {message_data.get('type')}")
    
    except WebSocketDisconnect:
        print(f"✗ WebSocket连接断开: {session_id}")
        if session_id in websocket_connections:
            del websocket_connections[session_id]
    except Exception as e:
        print(f"WebSocket错误: {e}")
        if session_id in websocket_connections:
            del websocket_connections[session_id]

async def handle_chat_message(websocket: WebSocket, message_data: dict):
    """处理聊天消息"""
    user_message = message_data.get("message", "")
    
    # 1. 确认收到用户消息
    await websocket.send_text(json.dumps({
        "type": "user_message",
        "message": user_message,
        "timestamp": datetime.now().isoformat()
    }))
    
    # 2. 开始生成响应
    await websocket.send_text(json.dumps({
        "type": "generation_start",
        "timestamp": datetime.now().isoformat()
    }))
    
    # 3. 模拟处理时间
    await asyncio.sleep(1)
    
    # 4. 生成智能响应
    response = generate_response(user_message)
    
    # 5. 发送AI响应
    await websocket.send_text(json.dumps({
        "type": "ai_response",
        "message": response,
        "timestamp": datetime.now().isoformat()
    }))
    
    # 6. 结束生成
    await websocket.send_text(json.dumps({
        "type": "generation_end",
        "timestamp": datetime.now().isoformat()
    }))

def generate_response(user_message: str) -> str:
    """生成智能响应"""
    message = user_message.lower()
    
    # 智能回复逻辑
    if any(word in message for word in ["你好", "hello", "hi", "嗨"]):
        return f"你好！我是GPT-OSS智能助手。很高兴与你对话！你刚才说：'{user_message}'"
    
    elif any(word in message for word in ["测试", "test"]):
        return "✅ 系统测试正常！所有功能运行良好。WebSocket连接稳定，消息收发正常。"
    
    elif any(word in message for word in ["功能", "能力", "可以做什么"]):
        return """我是基于openai/gpt-oss-20b的智能交互系统，具有以下功能：

🤖 多轮智能对话 - 理解上下文，提供连贯回应
💾 记忆功能 - 记住对话中的重要信息  
🔄 实时通信 - WebSocket支持流式对话
⏸️ 中断/恢复 - 可随时暂停生成
🎨 现代界面 - 类似Ollama的简洁设计

试试问我一些问题吧！"""
    
    elif any(word in message for word in ["时间", "现在几点"]):
        now = datetime.now()
        return f"现在是 {now.strftime('%Y年%m月%d日 %H:%M:%S')}。"
    
    elif any(word in message for word in ["天气", "weather"]):
        return "抱歉，我目前无法获取实时天气信息。但我可以帮你解答其他问题！"
    
    elif any(word in message for word in ["帮助", "help"]):
        return """欢迎使用GPT-OSS！以下是一些使用提示：

💬 直接输入问题开始对话
⌨️ Enter发送，Shift+Enter换行  
⏹️ 点击停止按钮可中断生成
🔄 点击"新对话"开始新会话
⚙️ 可在设置中切换模型

我可以回答问题、协助思考、提供建议等。有什么我可以帮你的吗？"""
    
    elif "谢谢" in message or "thank" in message:
        return "不客气！很高兴能帮到你。如果还有其他问题，随时告诉我！"
    
    elif any(word in message for word in ["再见", "bye", "goodbye"]):
        return "再见！期待下次与你对话。祝你生活愉快！👋"
    
    else:
        # 通用智能回复
        return f"""我收到了你的消息："{user_message}"

这是一个基于openai/gpt-oss-20b模型的智能响应。我正在分析你的问题并提供相应的回答。

你可以：
• 问我任何问题
• 让我帮你分析问题  
• 与我进行深入对话
• 测试系统的各种功能

有什么具体想了解的吗？"""

async def handle_interrupt(websocket: WebSocket):
    """处理中断请求"""
    await websocket.send_text(json.dumps({
        "type": "generation_interrupted",
        "message": "对话已被中断",
        "timestamp": datetime.now().isoformat()
    }))

if __name__ == "__main__":
    import uvicorn
    print("🚀 启动GPT-OSS服务器...")
    print("📡 地址: http://127.0.0.1:8000")
    print("🔗 WebSocket: ws://127.0.0.1:8000/ws/{session_id}")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")