"""
智能交互系统后端 API
基于 FastAPI + WebSocket 实现实时对话
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
import asyncio
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional
import logging
import sys
import os

# 添加父目录到路径以导入现有的AI模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from conversational_ai import ConversationalAI
from advanced_chat import AdvancedConversationalAI

# 导入新的管理模块
from websocket_manager import manager, message_handler, MessageTypes
from database import db_manager, ChatSession, ChatMessage as DBChatMessage, init_database

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GPT-OSS智能交互系统",
    description="基于openai/gpt-oss-20b的智能对话系统",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# 数据模型
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    model_name: Optional[str] = "GPT_OSS"
    generation_style: Optional[str] = "conservative"

class SessionInfo(BaseModel):
    session_id: str
    created_at: datetime
    model_name: str
    generation_style: str
    message_count: int
    last_activity: datetime

class ModelConfig(BaseModel):
    name: str
    model_id: str
    description: str

class GenerationStyle(BaseModel):
    name: str
    settings: Dict

# 全局变量
active_sessions: Dict[str, AdvancedConversationalAI] = {}
websocket_connections: Dict[str, WebSocket] = {}

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    logger.info("🚀 GPT-OSS智能交互系统启动中...")
    
    # 初始化数据库
    try:
        await init_database()
        logger.info("✅ 数据库初始化成功")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
    
    # 预加载默认模型（可选）
    try:
        # 创建一个默认会话以验证模型加载
        test_session = AdvancedConversationalAI(
            model_name="medium",  # 使用较小的模型进行测试
            generation_style="conservative"
        )
        logger.info("✅ 默认模型加载成功")
    except Exception as e:
        logger.warning(f"⚠️ 默认模型加载失败: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    logger.info("🔄 正在关闭系统...")
    # 清理所有会话
    active_sessions.clear()
    websocket_connections.clear()

# REST API 端点
@app.get("/")
async def root():
    """根路径 - 重定向到前端界面"""
    frontend_index = os.path.join(frontend_path, "index.html")
    if os.path.exists(frontend_index):
        return FileResponse(frontend_index)
    else:
        return {
            "message": "GPT-OSS智能交互系统API",
            "version": "1.0.0",
            "active_sessions": len(active_sessions),
            "frontend_path": frontend_path
        }

@app.get("/api")
async def api_info():
    """API信息端点"""
    return {
        "message": "GPT-OSS智能交互系统API",
        "version": "1.0.0",
        "active_sessions": len(active_sessions),
        "endpoints": {
            "websocket": "/ws/{session_id}",
            "models": "/models",
            "sessions": "/sessions",
            "chat": "/chat"
        }
    }

@app.get("/models", response_model=List[ModelConfig])
async def get_available_models():
    """获取可用模型列表"""
    try:
        with open("models_config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        models = []
        for name, info in config["models"].items():
            models.append(ModelConfig(
                name=name,
                model_id=info["model_id"],
                description=info.get("description", "")
            ))
        
        return models
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(status_code=500, detail="无法获取模型列表")

@app.get("/generation-styles", response_model=List[GenerationStyle])
async def get_generation_styles():
    """获取可用的生成风格"""
    try:
        with open("models_config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        styles = []
        for name, settings in config["generation_settings"].items():
            styles.append(GenerationStyle(
                name=name,
                settings=settings
            ))
        
        return styles
    except Exception as e:
        logger.error(f"获取生成风格失败: {e}")
        raise HTTPException(status_code=500, detail="无法获取生成风格")

@app.get("/sessions", response_model=List[SessionInfo])
async def get_active_sessions():
    """获取活跃会话列表"""
    sessions = []
    for session_id, ai in active_sessions.items():
        sessions.append(SessionInfo(
            session_id=session_id,
            created_at=datetime.now(),  # 实际应该从数据库获取
            model_name="GPT_OSS",  # 实际应该从会话信息获取
            generation_style="conservative",
            message_count=len(ai.conversation_history),
            last_activity=datetime.now()
        ))
    
    return sessions

@app.post("/sessions")
async def create_session(
    model_name: str = "GPT_OSS",
    generation_style: str = "conservative"
):
    """创建新的会话"""
    session_id = str(uuid.uuid4())
    
    try:
        # 创建新的AI实例
        ai = AdvancedConversationalAI(
            model_name=model_name,
            generation_style=generation_style
        )
        
        active_sessions[session_id] = ai
        
        logger.info(f"✅ 创建新会话: {session_id}")
        
        return {
            "session_id": session_id,
            "model_name": model_name,
            "generation_style": generation_style,
            "created_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    if session_id in active_sessions:
        del active_sessions[session_id]
        if session_id in websocket_connections:
            del websocket_connections[session_id]
        
        logger.info(f"🗑️ 删除会话: {session_id}")
        return {"message": "会话已删除"}
    else:
        raise HTTPException(status_code=404, detail="会话不存在")

@app.post("/chat")
async def chat_message(chat: ChatMessage):
    """发送聊天消息 (REST API)"""
    session_id = chat.session_id or str(uuid.uuid4())
    
    # 获取或创建AI实例
    if session_id not in active_sessions:
        try:
            ai = AdvancedConversationalAI(
                model_name=chat.model_name,
                generation_style=chat.generation_style
            )
            active_sessions[session_id] = ai
        except Exception as e:
            logger.error(f"创建AI实例失败: {e}")
            raise HTTPException(status_code=500, detail=f"创建AI实例失败: {str(e)}")
    
    ai = active_sessions[session_id]
    
    try:
        # 生成响应
        response = await asyncio.create_task(
            asyncio.to_thread(ai.generate_response, chat.message)
        )
        
        return {
            "session_id": session_id,
            "user_message": chat.message,
            "ai_response": response,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"生成响应失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成响应失败: {str(e)}")

# WebSocket 端点
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket连接处理"""
    connection_id = await manager.connect(websocket, session_id)
    
    # 创建或获取会话信息
    session_info = await db_manager.get_session(session_id)
    if not session_info:
        session_info = ChatSession(
            session_id=session_id,
            model_name="GPT_OSS",
            generation_style="conservative",
            created_at=datetime.now(),
            last_activity=datetime.now()
        )
        await db_manager.create_session(session_info)
    
    logger.info(f"🔗 WebSocket连接建立: {session_id}")
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # 处理不同类型的消息
            await message_handler.handle_message(session_id, message_data)
            
            # 如果是聊天消息，执行AI生成
            if message_data.get("type", "chat") == "chat":
                message = message_data.get("message", "")
                model_name = message_data.get("model_name", session_info.model_name)
                generation_style = message_data.get("generation_style", session_info.generation_style)
                
                if message:
                    # 获取或创建AI实例
                    if session_id not in active_sessions:
                        try:
                            ai = AdvancedConversationalAI(
                                model_name=model_name,
                                generation_style=generation_style
                            )
                            active_sessions[session_id] = ai
                            
                            # 恢复上下文记忆
                            memory = await db_manager.load_context_memory(session_id)
                            if memory:
                                ai.context_memory.update(memory)
                                
                        except Exception as e:
                            await manager.send_message(session_id, {
                                "type": MessageTypes.ERROR,
                                "message": f"创建AI实例失败: {str(e)}"
                            })
                            continue
                    
                    ai = active_sessions[session_id]
                    
                    # 启动生成任务（支持中断）
                    await manager.start_generation_task(
                        session_id,
                        ai.generate_response,
                        message
                    )
                    
                    # 保存对话到数据库
                    try:
                        # 等待生成完成
                        if session_id in manager.generation_tasks:
                            response = await manager.generation_tasks[session_id]
                            
                            # 保存消息
                            chat_message = DBChatMessage(
                                message_id=str(uuid.uuid4()),
                                session_id=session_id,
                                user_message=message,
                                ai_response=response or "",
                                timestamp=datetime.now(),
                                generation_time=0.0,
                                context_info=ai.context_memory
                            )
                            
                            await db_manager.save_message(chat_message)
                            await db_manager.save_context_memory(session_id, ai.context_memory)
                            
                    except Exception as e:
                        logger.error(f"保存对话失败: {e}")
    
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket连接断开: {session_id}")
        manager.disconnect(session_id)
    
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        manager.disconnect(session_id)

# 会话管理端点
@app.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """获取会话历史"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    ai = active_sessions[session_id]
    return {
        "session_id": session_id,
        "history": ai.conversation_history,
        "memory": ai.context_memory
    }

@app.post("/sessions/{session_id}/interrupt")
async def interrupt_session(session_id: str):
    """中断会话生成"""
    success = manager.set_interrupt_signal(session_id)
    if success:
        return {"message": "中断信号已发送", "session_id": session_id}
    else:
        raise HTTPException(status_code=404, detail="会话不存在或未在生成中")

@app.post("/sessions/{session_id}/resume")
async def resume_session(session_id: str):
    """恢复会话"""
    # 清除中断信号
    manager.clear_interrupt_signal(session_id)
    
    # 获取会话历史
    messages = await db_manager.get_session_messages(session_id, limit=10)
    memory = await db_manager.load_context_memory(session_id)
    
    return {
        "message": "会话已恢复",
        "session_id": session_id,
        "recent_messages": [
            {
                "user_message": msg.user_message,
                "ai_response": msg.ai_response,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in messages
        ],
        "context_memory": memory
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")