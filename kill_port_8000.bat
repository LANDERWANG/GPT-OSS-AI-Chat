@echo off
echo 正在检查端口8000占用情况...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    echo 发现进程ID: %%a 占用端口8000
    echo 正在结束进程...
    taskkill /F /PID %%a
    if errorlevel 1 (
        echo 结束进程失败，请手动结束
    ) else (
        echo 进程已成功结束
    )
)

echo 端口8000现在应该可用了
pause