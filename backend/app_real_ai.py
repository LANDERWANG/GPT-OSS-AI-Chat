"""
GPT-OSS后端 - 集成真实AI模型
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import json
import asyncio
import os
import sys
from datetime import datetime
from typing import Dict

# 添加项目路径以导入现有的AI模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI(title="GPT-OSS Real AI", version="3.0.0")

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
ai_instances: Dict[str, object] = {}
global_ai_instance = None  # 全域共享的AI實例
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    global global_ai_instance
    
    print("🚀 GPT-OSS Real AI 启动中...")
    print("🔄 正在初始化AI模型...")
    
    # 检查是否可以加载真实模型
    try:
        from conversational_ai import ConversationalAI
        from advanced_chat import AdvancedConversationalAI
        print("✅ AI模块加载成功")
        
        # 创建全域共享的AI實例（只載入一次）
        global_ai_instance = AdvancedConversationalAI(
            model_name="GPT_OSS",  # 使用 GPT-OSS 模型
            generation_style="conservative"
        )
        print("✅ AI模型初始化成功")
        
    except Exception as e:
        print(f"⚠️ AI模型加载失败: {e}")
        print("💡 将使用智能模拟模式")
        global_ai_instance = None

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
    except:
        return [
            {
                "name": "GPT_OSS",
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
        "version": "3.0.0-real-ai",
        "connections": len(websocket_connections),
        "ai_instances": len(ai_instances),
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
                await handle_chat_message(websocket, session_id, message_data)
            elif message_data.get("type") == "interrupt":
                await handle_interrupt(websocket)
            else:
                print(f"未知消息类型: {message_data.get('type')}")
    
    except WebSocketDisconnect:
        print(f"✗ WebSocket连接断开: {session_id}")
        cleanup_session(session_id)
    except Exception as e:
        print(f"WebSocket错误: {e}")
        cleanup_session(session_id)

def cleanup_session(session_id: str):
    """清理会话"""
    if session_id in websocket_connections:
        del websocket_connections[session_id]
    if session_id in ai_instances:
        del ai_instances[session_id]

async def handle_chat_message(websocket: WebSocket, session_id: str, message_data: dict):
    """处理聊天消息"""
    user_message = message_data.get("message", "")
    model_name = message_data.get("model_name", "GPT_OSS")
    generation_style = message_data.get("generation_style", "conservative")
    
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
    
    try:
        # 3. 获取或创建AI实例
        ai_instance = get_or_create_ai_instance(session_id, model_name, generation_style)
        
        # 4. 生成真实AI响应
        if ai_instance:
            print(f"使用真实AI模型生成回答: {model_name}")
            response = await generate_real_ai_response(ai_instance, user_message)
        else:
            print("使用智能模拟模式")
            response = generate_smart_fallback_response(user_message)
        
        # 5. 发送AI响应
        await websocket.send_text(json.dumps({
            "type": "ai_response",
            "message": response,
            "timestamp": datetime.now().isoformat()
        }))
        
    except Exception as e:
        print(f"生成响应失败: {e}")
        await websocket.send_text(json.dumps({
            "type": "ai_response",
            "message": f"抱歉，生成回答时遇到错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }))
    
    # 6. 结束生成
    await websocket.send_text(json.dumps({
        "type": "generation_end",
        "timestamp": datetime.now().isoformat()
    }))

def get_or_create_ai_instance(session_id: str, model_name: str, generation_style: str):
    """获取或创建AI实例 - 使用全域共享實例"""
    global global_ai_instance
    
    # 如果已經有為此會話創建的實例，返回它
    if session_id in ai_instances:
        return ai_instances[session_id]
    
    # 使用全域共享的AI實例（避免重複載入模型）
    if global_ai_instance is not None:
        ai_instances[session_id] = global_ai_instance
        print(f"✅ 为会话 {session_id} 使用共享AI实例")
        return global_ai_instance
    else:
        print(f"⚠️ 全域AI實例不可用，會話 {session_id} 無法使用真實AI")
        return None

async def generate_real_ai_response(ai_instance, user_message: str) -> str:
    """使用真实AI模型生成响应"""
    try:
        print(f"準備生成AI回應，輸入: {user_message[:50]}...")
        
        # 在后台线程中运行AI生成，避免阻塞WebSocket，增加超時機制
        response = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None, ai_instance.generate_response, user_message
            ),
            timeout=60.0  # 60秒超時
        )
        
        print(f"AI回應生成成功: {response[:100] if response else 'None'}...")
        return response
        
    except asyncio.TimeoutError:
        error_msg = "AI模型回應超時（60秒），請稍後再試"
        print(f"超時錯誤: {error_msg}")
        return error_msg
    except Exception as e:
        error_msg = f"AI模型回答时出现错误: {str(e)}"
        print(f"生成錯誤: {error_msg}")
        import traceback
        traceback.print_exc()
        return error_msg

def generate_smart_fallback_response(user_message: str) -> str:
    """智能后备回答（当真实AI不可用时）"""
    message = user_message.lower()
    
    # 更智能的模拟回答
    if any(word in message for word in ["你好", "hello", "hi", "嗨"]):
        return f"你好！我是GPT-OSS智能助手。很高兴与你交流！\n\n关于你说的「{user_message}」，我想说虽然目前我在模拟模式下运行，但我仍然致力于为你提供有价值的对话体验。"
    
    elif any(word in message for word in ["模型", "AI", "智能"]):
        return f"关于AI模型的问题很有趣！\n\n你询问：「{user_message}」\n\n目前系统支持多种模型，包括openai/gpt-oss-20b。我正在努力为你提供最佳的对话体验。你还想了解什么具体方面呢？"
    
    elif any(word in message for word in ["为什么", "如何", "怎么"]):
        return f"这是一个很好的问题！\n\n针对「{user_message}」，让我从几个角度来分析：\n\n1. 首先需要理解问题的核心\n2. 然后考虑可能的解决方案\n3. 最后提供实用的建议\n\n你是想了解更具体的哪个方面呢？"
    
    elif "开发" in message or "编程" in message or "代码" in message:
        return f"关于开发和编程的话题我很感兴趣！\n\n你提到：「{user_message}」\n\n在软件开发领域，有很多值得探讨的内容。无论是架构设计、代码优化，还是新技术学习，我都可以和你交流。\n\n你目前在开发什么项目，或者遇到了什么技术挑战吗？"
    
    else:
        return f"感谢你的消息：「{user_message}」\n\n这是一个很有意思的话题。虽然我目前处于模拟模式，但我会尽力为你提供有价值的回应。\n\n如果你想体验完整的AI对话功能，系统正在努力加载真实的openai/gpt-oss-20b模型。\n\n有什么其他问题我可以帮你思考的吗？"

async def handle_interrupt(websocket: WebSocket):
    """处理中断请求"""
    await websocket.send_text(json.dumps({
        "type": "generation_interrupted",
        "message": "对话已被中断",
        "timestamp": datetime.now().isoformat()
    }))

if __name__ == "__main__":
    import uvicorn
    print("🚀 启动GPT-OSS Real AI服务器...")
    print("📡 地址: http://127.0.0.1:8000")
    print("🤖 集成真实AI模型支持")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")