"""
工程標案智能查詢系統 - 依賴安裝腳本
"""

import subprocess
import sys

def install_requirements():
    """安裝所需的Python套件"""
    
    requirements = [
        "mysql-connector-python",  # MySQL資料庫連接
        "speechrecognition",       # 語音識別
        "matplotlib",              # 繪圖
        "pandas",                  # 數據處理
        "numpy",                   # 數值計算
        "seaborn",                 # 統計繪圖
        "plotly",                  # 互動式圖表
        "pyaudio",                 # 音頻處理（語音輸入需要）
    ]
    
    print("正在安裝工程標案查詢系統所需的套件...")
    print("需要安裝的套件:")
    for req in requirements:
        print(f"  • {req}")
    
    print("\n開始安裝...")
    
    for package in requirements:
        try:
            print(f"正在安裝 {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} 安裝成功")
        except subprocess.CalledProcessError:
            print(f"❌ {package} 安裝失敗")
            if package == "pyaudio":
                print("PyAudio 安裝可能需要額外步驟，請參考:")
                print("Windows: pip install pipwin && pipwin install pyaudio")
                print("Mac: brew install portaudio && pip install pyaudio")
                print("Linux: sudo apt-get install python3-pyaudio")
    
    print("\n✅ 套件安裝完成！")
    print("\n📋 系統需求檢查:")
    
    # 檢查套件是否正確安裝
    import_checks = {
        "mysql.connector": "MySQL連接器",
        "speech_recognition": "語音識別",
        "matplotlib": "圖表繪製",
        "pandas": "數據處理",
        "plotly": "互動式圖表"
    }
    
    for module, description in import_checks.items():
        try:
            __import__(module)
            print(f"✅ {description} - 可用")
        except ImportError:
            print(f"❌ {description} - 不可用")
    
    print("\n🗄️ 資料庫設置提醒:")
    print("1. 安裝 MySQL 服務器")
    print("2. 創建資料庫和表格（參考 engineering_query_system.py 中的 create_sample_database 函數）")
    print("3. 修改 db_config 中的連接參數")
    
    print("\n🎤 語音功能提醒:")
    print("1. 確保電腦有麥克風")
    print("2. 語音識別需要網絡連接（使用Google語音服務）")
    print("3. 如果語音功能有問題，可以只使用文字輸入")

if __name__ == "__main__":
    install_requirements()
