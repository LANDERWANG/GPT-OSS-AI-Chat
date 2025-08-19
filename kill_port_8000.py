#!/usr/bin/env python3
"""
終止占用端口 8000 的程序
"""

import subprocess
import sys
import re

def find_process_using_port(port):
    """查找使用指定端口的程序"""
    try:
        # 在 Windows 上使用 netstat 命令
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, encoding='gbk')
        
        lines = result.stdout.split('\n')
        for line in lines:
            if f':{port}' in line and 'LISTENING' in line:
                # 提取 PID
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    if pid.isdigit():
                        return int(pid)
        
        return None
    except Exception as e:
        print(f"查找程序失敗: {e}")
        return None

def get_process_name(pid):
    """獲取程序名稱"""
    try:
        result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], 
                              capture_output=True, text=True, encoding='gbk')
        lines = result.stdout.split('\n')
        for line in lines:
            if str(pid) in line:
                parts = line.split()
                if len(parts) > 0:
                    return parts[0]
        return "未知程序"
    except Exception as e:
        return f"錯誤: {e}"

def kill_process(pid):
    """終止程序"""
    try:
        subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                      capture_output=True, text=True)
        return True
    except Exception as e:
        print(f"終止程序失敗: {e}")
        return False

def main():
    print("=" * 60)
    print("🔍 檢查端口 8000 使用情況")
    print("=" * 60)
    
    pid = find_process_using_port(8000)
    
    if pid:
        process_name = get_process_name(pid)
        print(f"🔴 發現程序占用端口 8000:")
        print(f"   程序名: {process_name}")
        print(f"   PID: {pid}")
        
        choice = input("\n是否要終止此程序? (y/n): ")
        if choice.lower() in ['y', 'yes', '是']:
            print(f"🔄 正在終止程序 {pid}...")
            if kill_process(pid):
                print(f"✅ 程序 {pid} 已被終止")
                print("🚀 現在可以重新啟動你的系統!")
            else:
                print(f"❌ 無法終止程序 {pid}")
                print("💡 你可能需要手動關閉該程序")
        else:
            print("❌ 用戶取消操作")
    else:
        print("✅ 端口 8000 目前沒有被占用")
        print("🚀 可以啟動系統")

if __name__ == "__main__":
    main()