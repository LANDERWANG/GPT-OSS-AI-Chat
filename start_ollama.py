"""
GPT-OSS Ollama 版本啟動腳本
"""

import os
import sys
import subprocess
import webbrowser
import time
import threading
import requests
from pathlib import Path

# 設置控制台編碼為UTF-8
if os.name == 'nt':  # Windows
    os.system('chcp 65001 > nul')

def check_ollama_service():
    """檢查 Ollama 服務是否運行"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_ollama_service():
    """啟動 Ollama 服務"""
    print("[+] 啟動 Ollama 服務...")
    try:
        subprocess.Popen(
            ["ollama", "serve"], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )
        
        # 等待服務啟動
        for i in range(10):
            if check_ollama_service():
                print("[OK] Ollama 服務啟動成功")
                return True
            print(f"[*] 等待 Ollama 服務啟動... ({i+1}/10)")
            time.sleep(2)
        
        print("[ERROR] Ollama 服務啟動失敗")
        return False
        
    except Exception as e:
        print(f"[ERROR] 啟動 Ollama 服務時出錯: {e}")
        return False

def check_model_available():
    """檢查 GPT-OSS 模型是否可用"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [model['name'] for model in models]
            
            if 'gpt-oss:20b' in model_names:
                print("[OK] GPT-OSS:20B 模型可用")
                return True
            else:
                print("⚠️ GPT-OSS:20B 模型未找到")
                print(f"可用模型: {model_names}")
                
                if model_names:
                    print("\n💡 您可以選擇其他可用模型，或者執行以下命令安裝 GPT-OSS:")
                    print("   ollama pull gpt-oss:20b")
                else:
                    print("\n💡 請先安裝 GPT-OSS 模型:")
                    print("   ollama pull gpt-oss:20b")
                return False
        else:
            print(f"[ERROR] 無法獲取模型列表: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[ERROR] 檢查模型時出錯: {e}")
        return False

def kill_port_8000():
    """清理8000端口"""
    try:
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        for line in lines:
            if ':8000' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    print(f"發現進程 {pid} 占用端口8000，正在結束...")
                    subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                    print(f"進程 {pid} 已結束")
                    time.sleep(1)
                    break
    except Exception as e:
        print(f"清理端口時出錯: {e}")

def main():
    print("=" * 60)
    print("GPT-OSS Ollama 版本")
    print("   更快、更穩定的 AI 對話體驗")
    print("=" * 60)
    
    # 清理端口
    print("[+] 正在清理端口8000...")
    kill_port_8000()
    
    # 檢查 Ollama 是否安裝
    try:
        result = subprocess.run(['ollama', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[OK] Ollama 已安裝: {result.stdout.strip()}")
        else:
            print("[ERROR] Ollama 未正確安裝")
            return
    except FileNotFoundError:
        print("[ERROR] Ollama 未安裝，請先安裝 Ollama: https://ollama.ai")
        input("按 Enter 退出...")
        return
    
    # 檢查 Ollama 服務
    if not check_ollama_service():
        print("⚠️ Ollama 服務未運行，正在啟動...")
        if not start_ollama_service():
            print("[ERROR] 無法啟動 Ollama 服務")
            input("按 Enter 退出...")
            return
    else:
        print("[OK] Ollama 服務正在運行")
    
    # 檢查模型
    if not check_model_available():
        print("\n[ERROR] GPT-OSS 模型不可用")
        choice = input("是否現在下載 GPT-OSS:20B 模型？ (y/n): ")
        if choice.lower() == 'y':
            print("[+] 正在下載 GPT-OSS:20B 模型（這可能需要一些時間）...")
            try:
                subprocess.run(['ollama', 'pull', 'gpt-oss:20b'], check=True)
                print("[OK] 模型下載完成")
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] 模型下載失敗: {e}")
                input("按 Enter 退出...")
                return
        else:
            print("取消啟動")
            return
    
    # 設置工作目錄
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # 檢查必需文件
    required_files = [
        "frontend/index_new.html",
        "backend/app_ollama.py"
    ]
    
    print("\n[+] 文件檢查:")
    all_files_exist = True
    for file in required_files:
        if os.path.exists(file):
            print(f"[OK] {file}")
        else:
            print(f"✗ {file} - 缺失")
            all_files_exist = False
    
    if not all_files_exist:
        print("[ERROR] 缺少必需文件")
        input("按 Enter 退出...")
        return
    
    # 檢查依賴
    print("\n[+] 依賴檢查:")
    try:
        import fastapi, uvicorn, aiohttp
        print("[OK] FastAPI、Uvicorn、aiohttp 已安裝")
    except ImportError as e:
        print(f"⚠️ 缺少依賴: {e}")
        print("正在安裝...")
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", 
                "fastapi", "uvicorn[standard]", "aiohttp"
            ], check=True, capture_output=True)
            print("[OK] 依賴安裝完成")
        except Exception as install_error:
            print(f"[ERROR] 依賴安裝失敗: {install_error}")
            input("按 Enter 退出...")
            return
    
    print("\n[+] 啟動信息:")
    print("• 使用 Ollama API")
    print("• 模型: gpt-oss:20b")
    print("• 地址: http://127.0.0.1:8000")
    print("• 快速、穩定的回應")
    print("-" * 60)
    
    # 延迟打开浏览器
    def open_browser():
        time.sleep(3)
        try:
            webbrowser.open('http://127.0.0.1:8000')
            print("[OK] 瀏覽器已自動打開")
        except:
            print("⚠️ 請手動打開 http://127.0.0.1:8000")
    
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    try:
        # 啟動 Ollama 版本服務器
        from backend.app_ollama import app
        import uvicorn
        
        print("[+] 正在啟動 Ollama 服務器...")
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="info",
            access_log=True
        )
        
    except KeyboardInterrupt:
        print("\n🛑 服務器已停止")
    except Exception as e:
        print(f"[ERROR] 啟動失敗: {e}")
        import traceback
        traceback.print_exc()
        input("\n按 Enter 退出...")

if __name__ == "__main__":
    main()