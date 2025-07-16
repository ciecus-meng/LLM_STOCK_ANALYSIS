#!/bin/bash

# 智能分析系统管理脚本
# 功能：启动、停止、重启和监控系统服务

# 配置
APP_NAME="智能分析系统"
APP_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_CMD="python"
SERVER_MODULE="web_server" # 改为模块名
SERVER_SCRIPT="web_server.py" # 新增，用于文件检查
PID_FILE="${APP_DIR}/.server.pid"
LOG_FILE="${APP_DIR}/server.log"
WORKER_SCRIPT="background_worker.py"
WORKER_PID_FILE="${APP_DIR}/.worker.pid"
WORKER_LOG_FILE="${APP_DIR}/worker.log"
MONITOR_INTERVAL=30  # 监控检查间隔（秒）

# 颜色配置
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# 函数：显示帮助信息
show_help() {
    echo -e "${BLUE}${APP_NAME}管理脚本${NC}"
    echo "使用方法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start       启动服务"
    echo "  stop        停止服务"
    echo "  restart     重启服务"
    echo "  status      查看服务状态"
    echo "  monitor     以守护进程方式监控服务"
    echo "  logs        查看日志"
    echo "  help        显示此帮助信息"
}

# 函数：检查前置条件
check_prerequisites() {
    # 检查Python是否已安装
    if ! command -v $PYTHON_CMD &> /dev/null; then
        echo -e "${RED}错误: 未找到Python命令。请确保Python已安装且在PATH中。${NC}"
        exit 1
    fi

    # 检查server脚本是否存在
    if [ ! -f "${APP_DIR}/${SERVER_SCRIPT}" ]; then
        echo -e "${RED}错误: 未找到服务器脚本 ${SERVER_SCRIPT}。${NC}"
        echo -e "${YELLOW}当前目录: $(pwd)${NC}"
        exit 1
    fi

    # 检查worker脚本是否存在
    if [ ! -f "${APP_DIR}/${WORKER_SCRIPT}" ]; then
        echo -e "${RED}错误: 未找到工作进程脚本 ${WORKER_SCRIPT}。${NC}"
        exit 1
    fi
}

# 函数：初始化数据库
init_database() {
    echo -e "${BLUE}正在检查并初始化数据库...${NC}"
    $PYTHON_CMD -c "from database import init_db; init_db()"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}数据库初始化成功。${NC}"
    else
        echo -e "${RED}数据库初始化失败。请检查错误信息。${NC}"
        exit 1
    fi
}

# 函数：获取Web服务器进程ID
get_server_pid() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p $pid > /dev/null; then
            echo $pid
            return 0
        fi
    fi
    # 尝试通过进程名查找
    local pid=$(pgrep -f "${PYTHON_CMD}.*${SERVER_MODULE}" 2>/dev/null)
    if [ -n "$pid" ]; then
        echo $pid
        return 0
    fi
    echo ""
    return 1
}

# 函数：获取工作进程ID
get_worker_pid() {
    if [ -f "$WORKER_PID_FILE" ]; then
        local pid=$(cat "$WORKER_PID_FILE")
        if ps -p $pid > /dev/null; then
            echo $pid
            return 0
        fi
    fi
    # 尝试通过进程名查找
    local pid=$(pgrep -f "${PYTHON_CMD}.*${WORKER_SCRIPT}" 2>/dev/null)
    if [ -n "$pid" ]; then
        echo $pid
        return 0
    fi
    echo ""
    return 1
}

# 函数：启动服务
start_server() {
    local server_pid=$(get_server_pid)
    if [ -n "$server_pid" ]; then
        echo -e "${YELLOW}警告: Web服务器已在运行 (PID: $server_pid)${NC}"
    else
        echo -e "${BLUE}正在启动Web服务器...${NC}"
        cd "$APP_DIR"
        nohup gunicorn -w 4 -b 0.0.0.0:8888 ${SERVER_MODULE}:app > "$LOG_FILE" 2>&1 &
        local new_pid=$!
        echo $new_pid > "$PID_FILE"
        sleep 2
        if ps -p $new_pid > /dev/null; then
            echo -e "${GREEN}Web服务器已成功启动 (PID: $new_pid)${NC}"
        else
            echo -e "${RED}启动Web服务器失败。查看日志: ${LOG_FILE}${NC}"
        fi
    fi
    
    start_worker
}

# 函数：启动工作进程
start_worker() {
    local worker_pid=$(get_worker_pid)
    if [ -n "$worker_pid" ]; then
        echo -e "${YELLOW}警告: 工作进程已在运行 (PID: $worker_pid)${NC}"
    else
        echo -e "${BLUE}正在启动工作进程...${NC}"
        cd "$APP_DIR"
        nohup $PYTHON_CMD -u "$WORKER_SCRIPT" > "$WORKER_LOG_FILE" 2>&1 &
        local new_pid=$!
        echo $new_pid > "$WORKER_PID_FILE"
        sleep 2
        if ps -p $new_pid > /dev/null; then
            echo -e "${GREEN}工作进程已成功启动 (PID: $new_pid)${NC}"
        else
            echo -e "${RED}启动工作进程失败。查看日志: ${WORKER_LOG_FILE}${NC}"
        fi
    fi
}

# 函数：停止服务
stop_server() {
    stop_worker
    
    local server_pid=$(get_server_pid)
    if [ -z "$server_pid" ]; then
        echo -e "${YELLOW}Web服务器未运行${NC}"
    else
        echo -e "${BLUE}正在停止Web服务器 (PID: $server_pid)...${NC}"
        kill -15 $server_pid
        local max_wait=10
        local waited=0
        while ps -p $server_pid > /dev/null && [ $waited -lt $max_wait ]; do
            sleep 1
            waited=$((waited + 1))
        done
        if ps -p $server_pid > /dev/null; then
            kill -9 $server_pid
        fi
        echo -e "${GREEN}Web服务器已成功停止${NC}"
        rm -f "$PID_FILE"
    fi
}

# 函数：停止工作进程
stop_worker() {
    local worker_pid=$(get_worker_pid)
    if [ -z "$worker_pid" ]; then
        echo -e "${YELLOW}工作进程未运行${NC}"
    else
        echo -e "${BLUE}正在停止工作进程 (PID: $worker_pid)...${NC}"
        kill -15 $worker_pid
        sleep 2
        if ps -p $worker_pid > /dev/null; then
            kill -9 $worker_pid
        fi
        echo -e "${GREEN}工作进程已成功停止${NC}"
        rm -f "$WORKER_PID_FILE"
    fi
}


# 函数：重启服务
restart_server() {
    echo -e "${BLUE}正在重启${APP_NAME}...${NC}"
    stop_server
    sleep 2
    start_server
}

# 函数：检查服务状态
check_status() {
    local server_pid=$(get_server_pid)
    if [ -n "$server_pid" ]; then
        local uptime=$(ps -o etime= -p $server_pid)
        local mem=$(ps -o %mem= -p $server_pid)
        local cpu=$(ps -o %cpu= -p $server_pid)

        echo -e "${GREEN}Web服务器正在运行${NC}"
        echo -e "  PID:     ${BLUE}$server_pid${NC}"
        echo -e "  运行时间: ${BLUE}$uptime${NC}"
        echo -e "  内存使用: ${BLUE}$mem%${NC}"
        echo -e "  CPU使用:  ${BLUE}$cpu%${NC}"
        echo -e "  日志文件: ${BLUE}$LOG_FILE${NC}"
    else
        echo -e "${YELLOW}Web服务器未运行${NC}"
    fi
    
    echo "" # 添加空行以分隔

    local worker_pid=$(get_worker_pid)
    if [ -n "$worker_pid" ]; then
        local uptime=$(ps -o etime= -p $worker_pid)
        local mem=$(ps -o %mem= -p $worker_pid)
        local cpu=$(ps -o %cpu= -p $worker_pid)

        echo -e "${GREEN}工作进程正在运行${NC}"
        echo -e "  PID:     ${BLUE}$worker_pid${NC}"
        echo -e "  运行时间: ${BLUE}$uptime${NC}"
        echo -e "  内存使用: ${BLUE}$mem%${NC}"
        echo -e "  CPU使用:  ${BLUE}$cpu%${NC}"
        echo -e "  日志文件: ${BLUE}$WORKER_LOG_FILE${NC}"
    else
        echo -e "${YELLOW}工作进程未运行${NC}"
    fi
}

# 函数：监控服务
monitor_server() {
    echo -e "${BLUE}开始监控${APP_NAME}...${NC}"
    echo -e "${BLUE}监控日志将写入: ${LOG_FILE}.monitor${NC}"
    echo -e "${YELLOW}按 Ctrl+C 停止监控${NC}"

    # 在后台启动监控
    (
        while true; do
            local pid=$(get_pid)
            local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

            if [ -z "$pid" ]; then
                echo "$timestamp - 服务未运行，正在重启..." >> "${LOG_FILE}.monitor"
                cd "$APP_DIR"
                gunicorn -w 4 -b 0.0.0.0:8888 ${SERVER_MODULE}:app >> "$LOG_FILE" 2>&1 &
                local new_pid=$!
                echo $new_pid > "$PID_FILE"
                echo "$timestamp - 服务已重启 (PID: $new_pid)" >> "${LOG_FILE}.monitor"
            else
                # 检查服务是否响应 (可以通过访问服务API实现)
                local is_responsive=true

                # 这里可以添加额外的健康检查逻辑
                # 例如：使用curl检查API是否响应
                # if ! curl -s http://localhost:8888/health > /dev/null; then
                #     is_responsive=false
                # fi

                if [ "$is_responsive" = false ]; then
                    echo "$timestamp - 服务无响应，正在重启..." >> "${LOG_FILE}.monitor"
                    kill -9 $pid
                    sleep 2
                    cd "$APP_DIR"
                    gunicorn -w 4 -b 0.0.0.0:8888 ${SERVER_MODULE}:app >> "$LOG_FILE" 2>&1 &
                    local new_pid=$!
                    echo $new_pid > "$PID_FILE"
                    echo "$timestamp - 服务已重启 (PID: $new_pid)" >> "${LOG_FILE}.monitor"
                fi
            fi

            sleep $MONITOR_INTERVAL
        done
    ) &

    # 保存监控进程PID
    MONITOR_PID=$!
    echo $MONITOR_PID > "${APP_DIR}/.monitor.pid"
    echo -e "${GREEN}监控进程已启动 (PID: $MONITOR_PID)${NC}"

    # 捕获Ctrl+C以停止监控
    trap 'kill $MONITOR_PID; echo -e "${YELLOW}监控已停止${NC}"; rm -f "${APP_DIR}/.monitor.pid"' INT

    # 等待监控进程
    wait $MONITOR_PID
}

# 函数：查看日志
view_logs() {
    echo "请选择要查看的日志:"
    echo "1) Web服务器日志"
    echo "2) 工作进程日志"
    read -p "输入选项 (1-2): " choice

    local log_to_view=""
    case $choice in
        1) log_to_view="$LOG_FILE" ;;
        2) log_to_view="$WORKER_LOG_FILE" ;;
        *) echo "无效选项"; return 1 ;;
    esac

    if [ ! -f "$log_to_view" ]; then
        echo -e "${YELLOW}日志文件不存在: ${log_to_view}${NC}"
        return 1
    fi

    echo -e "${BLUE}显示最新的日志内容 (按Ctrl+C退出)${NC}"
    tail -f "$log_to_view"
}

# 主函数
main() {
    check_prerequisites
    init_database # 在执行任何操作前初始化数据库

    local command=${1:-"help"}

    case $command in
        start)
            start_server
            ;;
        stop)
            stop_server
            ;;
        restart)
            restart_server
            ;;
        status)
            check_status
            ;;
        monitor)
            monitor_server
            ;;
        logs)
            view_logs
            ;;
        help)
            show_help
            ;;
        *)
            show_help
            ;;
    esac
}

# 执行主函数
main "$@"