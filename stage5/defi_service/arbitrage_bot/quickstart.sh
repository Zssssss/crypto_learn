#!/bin/bash

# DeFi 套利机器人快速启动脚本
# 使用方法: ./quickstart.sh

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示欢迎信息
clear
echo "=============================================="
echo "     🚀 DeFi 套利机器人快速启动脚本"
echo "=============================================="
echo ""

# 检查系统要求
print_info "检查系统要求..."

# 检查 Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 未安装！请先安装 Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
print_success "Python 版本: $PYTHON_VERSION"

# 检查 Node.js
if ! command -v node &> /dev/null; then
    print_error "Node.js 未安装！请先安装 Node.js 16+"
    exit 1
fi

NODE_VERSION=$(node --version)
print_success "Node.js 版本: $NODE_VERSION"

# 检查 npm
if ! command -v npm &> /dev/null; then
    print_error "npm 未安装！"
    exit 1
fi

NPM_VERSION=$(npm --version)
print_success "npm 版本: $NPM_VERSION"

echo ""

# 安装依赖
print_info "安装 Python 依赖..."
pip3 install -r requirements.txt --quiet
print_success "Python 依赖安装完成"

print_info "安装 Node.js 依赖..."
cd arb-executor
npm install --silent
cd ..
print_success "Node.js 依赖安装完成"

echo ""

# 配置环境变量
if [ ! -f .env ]; then
    print_warning ".env 文件不存在，从模板创建..."
    cp .env.example .env
    print_success ".env 文件已创建"
    
    echo ""
    print_warning "请编辑 .env 文件并配置以下重要参数："
    echo "  1. ACCOUNT - 你的钱包地址"
    echo "  2. PRIVATE_KEY - 你的私钥（请妥善保管）"
    echo "  3. RPC_URL - RPC 节点 URL"
    echo "  4. AMOUNT_USDT - 每次套利金额"
    echo "  5. MIN_NET_PROFIT_USDT - 最小净利润要求"
    echo ""
    
    read -p "是否现在编辑 .env 文件？(y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v nano &> /dev/null; then
            nano .env
        elif command -v vim &> /dev/null; then
            vim .env
        else
            print_warning "请手动编辑 .env 文件"
        fi
    fi
else
    print_success ".env 文件已存在"
fi

echo ""

# 创建必要的目录
print_info "创建必要的目录..."
mkdir -p logs
mkdir -p backups
mkdir -p arb-executor/deployments
print_success "目录创建完成"

echo ""

# 选择运行模式
echo "请选择操作："
echo "  1) 部署智能合约到 Arbitrum 主网"
echo "  2) 部署智能合约到测试网"
echo "  3) 运行套利机器人（基础版）"
echo "  4) 运行套利机器人（高级版）"
echo "  5) 运行测试"
echo "  6) 查看使用说明"
echo "  0) 退出"
echo ""

read -p "请输入选项 (0-6): " choice

case $choice in
    1)
        print_info "部署到 Arbitrum 主网..."
        cd arb-executor
        npx hardhat compile
        npx hardhat run scripts/deploy.js --network arbitrum
        cd ..
        print_success "部署完成！"
        ;;
    2)
        print_info "部署到测试网..."
        cd arb-executor
        npx hardhat compile
        npx hardhat run scripts/deploy.js --network arbitrumGoerli
        cd ..
        print_success "部署完成！"
        ;;
    3)
        print_info "启动基础版套利机器人..."
        echo ""
        print_warning "按 Ctrl+C 停止机器人"
        echo ""
        python3 arbitrage_bot.py
        ;;
    4)
        print_info "启动高级版套利机器人..."
        echo ""
        print_warning "按 Ctrl+C 停止机器人"
        echo ""
        python3 arbitrage_bot_v2.py
        ;;
    5)
        print_info "运行测试..."
        python3 -m pytest tests/ -v
        print_success "测试完成！"
        ;;
    6)
        echo ""
        echo "=============================================="
        echo "                使用说明"
        echo "=============================================="
        echo ""
        echo "1. 配置："
        echo "   - 编辑 .env 文件，填入你的私钥和其他参数"
        echo "   - 确保账户有足够的 ETH 用于 Gas 费"
        echo ""
        echo "2. 部署合约："
        echo "   - 运行此脚本选择选项 1 或 2"
        echo "   - 部署成功后会自动更新 .env 中的合约地址"
        echo ""
        echo "3. 运行机器人："
        echo "   - 基础版：适合初学者，功能简单"
        echo "   - 高级版：支持多 DEX、闪电贷、性能监控等"
        echo ""
        echo "4. 监控："
        echo "   - 日志文件位于 logs/ 目录"
        echo "   - 使用 'tail -f logs/arbitrage.log' 查看实时日志"
        echo ""
        echo "5. 安全提示："
        echo "   - 永远不要分享你的私钥"
        echo "   - 先在测试网测试"
        echo "   - 设置合理的 Gas 价格上限"
        echo ""
        echo "更多信息请查看 README.md"
        echo ""
        ;;
    0)
        print_info "退出..."
        exit 0
        ;;
    *)
        print_error "无效的选项！"
        exit 1
        ;;
esac

echo ""
print_success "操作完成！"
echo ""

# 显示下一步建议
if [ "$choice" -eq 1 ] || [ "$choice" -eq 2 ]; then
    echo "下一步："
    echo "  1. 确保 .env 文件中的 EXECUTOR 地址已更新"
    echo "  2. 运行 './quickstart.sh' 并选择选项 3 或 4 启动机器人"
fi

echo ""
echo "=============================================="
echo "     感谢使用 DeFi 套利机器人！"
echo "     祝您套利成功！💰"
echo "=============================================="