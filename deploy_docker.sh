#!/bin/bash

# 期权交易策略系统 - Docker部署脚本
# 用途: 一键部署到生产服务器

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查必要的命令
check_requirements() {
    log_info "检查系统依赖..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装,请先安装Docker"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose未安装,请先安装Docker Compose"
        exit 1
    fi

    log_info "系统依赖检查通过!"
}

# 检查环境变量文件
check_env_file() {
    log_info "检查环境变量配置..."

    if [ ! -f .env ]; then
        log_warn ".env文件不存在,从.env.example创建..."
        cp .env.example .env
        log_warn "请编辑.env文件,填入必要的配置信息"
        exit 1
    fi

    log_info "环境变量配置检查通过!"
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    mkdir -p data logs ssl
    log_info "目录创建完成!"
}

# 构建Docker镜像
build_image() {
    log_info "构建Docker镜像..."
    docker-compose build --no-cache
    log_info "镜像构建完成!"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    docker-compose up -d
    log_info "服务启动完成!"
}

# 查看服务状态
check_status() {
    log_info "检查服务状态..."
    sleep 5
    docker-compose ps

    log_info "检查健康状态..."
    sleep 10
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_info "✓ 服务健康检查通过!"
    else
        log_warn "服务可能未正常启动,请检查日志"
    fi
}

# 显示访问信息
show_access_info() {
    echo ""
    log_info "============================================"
    log_info "期权交易策略系统部署完成!"
    log_info "============================================"
    echo ""
    log_info "访问地址:"
    log_info "  - API文档: http://localhost:8000/docs"
    log_info "  - 前端界面: http://localhost:8000/frontend"
    log_info "  - 健康检查: http://localhost:8000/health"
    echo ""
    log_info "常用命令:"
    log_info "  - 查看日志: docker-compose logs -f"
    log_info "  - 停止服务: docker-compose down"
    log_info "  - 重启服务: docker-compose restart"
    log_info "  - 查看状态: docker-compose ps"
    echo ""
    log_info "如需外网访问,请配置:"
    log_info "  1. 防火墙开放端口 80/443"
    log_info "  2. 配置域名解析"
    log_info "  3. 配置SSL证书(可选)"
    echo ""
}

# 主函数
main() {
    log_info "开始部署期权交易策略系统..."

    check_requirements
    check_env_file
    create_directories
    build_image
    start_services
    check_status
    show_access_info

    log_info "部署完成!"
}

# 执行主函数
main
