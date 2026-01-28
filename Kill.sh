#!/bin/sh

PROCESS="/home/ubuntu/pyProject/daily_post/main.py"

pids=$(pgrep -f "$PROCESS")

if [ -z "$pids" ]; then
    echo "[INFO] 未找到进程：$PROCESS"
    exit 0
fi

echo "[INFO] 找到进程 PID：$pids"
echo "[INFO] 正在杀死进程..."

kill -9 $pids

echo "[OK] 进程已终止"

