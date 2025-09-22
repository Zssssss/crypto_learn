# RL DeFi 测试项目

## 项目概述
这是一个基于强化学习的DeFi交易策略测试项目，专注于Hyperliquid链上数据的获取、处理和训练。项目提供了完整的数据管道，从原始数据获取到模型训练的全流程支持。

## 🏗️ 项目架构

```
rl_defi_test/
├── 📁 data/                    # 数据目录
│   ├── sample_data.csv        # 示例数据
│   └── hyperliquid/           # Hyperliquid原始数据
├── 📁 configs/                # 配置文件
│   └── config.yaml            # 主配置文件
├── 📁 scripts/                # 执行脚本
│   ├── fetch_hyperliquid_data.py  # 数据获取脚本
│   └── run_backtest.sh        # 回测脚本
├── 📁 models/                 # 模型保存目录
├── 📁 logs/                   # 日志目录
├── 📄 requirements.txt        # 项目依赖
├── 📄 Makefile               # 构建命令
└── 🔧 核心模块
    ├── hyperliquid_data_provider.py  # 数据提供器
    ├── data_formatter.py          # 数据格式化
    ├── data_validator.py          # 数据验证
    ├── realtime_processor.py      # 实时处理
    ├── data_loader.py             # 数据加载
    └── utils.py                   # 工具函数
```

## 🚀 快速开始

### 1. 环境准备
```bash
# 克隆项目
cd stage5/defi_service/rl_defi_test

# 安装依赖
pip install -r requirements.txt

# 创建必要目录
mkdir -p data logs models
```

### 2. 运行测试
```bash
# 运行完整测试
python run_test.py

# 运行组件测试
python test_fixed.py

# 运行简化测试
python test_simple.py
```

### 3. 获取数据
```bash
# 获取单个交易对数据
python scripts/fetch_hyperliquid_data.py --symbol BTC-USD --days 30

# 获取多个交易对数据
python scripts/fetch_hyperliquid_data.py --symbols BTC-USD ETH-USD --days 7

# 查看帮助
python scripts/fetch_hyperliquid_data.py --help
```

### 4. 训练模型
```bash
# 使用DQN训练
python train_dqn.py

# 使用PPO训练
python train_ppo.py
```

## 📊 数据流程

### 数据获取 → 验证 → 清理 → 格式化 → 训练

1. **数据获取** (`hyperliquid_data_provider.py`)
   - 从Hyperliquid API获取实时/历史数据
   - 支持多种时间间隔和交易对

2. **数据验证** (`data_validator.py`)
   - 验证数据完整性和质量
   - 检测异常值和缺失值
   - 生成数据健康报告

3. **数据清理** (`data_validator.py`)
   - 修复价格关系错误
   - 处理缺失值和异常值
   - 标准化数据格式

4. **数据格式化** (`data_formatter.py`)
   - 创建技术指标
   - 生成训练特征
   - 分割训练/验证/测试集

5. **模型训练** (`train_dqn.py`, `train_ppo.py`)
   - 使用强化学习算法训练
   - 支持DQN和PPO算法

## 🔧 核心模块说明

### 1. 数据提供器 (`hyperliquid_data_provider.py`)
- **功能**: 连接Hyperliquid API获取数据
- **方法**:
  - `fetch_historical_data()`: 获取历史数据
  - `fetch_realtime_data()`: 获取实时数据
  - `process_raw_data()`: 处理原始数据

### 2. 数据验证器 (`data_validator.py`)
- **功能**: 验证数据质量和完整性
- **验证项**:
  - 必需列检查
  - 数据类型验证
  - 价格关系验证
  - 异常值检测
  - 时间序列完整性

### 3. 数据格式化器 (`data_formatter.py`)
- **功能**: 将原始数据转换为训练格式
- **功能**:
  - 添加技术指标（MA, RSI, MACD等）
  - 创建特征向量
  - 生成训练标签
  - 数据标准化

### 4. 数据加载器 (`data_loader.py`)
- **功能**: 加载和预处理CSV数据
- **功能**:
  - CSV文件读取
  - 数据验证
  - 数据分割
  - 示例数据生成

### 5. 工具函数 (`utils.py`)
- **功能**: 提供通用工具函数
- **包含**:
  - 技术指标计算
  - 特征创建
  - 数据标准化
  - 收益计算

## ⚙️ 配置文件 (`configs/config.yaml`)

```yaml
# 实时配置
realtime:
  symbol: "BTC-USD"
  interval: "1m"

# 环境配置
env:
  window_size: 10
  action_space: 3  # 买入、卖出、持有

# 数据配置
data:
  interval: "1m"
  lookback_days: 30

# 训练配置
training:
  batch_size: 32
  learning_rate: 0.001
  episodes: 1000
```

## 🧪 测试说明

### 测试文件
- `test_fixed.py`: 修复后的集成测试
- `test_simple.py`: 简化版功能测试
- `run_test.py`: 一键测试脚本

### 测试内容
- ✅ 数据加载测试
- ✅ 数据格式化测试
- ✅ 数据验证测试
- ✅ 工具函数测试
- ✅ 端到端流程测试

## 📈 技术指标

项目自动计算以下技术指标：
- **移动平均线**: MA5, MA10, MA20, MA50
- **指数移动平均**: EMA12, EMA26
- **MACD**: MACD线、信号线、柱状图
- **RSI**: 相对强弱指标
- **布林带**: 上轨、中轨、下轨
- **ATR**: 平均真实波幅
- **随机指标**: K值、D值
- **Williams %R**: 威廉指标

## 🎯 使用场景

### 场景1：快速测试
```bash
python run_test.py
```

### 场景2：获取训练数据
```bash
python scripts/fetch_hyperliquid_data.py --symbol BTC-USD --days 30
```

### 场景3：使用本地数据
```python
from data_loader import load_csv, prepare_data
df = load_csv('data/my_data.csv')
df = prepare_data(df)
```

### 场景4：自定义训练
```python
from data_formatter import DataFormatter
formatter = DataFormatter(config)
X_train, X_val, X_test, y_train, y_val, y_test = formatter.prepare_training_dataset(df)
```

## 🔍 故障排除

### 常见问题
1. **ImportError**: 确保已安装所有依赖 `pip install -r requirements.txt`
2. **数据为空**: 检查网络连接和API可用性
3. **语法错误**: 所有语法错误已修复，如遇新问题请检查Python版本

### 调试工具
```bash
# 查看详细日志
python scripts/fetch_hyperliquid_data.py --log-level DEBUG

# 验证数据质量
python -c "from data_validator import DataQualityValidator; print('验证器正常')"
```

## 📞 支持
项目已完全修复和整理，可以直接使用。如有问题请参考测试文件或查看日志。