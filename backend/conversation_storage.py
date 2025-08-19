"""
對話存儲管理模組
提供對話的持久化存儲、檢索和管理功能
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

class ConversationStorage:
    def __init__(self, storage_dir: str = "conversations"):
        """初始化對話存儲"""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.index_file = self.storage_dir / "index.json"
        self.conversations_dir = self.storage_dir / "data"
        self.conversations_dir.mkdir(exist_ok=True)
        
        # 確保索引文件存在
        if not self.index_file.exists():
            self._save_index({})
    
    def _load_index(self) -> Dict:
        """載入對話索引"""
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_index(self, index: Dict):
        """保存對話索引"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    
    def create_conversation(self, session_id: str, title: str = None) -> Dict:
        """創建新對話"""
        conversation_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        if not title:
            title = f"對話 {datetime.now().strftime('%m-%d %H:%M')}"
        
        conversation = {
            "id": conversation_id,
            "session_id": session_id,
            "title": title,
            "created_at": timestamp,
            "updated_at": timestamp,
            "message_count": 0,
            "messages": []
        }
        
        # 保存對話文件
        conv_file = self.conversations_dir / f"{conversation_id}.json"
        with open(conv_file, 'w', encoding='utf-8') as f:
            json.dump(conversation, f, ensure_ascii=False, indent=2)
        
        # 更新索引
        index = self._load_index()
        index[conversation_id] = {
            "id": conversation_id,
            "session_id": session_id,
            "title": title,
            "created_at": timestamp,
            "updated_at": timestamp,
            "message_count": 0,
            "file": f"{conversation_id}.json"
        }
        self._save_index(index)
        
        return conversation
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """獲取對話詳情"""
        conv_file = self.conversations_dir / f"{conversation_id}.json"
        
        if not conv_file.exists():
            return None
        
        try:
            with open(conv_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None
    
    def save_conversation(self, conversation: Dict):
        """保存對話"""
        conversation_id = conversation["id"]
        conversation["updated_at"] = datetime.now().isoformat()
        conversation["message_count"] = len(conversation["messages"])
        
        # 保存對話文件
        conv_file = self.conversations_dir / f"{conversation_id}.json"
        with open(conv_file, 'w', encoding='utf-8') as f:
            json.dump(conversation, f, ensure_ascii=False, indent=2)
        
        # 更新索引
        index = self._load_index()
        if conversation_id in index:
            index[conversation_id].update({
                "title": conversation["title"],
                "updated_at": conversation["updated_at"],
                "message_count": conversation["message_count"]
            })
            self._save_index(index)
    
    def add_message(self, conversation_id: str, user_message: str, ai_response: str):
        """添加消息到對話"""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False
        
        message = {
            "id": str(uuid.uuid4()),
            "user": user_message,
            "assistant": ai_response,
            "timestamp": datetime.now().isoformat()
        }
        
        conversation["messages"].append(message)
        self.save_conversation(conversation)
        return True
    
    def list_conversations(self, limit: int = 50) -> List[Dict]:
        """列出所有對話"""
        index = self._load_index()
        conversations = list(index.values())
        
        # 按更新時間降序排列
        conversations.sort(key=lambda x: x["updated_at"], reverse=True)
        
        return conversations[:limit]
    
    def search_conversations(self, query: str, limit: int = 20) -> List[Dict]:
        """搜索對話"""
        index = self._load_index()
        matching_conversations = []
        
        for conv_info in index.values():
            # 搜索標題
            if query.lower() in conv_info["title"].lower():
                matching_conversations.append(conv_info)
                continue
            
            # 搜索對話內容
            conversation = self.get_conversation(conv_info["id"])
            if conversation:
                for message in conversation["messages"]:
                    if (query.lower() in message["user"].lower() or 
                        query.lower() in message["assistant"].lower()):
                        matching_conversations.append(conv_info)
                        break
        
        # 按更新時間降序排列
        matching_conversations.sort(key=lambda x: x["updated_at"], reverse=True)
        
        return matching_conversations[:limit]
    
    def update_conversation_title(self, conversation_id: str, new_title: str) -> bool:
        """更新對話標題"""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False
        
        conversation["title"] = new_title
        self.save_conversation(conversation)
        return True
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """刪除對話"""
        conv_file = self.conversations_dir / f"{conversation_id}.json"
        
        if conv_file.exists():
            conv_file.unlink()
        
        # 從索引中移除
        index = self._load_index()
        if conversation_id in index:
            del index[conversation_id]
            self._save_index(index)
            return True
        
        return False
    
    def get_conversation_by_session(self, session_id: str) -> Optional[Dict]:
        """根據會話ID獲取對話"""
        index = self._load_index()
        
        for conv_info in index.values():
            if conv_info["session_id"] == session_id:
                return self.get_conversation(conv_info["id"])
        
        return None

# 全局存儲實例
storage = ConversationStorage()