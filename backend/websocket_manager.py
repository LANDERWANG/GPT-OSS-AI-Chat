"""
WebSocket连接管理器
处理实时对话、连接管理和中断控制
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Set, Optional
from fastapi import WebSocket
import threading

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # WebSocket连接池
        self.active_connections: Dict[str, WebSocket] = {}
        # 会话到连接的映射
        self.session_connections: Dict[str, str] = {}
        # 生成任务管理
        self.generation_tasks: Dict[str, asyncio.Task] = {}
        # 中断信号
        self.interrupt_signals: Dict[str, threading.Event] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """接受WebSocket连接"""
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        
        self.active_connections[connection_id] = websocket
        self.session_connections[session_id] = connection_id
        self.interrupt_signals[session_id] = threading.Event()
        
        logger.info(f"WebSocket连接建立 - Session: {session_id}, Connection: {connection_id}")
        
        return connection_id
    
    def disconnect(self, session_id: str):
        """断开WebSocket连接"""
        if session_id in self.session_connections:
            connection_id = self.session_connections[session_id]
            
            # 清理连接
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
            del self.session_connections[session_id]
            
            # 取消生成任务
            if session_id in self.generation_tasks:
                self.generation_tasks[session_id].cancel()
                del self.generation_tasks[session_id]
            
            # 清理中断信号
            if session_id in self.interrupt_signals:
                del self.interrupt_signals[session_id]
            
            logger.info(f"WebSocket连接断开 - Session: {session_id}")
    
    async def send_message(self, session_id: str, message: dict):
        """向特定会话发送消息"""
        if session_id in self.session_connections:
            connection_id = self.session_connections[session_id]
            if connection_id in self.active_connections:
                websocket = self.active_connections[connection_id]
                try:
                    await websocket.send_text(json.dumps(message, ensure_ascii=False))
                    return True
                except Exception as e:
                    logger.error(f"发送消息失败: {e}")
                    self.disconnect(session_id)
        return False
    
    async def broadcast(self, message: dict):
        """广播消息到所有连接"""
        disconnected_sessions = []
        for session_id, connection_id in self.session_connections.items():
            if not await self.send_message(session_id, message):
                disconnected_sessions.append(session_id)
        
        # 清理断开的连接
        for session_id in disconnected_sessions:
            self.disconnect(session_id)
    
    def set_interrupt_signal(self, session_id: str):
        """设置中断信号"""
        if session_id in self.interrupt_signals:
            self.interrupt_signals[session_id].set()
            logger.info(f"中断信号已设置 - Session: {session_id}")
            return True
        return False
    
    def is_interrupted(self, session_id: str) -> bool:
        """检查是否已被中断"""
        if session_id in self.interrupt_signals:
            return self.interrupt_signals[session_id].is_set()
        return False
    
    def clear_interrupt_signal(self, session_id: str):
        """清除中断信号"""
        if session_id in self.interrupt_signals:
            self.interrupt_signals[session_id].clear()
    
    async def start_generation_task(self, session_id: str, generation_func, *args, **kwargs):
        """启动生成任务"""
        # 取消现有任务
        if session_id in self.generation_tasks:
            self.generation_tasks[session_id].cancel()
        
        # 清除中断信号
        self.clear_interrupt_signal(session_id)
        
        # 创建新任务
        task = asyncio.create_task(
            self._run_generation_with_interrupt(session_id, generation_func, *args, **kwargs)
        )
        self.generation_tasks[session_id] = task
        
        return task
    
    async def _run_generation_with_interrupt(self, session_id: str, generation_func, *args, **kwargs):
        """带中断检查的生成任务执行器"""
        try:
            # 发送开始生成消息
            await self.send_message(session_id, {
                "type": "generation_start",
                "timestamp": datetime.now().isoformat()
            })
            
            # 在线程中执行生成，支持中断
            def generation_with_check():
                # 这里需要修改 ConversationalAI 类来支持中断检查
                return generation_func(*args, **kwargs)
            
            result = await asyncio.get_event_loop().run_in_executor(
                None, generation_with_check
            )
            
            # 检查是否被中断
            if self.is_interrupted(session_id):
                await self.send_message(session_id, {
                    "type": "generation_interrupted",
                    "message": "生成已被中断",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                await self.send_message(session_id, {
                    "type": "ai_response",
                    "message": result,
                    "timestamp": datetime.now().isoformat()
                })
        
        except asyncio.CancelledError:
            await self.send_message(session_id, {
                "type": "generation_cancelled",
                "message": "生成任务已取消",
                "timestamp": datetime.now().isoformat()
            })
        
        except Exception as e:
            logger.error(f"生成任务错误: {e}")
            await self.send_message(session_id, {
                "type": "error",
                "message": f"生成失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
        
        finally:
            # 清理任务
            if session_id in self.generation_tasks:
                del self.generation_tasks[session_id]
            await self.send_message(session_id, {
                "type": "generation_end",
                "timestamp": datetime.now().isoformat()
            })

# 全局连接管理器实例
manager = ConnectionManager()

# 消息类型定义
class MessageTypes:
    USER_MESSAGE = "user_message"
    AI_RESPONSE = "ai_response"
    GENERATION_START = "generation_start"
    GENERATION_END = "generation_end"
    GENERATION_INTERRUPTED = "generation_interrupted"
    GENERATION_CANCELLED = "generation_cancelled"
    ERROR = "error"
    SYSTEM = "system"
    TYPING = "typing"

# WebSocket消息处理器
class MessageHandler:
    def __init__(self, connection_manager: ConnectionManager):
        self.manager = connection_manager
    
    async def handle_message(self, session_id: str, message_data: dict):
        """处理接收到的WebSocket消息"""
        message_type = message_data.get("type", "chat")
        
        if message_type == "chat":
            await self._handle_chat_message(session_id, message_data)
        elif message_type == "interrupt":
            await self._handle_interrupt(session_id)
        elif message_type == "ping":
            await self._handle_ping(session_id)
        else:
            logger.warning(f"未知消息类型: {message_type}")
    
    async def _handle_chat_message(self, session_id: str, message_data: dict):
        """处理聊天消息"""
        message = message_data.get("message", "")
        if not message:
            return
        
        # 确认收到用户消息
        await self.manager.send_message(session_id, {
            "type": MessageTypes.USER_MESSAGE,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _handle_interrupt(self, session_id: str):
        """处理中断请求"""
        success = self.manager.set_interrupt_signal(session_id)
        if success:
            await self.manager.send_message(session_id, {
                "type": MessageTypes.SYSTEM,
                "message": "中断信号已发送",
                "timestamp": datetime.now().isoformat()
            })
    
    async def _handle_ping(self, session_id: str):
        """处理心跳检测"""
        await self.manager.send_message(session_id, {
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        })

# 全局消息处理器
message_handler = MessageHandler(manager)