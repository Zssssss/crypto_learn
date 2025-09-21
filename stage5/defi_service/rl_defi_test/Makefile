.PHONY: help install test fetch-data clean lint format

# 默认目标
help:
	@echo "Hyperliquid RL DeFi 数据获取和处理工具"
	@echo ""
	@echo "可用命令:"
	@echo "  install      - 安装依赖"
	@echo "  test         - 运行测试"
	@echo "  fetch-data   - 获取Hyperliquid数据"
	@echo "  clean        - 清理数据文件"
	@echo "  lint         - 代码检查"
	@echo "  format       - 代码格式化"
	@echo ""

# 安装依赖
install:
	pip install -r requirements.txt

# 运行测试
test:
	python test_hyperliquid_integration.py

# 获取数据
fetch-data:
	python scripts/fetch_hyperliquid_data.py --days 30 --symbol BTC-USD

# 获取多个交易对数据
fetch-multi:
	python scripts/fetch_hyperliquid_data.py --symbols BTC-USD ETH-USD SOL-USD --days 7

# 清理数据文件
clean:
	rm -rf data/hyperliquid/*
	rm -rf logs/*
	rm -rf models/*

# 代码检查
lint:
	python -m flake8 *.py scripts/ --max-line-length=100

# 代码格式化
format:
	python -m black *.py scripts/ --line-length=100

# 实时数据测试
test-realtime:
	python -c "import asyncio; from realtime_processor import RealtimeDataProcessor; import yaml; asyncio.run(RealtimeDataProcessor(yaml.safe_load(open('configs/config.yaml'))).start())"

# 创建必要的目录
setup-dirs:
	mkdir -p data/hyperliquid
	mkdir -p logs
	mkdir -p models
	mkdir -p data/realtime

# 运行所有检查
check: lint test

# 开发环境设置
dev-setup: setup-dirs install
	@echo "开发环境设置完成！"

# 快速测试
quick-test:
	python -c "import asyncio; from hyperliquid_data_provider import HyperliquidDataProvider, HyperliquidConfig; async def test(): p = HyperliquidDataProvider(HyperliquidConfig()); print(await p.get_market_info()); await p.close(); asyncio.run(test())"