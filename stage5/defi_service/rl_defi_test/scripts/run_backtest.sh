#!/bin/bash

# 永续合约RL交易回测运行脚本

set -e

echo "=== Hyperliquid Perpetual RL Trading Bot ==="
echo "Starting backtest training..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# 检查依赖
if [ ! -f "requirements.txt" ]; then
    echo "Error: requirements.txt not found"
    exit 1
fi

# 安装依赖
echo "Installing dependencies..."
pip install -r requirements.txt

# 创建必要的目录
echo "Creating directories..."
mkdir -p models/checkpoints
mkdir -p models/logs
mkdir -p models/best_model
mkdir -p logs
mkdir -p data

# 检查配置文件
if [ ! -f "configs/config.yaml" ]; then
    echo "Error: config.yaml not found"
    exit 1
fi

# 检查数据文件
if [ ! -f "data/sample_data.csv" ]; then
    echo "Generating sample data..."
    python3 -c "
from data_loader import create_sample_data
import pandas as pd
df = create_sample_data()
df.to_csv('data/sample_data.csv', index=False)
print(f'Generated {len(df)} rows of sample data')
"
fi

# 运行DQN训练
echo "Starting DQN training..."
python3 train_dqn.py

# 运行PPO训练（可选）
read -p "Do you want to run PPO training as well? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting PPO training..."
    python3 train_ppo.py
fi

echo "Training completed!"
echo "Check models/ directory for trained models"
echo "Check backtest_results_*.csv for detailed trading records"