# Makefile for DeFi Arbitrage Bot
# 使用方法: make [target]

.PHONY: help install test deploy run clean docker-build docker-run all

# 默认目标
help:
	@echo "📚 DeFi 套利机器人 - 可用命令:"
	@echo ""
	@echo "  make install      - 安装所有依赖"
	@echo "  make test         - 运行测试"
	@echo "  make deploy       - 部署智能合约"
	@echo "  make run          - 运行套利机器人"
	@echo "  make run-v2       - 运行高级版套利机器人"
	@echo "  make clean        - 清理临时文件"
	@echo "  make docker-build - 构建 Docker 镜像"
	@echo "  make docker-run   - 在 Docker 中运行"
	@echo "  make all          - 完整安装和部署"
	@echo ""

# 安装依赖
install:
	@echo "📦 安装 Python 依赖..."
	pip install -r requirements.txt
	@echo ""
	@echo "📦 安装 Node.js 依赖..."
	cd arb-executor && npm install
	@echo "✅ 依赖安装完成！"

# 运行测试
test:
	@echo "🧪 运行 Python 单元测试..."
	python -m pytest tests/ -v --tb=short
	@echo ""
	@echo "🧪 运行 Solidity 测试..."
	cd arb-executor && npx hardhat test
	@echo "✅ 所有测试通过！"

# 编译合约
compile:
	@echo "🔨 编译智能合约..."
	cd arb-executor && npx hardhat compile
	@echo "✅ 合约编译完成！"

# 部署合约
deploy: compile
	@echo "🚀 部署智能合约..."
	cd arb-executor && npx hardhat run scripts/deploy.js --network arbitrum
	@echo "✅ 合约部署完成！"

# 部署到测试网
deploy-test: compile
	@echo "🚀 部署到测试网..."
	cd arb-executor && npx hardhat run scripts/deploy.js --network arbitrumGoerli
	@echo "✅ 测试网部署完成！"

# 运行基础版机器人
run:
	@echo "🤖 启动套利机器人（基础版）..."
	@if [ ! -f .env ]; then \
		echo "⚠️  未找到 .env 文件，从模板创建..."; \
		cp .env.example .env; \
		echo "📝 请编辑 .env 文件配置你的私钥和其他参数"; \
		exit 1; \
	fi
	python arbitrage_bot.py

# 运行高级版机器人
run-v2:
	@echo "🤖 启动套利机器人（高级版）..."
	@if [ ! -f .env ]; then \
		echo "⚠️  未找到 .env 文件，从模板创建..."; \
		cp .env.example .env; \
		echo "📝 请编辑 .env 文件配置你的私钥和其他参数"; \
		exit 1; \
	fi
	python arbitrage_bot_v2.py

# 检查配置
check-config:
	@echo "🔍 检查配置..."
	@if [ ! -f .env ]; then \
		echo "❌ .env 文件不存在"; \
		echo "运行 'cp .env.example .env' 并编辑配置"; \
		exit 1; \
	else \
		echo "✅ .env 文件存在"; \
	fi
	@echo "📋 当前配置:"
	@grep -E "^(RPC_URL|ACCOUNT|AMOUNT_USDT|MIN_NET_PROFIT_USDT)" .env | sed 's/PRIVATE_KEY=.*/PRIVATE_KEY=***/'

# 创建日志目录
setup-logs:
	@mkdir -p logs
	@echo "📁 日志目录已创建: ./logs/"

# 查看日志
logs:
	@if [ -f logs/arbitrage.log ]; then \
		tail -f logs/arbitrage.log; \
	else \
		echo "⚠️  日志文件不存在"; \
	fi

# 清理
clean:
	@echo "🧹 清理临时文件..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	rm -rf .pytest_cache 2>/dev/null || true
	cd arb-executor && npx hardhat clean 2>/dev/null || true
	@echo "✅ 清理完成！"

# Docker 构建
docker-build:
	@echo "🐳 构建 Docker 镜像..."
	docker build -t defi-arbitrage-bot:latest .
	@echo "✅ Docker 镜像构建完成！"

# Docker 运行
docker-run:
	@echo "🐳 在 Docker 中运行..."
	docker run -it --rm \
		--env-file .env \
		-v $(PWD)/logs:/app/logs \
		defi-arbitrage-bot:latest

# 完整安装和部署
all: install test deploy setup-logs
	@echo ""
	@echo "🎉 完整安装和部署完成！"
	@echo ""
	@echo "下一步:"
	@echo "  1. 编辑 .env 文件配置你的私钥"
	@echo "  2. 运行 'make run-v2' 启动套利机器人"
	@echo ""

# 开发模式（监视文件变化）
dev:
	@echo "👨‍💻 开发模式..."
	@echo "监视文件变化并自动重启..."
	@while true; do \
		python arbitrage_bot_v2.py; \
		echo "⚠️  机器人停止，5秒后重启..."; \
		sleep 5; \
	done

# 性能分析
profile:
	@echo "📊 运行性能分析..."
	python -m cProfile -o profile.stats arbitrage_bot_v2.py
	python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"

# 代码格式化
format:
	@echo "🎨 格式化代码..."
	black *.py tests/*.py
	@echo "✅ 代码格式化完成！"

# 代码检查
lint:
	@echo "🔍 检查代码质量..."
	flake8 *.py tests/*.py --max-line-length=120
	mypy *.py --ignore-missing-imports
	@echo "✅ 代码检查通过！"

# 生成文档
docs:
	@echo "📚 生成文档..."
	python -m pydoc -w arbitrage_bot_v2
	@echo "✅ 文档已生成！"

# 统计代码行数
stats:
	@echo "📊 代码统计:"
	@echo ""
	@echo "Python 代码:"
	@find . -name "*.py" -type f | xargs wc -l | tail -1
	@echo ""
	@echo "Solidity 代码:"
	@find . -name "*.sol" -type f | xargs wc -l | tail -1
	@echo ""
	@echo "总计:"
	@find . \( -name "*.py" -o -name "*.sol" -o -name "*.js" \) -type f | xargs wc -l | tail -1

# 备份配置
backup:
	@echo "💾 备份配置和日志..."
	@mkdir -p backups
	@tar -czf backups/backup-$(shell date +%Y%m%d-%H%M%S).tar.gz \
		.env logs/ arb-executor/deployments/ 2>/dev/null || true
	@echo "✅ 备份完成！"

# 更新依赖
update:
	@echo "🔄 更新依赖..."
	pip install --upgrade -r requirements.txt
	cd arb-executor && npm update
	@echo "✅ 依赖更新完成！"

# 安全检查
security:
	@echo "🔒 安全检查..."
	@echo "检查 Python 依赖..."
	pip-audit || true
	@echo ""
	@echo "检查 Node.js 依赖..."
	cd arb-executor && npm audit || true
	@echo "✅ 安全检查完成！"