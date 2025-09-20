#!/bin/bash
# 空投狩猎启动脚本

set -e

echo "🪂 Airdrop Hunter Agent 启动器"
echo "================================"

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装 Python3"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python 版本: $PYTHON_VERSION"

# 检查并安装依赖
echo "📦 检查依赖..."
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate

# 升级pip
echo "升级 pip..."
pip install --upgrade pip

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 检查配置文件
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件，创建示例配置..."
    cp .env.example .env
    echo "请编辑 .env 文件配置你的钱包和API密钥"
    exit 1
fi

# 创建必要的目录
mkdir -p logs
mkdir -p data
mkdir -p chrome_data

# 检查ChromeDriver
if ! command -v chromedriver &> /dev/null && [ ! -f "./chromedriver" ]; then
    echo "⚠️  未找到 ChromeDriver"
    echo "请安装 ChromeDriver 或将其放在当前目录"
    echo "下载地址: https://chromedriver.chromium.org/"
fi

# 启动程序
echo "🚀 启动空投狩猎..."
python3 main.py "$@"