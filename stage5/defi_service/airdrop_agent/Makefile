.PHONY: help install start stop status clean test lint format

# 默认目标
help:
	@echo "🪂 Airdrop Hunter Agent - Makefile"
	@echo ""
	@echo "使用方法:"
	@echo "  make install     - 安装依赖"
	@echo "  make start       - 启动空投狩猎"
	@echo "  make status      - 查看状态"
	@echo "  make stop        - 停止运行"
	@echo "  make clean       - 清理缓存"
	@echo "  make test        - 运行测试"
	@echo "  make lint        - 代码检查"
	@echo "  make format      - 代码格式化"

# 安装依赖
install:
	@echo "📦 安装依赖..."
	@python3 -m pip install --upgrade pip
	@pip install -r requirements.txt
	@echo "✅ 依赖安装完成"

# 启动程序
start:
	@echo "🚀 启动空投狩猎..."
	@./start.sh

# 查看状态
status:
	@echo "📊 查看当前状态..."
	@python3 main.py status

# 停止程序
stop:
	@echo "🛑 停止程序..."
	@pkill -f "main.py"

# 清理缓存
clean:
	@echo "🧹 清理缓存..."
	@rm -rf __pycache__/
	@rm -rf *.pyc
	@rm -rf logs/*.log
	@rm -rf data/*.json
	@echo "✅ 清理完成"

# 运行测试
test:
	@echo "🧪 运行测试..."
	@python3 -m pytest tests/ -v

# 代码检查
lint:
	@echo "🔍 代码检查..."
	@flake8 *.py utils/
	@echo "✅ 代码检查通过"

# 代码格式化
format:
	@echo "✨ 代码格式化..."
	@black *.py utils/
	@isort *.py utils/
	@echo "✅ 格式化完成"

# 创建虚拟环境
venv:
	@echo "🐍 创建虚拟环境..."
	@python3 -m venv venv
	@echo "✅ 虚拟环境创建完成"
	@echo "激活虚拟环境: source venv/bin/activate"

# 开发环境设置
dev: venv install
	@echo "🔧 开发环境设置完成"
	@echo "激活虚拟环境: source venv/bin/activate"

# 生产环境部署
prod:
	@echo "🏭 生产环境部署..."
	@cp .env.example .env
	@echo "请编辑 .env 文件配置生产环境参数"