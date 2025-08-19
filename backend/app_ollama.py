# -*- coding: utf-8 -*-
"""
GPT-OSS Ollama 後端 - 使用 Ollama API
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import json
import asyncio
import aiohttp
import os
from datetime import datetime
from typing import Dict, List
from .conversation_storage import storage

app = FastAPI(title="GPT-OSS Ollama", version="4.0.0")

# CORS設置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局變量
websocket_connections: Dict[str, WebSocket] = {}
conversation_history: Dict[str, List[Dict]] = {}  # 儲存每個會話的對話歷史
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

# Ollama 配置
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "gpt-oss:20b"

@app.on_event("startup")
async def startup_event():
    """應用啟動時的初始化"""
    print(">> GPT-OSS Ollama backend starting...")
    
    # 檢查 Ollama 服務是否運行
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{OLLAMA_BASE_URL}/api/tags") as response:
                if response.status == 200:
                    models = await response.json()
                    model_names = [model['name'] for model in models.get('models', [])]
                    
                    if OLLAMA_MODEL in model_names:
                        print(f"[OK] Ollama service running, model {OLLAMA_MODEL} available")
                    else:
                        print(f"[WARNING] Model {OLLAMA_MODEL} not found")
                        print(f"Available models: {model_names}")
                else:
                    print(f"[ERROR] Ollama service error: {response.status}")
    except Exception as e:
        print(f"[ERROR] Cannot connect to Ollama service: {e}")
        print("Please ensure Ollama service is running: ollama serve")

@app.get("/")
async def serve_frontend():
    """服務前端頁面"""
    index_path = os.path.join(frontend_path, "index_new.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"error": "Frontend not found", "path": index_path}

@app.get("/favicon.ico")
async def serve_favicon():
    """服務 favicon"""
    favicon_path = os.path.join(frontend_path, "favicon.svg")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/svg+xml")
    return {"error": "Favicon not found"}

@app.get("/models")
async def get_models():
    """獲取可用模型"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{OLLAMA_BASE_URL}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = []
                    for model in data.get('models', []):
                        models.append({
                            "name": model['name'],
                            "model_id": model['name'],
                            "description": f"Ollama Model - Size: {model.get('size', 'Unknown')}"
                        })
                    return models
                else:
                    return [{"name": OLLAMA_MODEL, "model_id": OLLAMA_MODEL, "description": "GPT-OSS 20B Model"}]
    except:
        return [{"name": OLLAMA_MODEL, "model_id": OLLAMA_MODEL, "description": "GPT-OSS 20B 模型"}]

@app.get("/status")
async def get_status():
    """系統狀態"""
    return {
        "status": "running",
        "version": "4.0.0-ollama",
        "connections": len(websocket_connections),
        "active_sessions": len(conversation_history),
        "model": OLLAMA_MODEL,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """獲取會話歷史"""
    if session_id in conversation_history:
        return {
            "session_id": session_id,
            "history": conversation_history[session_id],
            "total_messages": len(conversation_history[session_id])
        }
    else:
        return {
            "session_id": session_id,
            "history": [],
            "total_messages": 0
        }

@app.delete("/sessions/{session_id}/history")
async def clear_session_history(session_id: str):
    """清除會話歷史"""
    if session_id in conversation_history:
        del conversation_history[session_id]
        return {"message": f"Session {session_id} history cleared"}
    else:
        return {"message": f"Session {session_id} does not exist"}

@app.get("/conversations")
async def list_conversations(limit: int = 50):
    """獲取對話列表"""
    conversations = storage.list_conversations(limit)
    return {"conversations": conversations}

@app.post("/conversations")
async def create_conversation(session_id: str, title: str = None):
    """創建新對話"""
    conversation = storage.create_conversation(session_id, title)
    return conversation

@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """獲取對話詳情"""
    conversation = storage.get_conversation(conversation_id)
    if conversation:
        return conversation
    else:
        return {"error": "Conversation not found"}

@app.put("/conversations/{conversation_id}/title")
async def update_conversation_title(conversation_id: str, request: Request):
    """更新對話標題"""
    data = await request.json()
    title = data.get("title", "")
    success = storage.update_conversation_title(conversation_id, title)
    if success:
        return {"message": "Title updated"}
    else:
        return {"error": "Conversation not found"}

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """刪除對話"""
    success = storage.delete_conversation(conversation_id)
    if success:
        return {"message": "Conversation deleted"}
    else:
        return {"error": "Conversation not found"}

@app.get("/conversations/search")
async def search_conversations(q: str, limit: int = 20):
    """搜索對話"""
    conversations = storage.search_conversations(q, limit)
    return {"conversations": conversations, "query": q}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket連接處理"""
    await websocket.accept()
    websocket_connections[session_id] = websocket
    
    print(f"[+] WebSocket connection established: {session_id}")
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            print(f"Received message: {message_data}")
            
            if message_data.get("type") == "chat":
                await handle_chat_message(websocket, session_id, message_data)
            elif message_data.get("type") == "interrupt":
                await handle_interrupt(websocket)
            else:
                print(f"Unknown message type: {message_data.get('type')}")
    
    except WebSocketDisconnect:
        print(f"[-] WebSocket connection closed: {session_id}")
        cleanup_session(session_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        cleanup_session(session_id)

def cleanup_session(session_id: str):
    """清理會話"""
    if session_id in websocket_connections:
        del websocket_connections[session_id]
    # 保留對話歷史，不刪除（用於記憶功能）

async def handle_chat_message(websocket: WebSocket, session_id: str, message_data: dict):
    """處理聊天消息"""
    user_message = message_data.get("message", "")
    settings = message_data.get("settings", {})
    
    # 初始化會話歷史（如果不存在）
    if session_id not in conversation_history:
        conversation_history[session_id] = []
        
    # 檢查是否需要創建新的持久化對話
    existing_conversation = storage.get_conversation_by_session(session_id)
    if not existing_conversation:
        # 創建新對話，使用用戶消息的前30個字符作為標題
        title = user_message[:30] + "..." if len(user_message) > 30 else user_message
        conversation = storage.create_conversation(session_id, title)
        conversation_id = conversation["id"]
        print(f"Created new conversation: {conversation_id} - {title}")
    else:
        conversation_id = existing_conversation["id"]
    
    # 1. 確認收到用戶消息
    await websocket.send_text(json.dumps({
        "type": "user_message",
        "message": user_message,
        "timestamp": datetime.now().isoformat()
    }))
    
    # 2. 開始生成響應
    await websocket.send_text(json.dumps({
        "type": "generation_start",
        "timestamp": datetime.now().isoformat()
    }))
    
    # 2.5 發送進度提示
    mode_desc = {
        'balanced': 'Balanced Mode',
        'creative': 'Creative Mode',
        'focused': 'Focused Mode',
        'detailed': 'Detailed Mode'
    }.get(settings.get('responseMode', 'balanced'), 'Balanced Mode')
    
    context_info = f" (with {len(conversation_history[session_id])} history)" if conversation_history[session_id] else ""
    
    await websocket.send_text(json.dumps({
        "type": "generation_progress",
        "message": f"Using GPT-OSS:20B model ({mode_desc}){context_info} generating response...",
        "timestamp": datetime.now().isoformat()
    }))
    
    try:
        # 3. 使用 Ollama API 生成回應（包含設置和歷史）
        # 創建一個長時間運行的任務
        generation_task = asyncio.create_task(
            generate_ollama_response(user_message, settings, session_id)
        )
        
        # 在等待響應時發送心跳，不中斷任務
        heartbeat_count = 0
        while not generation_task.done():
            # 等待5秒然後檢查狀態，但不取消任務
            await asyncio.sleep(5.0)
            
            if not generation_task.done():
                heartbeat_count += 1
                progress_messages = [
                    "Model is thinking... please wait",
                    "Processing your request...",
                    "Generating response... (this may take 20-30 seconds for 20B model)",
                    "Still working on your response...",
                    "Almost done, please be patient...",
                ]
                message_index = min(heartbeat_count - 1, len(progress_messages) - 1)
                
                try:
                    await websocket.send_text(json.dumps({
                        "type": "generation_progress", 
                        "message": f"{progress_messages[message_index]} ({heartbeat_count * 5}s)",
                        "timestamp": datetime.now().isoformat()
                    }))
                except:
                    # 如果WebSocket連接斷開，取消任務
                    print(f"WebSocket disconnected, cancelling task for session: {session_id}")
                    generation_task.cancel()
                    return
        
        # 獲取完成的任務結果
        try:
            response = await generation_task
        except asyncio.CancelledError:
            print(f"Generation task was cancelled for session: {session_id}")
            response = "Sorry, the response generation was interrupted. Please try again."
        
        # 4. 記錄對話到內存歷史
        conversation_history[session_id].append({
            "user": user_message,
            "assistant": response,
            "timestamp": datetime.now().isoformat()
        })
        
        # 5. 保存對話到持久化存儲
        storage.add_message(conversation_id, user_message, response)
        print(f"Conversation saved to persistent storage: {conversation_id}")
        
        # 6. 限制內存歷史長度（保留最近10輪對話）
        if len(conversation_history[session_id]) > 10:
            conversation_history[session_id] = conversation_history[session_id][-10:]
        
        # 7. 發送AI響應
        await websocket.send_text(json.dumps({
            "type": "ai_response",
            "message": response,
            "timestamp": datetime.now().isoformat()
        }))
        
    except asyncio.CancelledError:
        print(f"WebSocket connection cancelled for session: {session_id}")
        return  # Don't send response if connection is cancelled
    except Exception as e:
        print(f"Response generation failed: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "ai_response",
                "message": f"Sorry, error occurred while generating response: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }))
        except:
            print(f"Failed to send error message to client: {session_id}")
    
    # 8. 結束生成 (只在連接仍然有效時發送)
    try:
        await websocket.send_text(json.dumps({
            "type": "generation_end",
            "timestamp": datetime.now().isoformat()
        }))
    except:
        print(f"Failed to send generation_end to client: {session_id}")

async def generate_ollama_response(user_message: str, settings: dict = None, session_id: str = None) -> str:
    """使用 Ollama API 生成回應"""
    try:
        if settings is None:
            settings = {}
            
        print(f"Using Ollama to generate response: {user_message[:50]}...")
        print(f"Using settings: {settings}")
        
        # 快速回復常見問題以改善用戶體驗
        quick_responses = {
            "hello": "Hello! How can I help you today?",
            "hi": "Hi there! What can I do for you?", 
            "你好": "你好！有什麼我可以幫助你的嗎？",
            "test": "Test successful! The system is working properly.",
            "測試": "測試成功！系統運行正常。",
        }
        
        message_lower = user_message.lower().strip()
        if message_lower in quick_responses:
            print(f"Quick response for: {message_lower}")
            return quick_responses[message_lower]
        
        # 根據設置調整參數
        response_length = settings.get('responseLength', 2048)
        temperature = settings.get('temperature', 0.7)
        response_mode = settings.get('responseMode', 'balanced')
        
        # 根據回應模式調整參數
        mode_configs = {
            'balanced': {'top_p': 0.9, 'top_k': 40, 'repeat_penalty': 1.1},
            'creative': {'top_p': 0.95, 'top_k': 60, 'repeat_penalty': 1.05},
            'focused': {'top_p': 0.8, 'top_k': 20, 'repeat_penalty': 1.2},
            'detailed': {'top_p': 0.9, 'top_k': 50, 'repeat_penalty': 1.1}
        }
        
        mode_config = mode_configs.get(response_mode, mode_configs['balanced'])
        
        # 構建包含對話歷史的提示 (限制長度以提升速度)
        full_prompt = build_context_prompt(user_message, session_id, max_history=3)
        print(f"Context prompt length: {len(full_prompt)} characters")
        
        # 構建請求數據 - 使用用戶設置和上下文
        request_data = {
            "model": OLLAMA_MODEL,
            "prompt": full_prompt,
            "stream": False,  # 暫時使用非流式響應來修復問題
            "options": {
                "temperature": temperature,
                "top_p": mode_config['top_p'],
                "top_k": mode_config['top_k'],
                "repeat_penalty": mode_config['repeat_penalty'],
                "num_predict": response_length,
                "num_ctx": 4096,
                "num_thread": -1,
            }
        }
        
        # 發送請求到 Ollama (非流式)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=300)
            ) as response:
                
                if response.status == 200:
                    # 處理非流式響應
                    data = await response.json()
                    full_response = data.get("response", "")
                    
                    if full_response.strip():
                        print(f"Ollama response complete: {len(full_response)} characters")
                        return full_response.strip()
                    else:
                        print("Empty response from Ollama")
                        return "Sorry, no valid response received."
                        
                else:
                    error_text = await response.text()
                    print(f"Ollama API error {response.status}: {error_text}")
                    return f"Ollama service error: {response.status}"
                    
    except asyncio.TimeoutError:
        return "Response timeout, please try again later."
    except Exception as e:
        print(f"Ollama request failed: {e}")
        return f"Unable to connect to Ollama service: {str(e)}"

def build_context_prompt(user_message: str, session_id: str, max_history: int = 3) -> str:
    """構建包含對話歷史的提示"""
    if not session_id or session_id not in conversation_history:
        return user_message
    
    history = conversation_history[session_id]
    if not history:
        return user_message
    
    # 構建對話上下文 (限制歷史長度以提升速度)
    context_parts = []
    context_parts.append("Previous conversation history for context:\n")
    
    # 只使用最近的指定輪數對話作為上下文
    recent_history = history[-max_history:] if len(history) > max_history else history
    
    for i, conv in enumerate(recent_history, 1):
        context_parts.append(f"Conversation {i}:")
        context_parts.append(f"User: {conv['user']}")
        context_parts.append(f"Assistant: {conv['assistant']}")
        context_parts.append("")
    
    context_parts.append("Now please answer the following new question:")
    context_parts.append(f"User: {user_message}")
    context_parts.append("Assistant:")
    
    return "\n".join(context_parts)

async def handle_interrupt(websocket: WebSocket):
    """處理中斷請求"""
    await websocket.send_text(json.dumps({
        "type": "generation_interrupted",
        "message": "Conversation interrupted",
        "timestamp": datetime.now().isoformat()
    }))

if __name__ == "__main__":
    import uvicorn
    print(">> Starting GPT-OSS Ollama server...")
    print(">> Address: http://127.0.0.1:8000")
    print(">> Using Ollama model: gpt-oss:20b")
    print(">> Faster, more stable AI chat experience")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")