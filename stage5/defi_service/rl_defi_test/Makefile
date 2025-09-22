# 🚀 RL DeFi 项目 Makefile

.PHONY: help install test clean setup data train all

# 默认目标
.DEFAULT_GOAL := help

# 变量
PYTHON := python3
PIP := pip3

## 📋 帮助信息
help:
	@echo "🎯 RL DeFi 项目 - 可用命令"
	@echo ""
	@echo "📦 安装和设置:"
	@echo "  make setup     - 一键设置环境"
	@echo "  make install   - 安装依赖"
	@echo ""
	@echo "🧪 测试:"
	@echo "  make test      - 运行所有测试"
	@echo "  make quick     - 快速测试"
	@echo ""
	@echo "📊 数据:"
	@echo "  make data      - 获取示例数据"
	@echo "  make clean     - 清理数据"
	@echo ""
	@echo "🤖 训练:"
	@echo "  make train     - 训练DQN模型"
	@echo "  make train-ppo - 训练PPO模型"
	@echo ""
	@echo "🔧 开发:"
	@echo "  make format    - 格式化代码"
	@echo "  make lint      - 代码检查"

## 📦 环境设置
setup:
	@echo "🔧 设置项目环境..."
	@mkdir -p data logs models
	@$(PIP) install -r requirements.txt
	@echo "✅ 环境设置完成"

install:
	@echo "📦 安装依赖..."
	@$(PIP) install -r requirements.txt
	@echo "✅ 依赖安装完成"

## 🧪 测试
test:
	@echo "🧪 运行完整测试..."
	@$(PYTHON) run_test.py

quick:
	@echo "⚡ 运行快速测试..."
	@$(PYTHON) test_fixed.py

## 📊 数据管理
data:
	@echo "📊 获取示例数据..."
	@$(PYTHON) -c "from data_loader import create_sample_data; create_sample_data('data/sample_data.csv', 1000)"
	@echo "✅ 示例数据创建完成"

clean:
	@echo "🧹 清理数据..."
	@rm -rf data/*.csv data/*.npz logs/*
	@echo "✅ 清理完成"

## 🤖 训练
train:
	@echo "🤖 开始DQN训练..."
	@$(PYTHON) train_dqn.py

train-ppo:
	@echo "🤖 开始PPO训练..."
	@$(PYTHON) train_ppo.py

## 🔧 开发工具
format:
	@echo "🎨 格式化代码..."
	@black *.py scripts/*.py

lint:
	@echo "🔍 代码检查..."
	@flake8 *.py scripts/*.py --max-line-length=100

## 🚀 一键运行
all: setup test data
	@echo "🎉 项目准备完成！"
	@echo "下一步："
	@echo "1. 运行 'make train' 开始训练"
	@echo "2. 查看 'README.md' 获取完整文档"