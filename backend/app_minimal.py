"""
最小化版本的GPT-OSS后端 - 用于测试基础功能
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json
import uuid
import asyncio
from datetime import datetime
from typing import Dict
import os

app = FastAPI(title="GPT-OSS智能交互系统 (测试版)", version="1.0.0")

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# 添加各种静态文件路由
@app.get("/styles.css")
async def get_styles():
    css_path = os.path.join(frontend_path, "styles.css")
    if os.path.exists(css_path):
        return FileResponse(css_path, media_type="text/css")
    return {"error": "CSS file not found"}

@app.get("/app.js")
async def get_app_js():
    js_path = os.path.join(frontend_path, "app.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    return {"error": "JS file not found"}

# 简单的内存存储
active_sessions: Dict[str, dict] = {}
websocket_connections: Dict[str, WebSocket] = {}

@app.get("/")
async def root():
    """主页面"""
    frontend_index = os.path.join(frontend_path, "index.html")
    if os.path.exists(frontend_index):
        return FileResponse(frontend_index)
    return {"message": "GPT-OSS API 测试版运行中", "frontend_available": False}

@app.get("/models")
async def get_models():
    """获取模型列表"""
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models_config.json")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        models = []
        for name, info in config["models"].items():
            models.append({
                "name": name,
                "model_id": info["model_id"],
                "description": info.get("description", "")
            })
        return models
    except Exception as e:
        return [{"name": "GPT_OSS", "model_id": "openai/gpt-oss-20b", "description": "默认模型"}]

@app.get("/generation-styles")
async def get_styles():
    """获取生成风格"""
    return [
        {"name": "conservative", "settings": {"temperature": 0.7}},
        {"name": "creative", "settings": {"temperature": 0.9}},
        {"name": "focused", "settings": {"temperature": 0.5}}
    ]

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket连接"""
    await websocket.accept()
    websocket_connections[session_id] = websocket
    
    print(f"WebSocket连接建立: {session_id}")
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "chat":
                user_message = message_data.get("message", "")
                
                # 确认收到用户消息
                await websocket.send_text(json.dumps({
                    "type": "user_message",
                    "message": user_message,
                    "timestamp": datetime.now().isoformat()
                }))
                
                # 显示正在生成
                await websocket.send_text(json.dumps({
                    "type": "generation_start",
                    "timestamp": datetime.now().isoformat()
                }))
                
                # 模拟AI响应 (在实际系统中这里会调用真实的AI模型)
                await asyncio.sleep(1)  # 模拟生成时间
                
                # 简单的模拟响应
                if "你好" in user_message or "hello" in user_message.lower():
                    response = f"你好！我是GPT-OSS智能助手。你刚才说：'{user_message}'"
                elif "测试" in user_message:
                    response = "系统测试正常！所有功能运行良好。"
                elif "功能" in user_message:
                    response = "我支持多轮对话、记忆功能、实时通信等功能。这是一个基于openai/gpt-oss-20b的智能交互系统。"
                else:
                    response = f"我收到了你的消息：'{user_message}'。这是一个测试响应，证明系统正在正常工作。"
                
                # 发送AI响应
                await websocket.send_text(json.dumps({
                    "type": "ai_response",
                    "message": response,
                    "timestamp": datetime.now().isoformat()
                }))
                
                # 生成结束
                await websocket.send_text(json.dumps({
                    "type": "generation_end",
                    "timestamp": datetime.now().isoformat()
                }))
            
            elif message_data.get("type") == "interrupt":
                await websocket.send_text(json.dumps({
                    "type": "generation_interrupted",
                    "message": "生成已中断",
                    "timestamp": datetime.now().isoformat()
                }))
    
    except WebSocketDisconnect:
        print(f"WebSocket连接断开: {session_id}")
        if session_id in websocket_connections:
            del websocket_connections[session_id]
    except Exception as e:
        print(f"WebSocket错误: {e}")
        if session_id in websocket_connections:
            del websocket_connections[session_id]

@app.get("/api/status")
async def get_status():
    """系统状态"""
    return {
        "status": "running",
        "version": "1.0.0-minimal",
        "active_sessions": len(active_sessions),
        "websocket_connections": len(websocket_connections),
        "message": "最小化测试版本正在运行"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)