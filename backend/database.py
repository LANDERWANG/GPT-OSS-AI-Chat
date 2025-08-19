"""
数据库管理模块
处理对话历史、会话管理和持久化存储
"""

import sqlite3
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
import aiosqlite
import os

logger = logging.getLogger(__name__)

@dataclass
class ChatSession:
    session_id: str
    model_name: str
    generation_style: str
    created_at: datetime
    last_activity: datetime
    message_count: int = 0
    is_active: bool = True

@dataclass
class ChatMessage:
    message_id: str
    session_id: str
    user_message: str
    ai_response: str
    timestamp: datetime
    generation_time: float = 0.0
    context_info: Optional[Dict] = None

class DatabaseManager:
    def __init__(self, db_path: str = "chat_history.db"):
        self.db_path = db_path
        self.connection_pool = {}
    
    async def initialize(self):
        """初始化数据库表结构"""
        async with aiosqlite.connect(self.db_path) as db:
            # 创建会话表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    model_name TEXT NOT NULL,
                    generation_style TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    last_activity TIMESTAMP NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # 创建消息表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    ai_response TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    generation_time REAL DEFAULT 0.0,
                    context_info TEXT,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions (session_id)
                )
            """)
            
            # 创建记忆表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS context_memory (
                    session_id TEXT NOT NULL,
                    memory_key TEXT NOT NULL,
                    memory_value TEXT NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (session_id, memory_key),
                    FOREIGN KEY (session_id) REFERENCES chat_sessions (session_id)
                )
            """)
            
            # 创建索引
            await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages (session_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON chat_messages (timestamp)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_activity ON chat_sessions (last_activity)")
            
            await db.commit()
        
        logger.info("数据库初始化完成")
    
    async def create_session(self, session: ChatSession) -> bool:
        """创建新会话"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO chat_sessions 
                    (session_id, model_name, generation_style, created_at, last_activity, message_count, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    session.session_id,
                    session.model_name,
                    session.generation_style,
                    session.created_at.isoformat(),
                    session.last_activity.isoformat(),
                    session.message_count,
                    session.is_active
                ))
                await db.commit()
            
            logger.info(f"会话已创建: {session.session_id}")
            return True
        
        except Exception as e:
            logger.error(f"创建会话失败: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取会话信息"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT session_id, model_name, generation_style, created_at, 
                           last_activity, message_count, is_active
                    FROM chat_sessions WHERE session_id = ?
                """, (session_id,)) as cursor:
                    row = await cursor.fetchone()
                    
                    if row:
                        return ChatSession(
                            session_id=row[0],
                            model_name=row[1],
                            generation_style=row[2],
                            created_at=datetime.fromisoformat(row[3]),
                            last_activity=datetime.fromisoformat(row[4]),
                            message_count=row[5],
                            is_active=bool(row[6])
                        )
        
        except Exception as e:
            logger.error(f"获取会话失败: {e}")
        
        return None
    
    async def update_session_activity(self, session_id: str):
        """更新会话活跃时间"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE chat_sessions 
                    SET last_activity = ?, message_count = message_count + 1
                    WHERE session_id = ?
                """, (datetime.now().isoformat(), session_id))
                await db.commit()
        
        except Exception as e:
            logger.error(f"更新会话活跃时间失败: {e}")
    
    async def save_message(self, message: ChatMessage) -> bool:
        """保存对话消息"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 保存消息
                await db.execute("""
                    INSERT INTO chat_messages 
                    (message_id, session_id, user_message, ai_response, timestamp, 
                     generation_time, context_info)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    message.message_id,
                    message.session_id,
                    message.user_message,
                    message.ai_response,
                    message.timestamp.isoformat(),
                    message.generation_time,
                    json.dumps(message.context_info, ensure_ascii=False) if message.context_info else None
                ))
                
                # 更新会话活跃时间
                await db.execute("""
                    UPDATE chat_sessions 
                    SET last_activity = ?, message_count = message_count + 1
                    WHERE session_id = ?
                """, (message.timestamp.isoformat(), message.session_id))
                
                await db.commit()
            
            logger.info(f"消息已保存: {message.message_id}")
            return True
        
        except Exception as e:
            logger.error(f"保存消息失败: {e}")
            return False
    
    async def get_session_messages(self, session_id: str, limit: int = 50, offset: int = 0) -> List[ChatMessage]:
        """获取会话消息历史"""
        messages = []
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT message_id, session_id, user_message, ai_response, 
                           timestamp, generation_time, context_info
                    FROM chat_messages 
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (session_id, limit, offset)) as cursor:
                    async for row in cursor:
                        context_info = None
                        if row[6]:
                            try:
                                context_info = json.loads(row[6])
                            except json.JSONDecodeError:
                                pass
                        
                        messages.append(ChatMessage(
                            message_id=row[0],
                            session_id=row[1],
                            user_message=row[2],
                            ai_response=row[3],
                            timestamp=datetime.fromisoformat(row[4]),
                            generation_time=row[5],
                            context_info=context_info
                        ))
        
        except Exception as e:
            logger.error(f"获取会话消息失败: {e}")
        
        return messages
    
    async def save_context_memory(self, session_id: str, memory: Dict[str, str]):
        """保存上下文记忆"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 清除旧记忆
                await db.execute("DELETE FROM context_memory WHERE session_id = ?", (session_id,))
                
                # 保存新记忆
                for key, value in memory.items():
                    await db.execute("""
                        INSERT INTO context_memory (session_id, memory_key, memory_value, updated_at)
                        VALUES (?, ?, ?, ?)
                    """, (session_id, key, value, datetime.now().isoformat()))
                
                await db.commit()
            
            logger.info(f"记忆已保存: {session_id}")
        
        except Exception as e:
            logger.error(f"保存记忆失败: {e}")
    
    async def load_context_memory(self, session_id: str) -> Dict[str, str]:
        """加载上下文记忆"""
        memory = {}
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT memory_key, memory_value 
                    FROM context_memory 
                    WHERE session_id = ?
                """, (session_id,)) as cursor:
                    async for row in cursor:
                        memory[row[0]] = row[1]
        
        except Exception as e:
            logger.error(f"加载记忆失败: {e}")
        
        return memory
    
    async def get_active_sessions(self, limit: int = 20) -> List[ChatSession]:
        """获取活跃会话列表"""
        sessions = []
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT session_id, model_name, generation_style, created_at,
                           last_activity, message_count, is_active
                    FROM chat_sessions 
                    WHERE is_active = 1
                    ORDER BY last_activity DESC
                    LIMIT ?
                """, (limit,)) as cursor:
                    async for row in cursor:
                        sessions.append(ChatSession(
                            session_id=row[0],
                            model_name=row[1],
                            generation_style=row[2],
                            created_at=datetime.fromisoformat(row[3]),
                            last_activity=datetime.fromisoformat(row[4]),
                            message_count=row[5],
                            is_active=bool(row[6])
                        ))
        
        except Exception as e:
            logger.error(f"获取活跃会话失败: {e}")
        
        return sessions
    
    async def deactivate_session(self, session_id: str) -> bool:
        """停用会话"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE chat_sessions 
                    SET is_active = 0, last_activity = ?
                    WHERE session_id = ?
                """, (datetime.now().isoformat(), session_id))
                await db.commit()
            
            logger.info(f"会话已停用: {session_id}")
            return True
        
        except Exception as e:
            logger.error(f"停用会话失败: {e}")
            return False
    
    async def cleanup_old_sessions(self, days: int = 30) -> int:
        """清理旧会话"""
        try:
            cutoff_date = datetime.now().replace(day=datetime.now().day - days)
            
            async with aiosqlite.connect(self.db_path) as db:
                # 获取要删除的会话数量
                async with db.execute("""
                    SELECT COUNT(*) FROM chat_sessions 
                    WHERE last_activity < ? AND is_active = 0
                """, (cutoff_date.isoformat(),)) as cursor:
                    count = await cursor.fetchone()
                    count = count[0] if count else 0
                
                if count > 0:
                    # 删除相关消息
                    await db.execute("""
                        DELETE FROM chat_messages 
                        WHERE session_id IN (
                            SELECT session_id FROM chat_sessions 
                            WHERE last_activity < ? AND is_active = 0
                        )
                    """, (cutoff_date.isoformat(),))
                    
                    # 删除相关记忆
                    await db.execute("""
                        DELETE FROM context_memory 
                        WHERE session_id IN (
                            SELECT session_id FROM chat_sessions 
                            WHERE last_activity < ? AND is_active = 0
                        )
                    """, (cutoff_date.isoformat(),))
                    
                    # 删除会话
                    await db.execute("""
                        DELETE FROM chat_sessions 
                        WHERE last_activity < ? AND is_active = 0
                    """, (cutoff_date.isoformat(),))
                    
                    await db.commit()
                
                logger.info(f"清理了 {count} 个旧会话")
                return count
        
        except Exception as e:
            logger.error(f"清理旧会话失败: {e}")
            return 0

# 全局数据库管理器实例
db_manager = DatabaseManager()

# 初始化函数
async def init_database():
    """初始化数据库"""
    await db_manager.initialize()
    logger.info("数据库管理器初始化完成")