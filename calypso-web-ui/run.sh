#!/usr/bin/env bash
# ==============================================================================
# Calypso AI Chinese Web UI - Helper Management Script
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

IMAGE_NAME="calypso-web-ui:latest"
CONTAINER_NAME="calypso-ui"
PORT="${PORT:-8080}"

print_usage() {
    echo "================================================================="
    echo "  Calypso AI 中文安全运营与体验控制台 - 管理脚本"
    echo "================================================================="
    echo "用法: ./run.sh <命令>"
    echo ""
    echo "可用命令:"
    echo "  local          本地启动服务 (自动构建前端并以热重载模式运行 Uvicorn)"
    echo "  docker-build   构建生产级 Docker 多阶段镜像 ($IMAGE_NAME)"
    echo "  docker-run     在后台启动 Docker 容器 ($CONTAINER_NAME, 映射端口 $PORT)"
    echo "  docker-stop    停止并清理运行中的 Docker 容器 ($CONTAINER_NAME)"
    echo "  test           运行后端单元与集成自动化测试 (pytest)"
    echo "  help           查看本帮助说明"
    echo "================================================================="
}

case "$1" in
    local)
        echo ">>> [Local] 准备本地运行环境..."
        if [ ! -d "app/static" ] || [ ! -f "app/static/index.html" ]; then
            echo ">>> [Local] 检测到 app/static 为空，正在编译前端项目 (web)..."
            (cd web && npm run build)
            rm -rf app/static
            cp -r web/dist app/static
            echo ">>> [Local] 前端静态资源编译并同步完成。"
        fi
        echo ">>> [Local] 启动 FastAPI / Uvicorn 服务 (端口: $PORT)..."
        echo ">>> 访问地址: http://localhost:$PORT"
        PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --reload
        ;;

    docker-build)
        echo ">>> [Docker] 开始构建 Docker 多阶段镜像: $IMAGE_NAME..."
        docker build -t "$IMAGE_NAME" .
        echo ">>> [Docker] 镜像构建成功: $IMAGE_NAME"
        ;;

    docker-run)
        echo ">>> [Docker] 准备启动容器: $CONTAINER_NAME..."
        if [ "$(docker ps -aq -f name=^/${CONTAINER_NAME}$)" ]; then
            echo ">>> [Docker] 检测到已存在同名容器，正在停止并移除旧容器..."
            docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
            docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
        fi

        ENV_ARGS=()
        if [ -f ".env" ]; then
            echo ">>> [Docker] 检测到 .env 文件，已加载环境变量。"
            ENV_ARGS+=(--env-file .env)
        fi

        docker run -d \
            --name "$CONTAINER_NAME" \
            -p "${PORT}:8080" \
            "${ENV_ARGS[@]}" \
            "$IMAGE_NAME"

        echo ">>> [Docker] 容器启动成功！"
        echo ">>> 容器名称: $CONTAINER_NAME"
        echo ">>> 访问地址: http://localhost:${PORT}"
        echo ">>> 查看日志: docker logs -f $CONTAINER_NAME"
        ;;

    docker-stop)
        echo ">>> [Docker] 正在停止容器: $CONTAINER_NAME..."
        docker stop "$CONTAINER_NAME" 2>/dev/null || echo ">>> 容器未在运行。"
        echo ">>> [Docker] 正在移除容器: $CONTAINER_NAME..."
        docker rm "$CONTAINER_NAME" 2>/dev/null || echo ">>> 容器已清理。"
        echo ">>> [Docker] 完成。"
        ;;

    test)
        echo ">>> [Test] 正在执行自动化测试套件 (pytest)..."
        PYTHONPATH=. pytest tests/ -v
        echo ">>> [Test] 测试执行完毕。"
        ;;

    help|--help|-h)
        print_usage
        ;;

    *)
        print_usage
        exit 1
        ;;
esac
