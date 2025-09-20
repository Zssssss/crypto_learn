# Hyperliquid永续合约RL交易代理

这是一个基于强化学习的永续合约交易代理项目，专为Hyperliquid交易所设计。项目支持历史回测、实时交易和多种RL算法训练。

## 🚀 功能特性

- **多算法支持**: DQN和PPO算法
- **实时数据**: 通过WebSocket连接Hyperliquid API
- **技术指标**: 内置多种技术指标计算
- **风险管理**: 支持杠杆、保证金和风险控制
- **回测系统**: 完整的历史回测框架
- **实时交易**: 支持实时交易执行
- **可视化**: 交易结果和性能指标可视化

## 📁 项目结构

```
rl_defi_test/
├── README.md                    # 项目说明文档
├── requirements.txt            # Python依赖
├── Dockerfile                  # Docker容器配置
├── configs/
│   └── config.yaml            # 配置文件
├── data/
│   └── sample_data.csv        # 示例数据
├── env/
│   ├── __init__.py
│   └── trading_env.py         # 交易环境
├── models/                    # 模型保存目录
├── scripts/
│   ├── run_backtest.sh        # 回测运行脚本
│   └── run_realtime.py        # 实时交易脚本
├── logs/                      # 日志目录
├── data_loader.py             # 数据加载器
├── realtime_adapter.py        # 实时数据适配器
├── utils.py                   # 工具函数
├── train_dqn.py               # DQN训练脚本
└── train_ppo.py               # PPO训练脚本
```

## 🛠️ 安装

### 环境要求
- Python 3.8+
- pip包管理器
- Docker（可选）

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd rl_defi_test
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **使用Docker**
```bash
docker build -t hyperliquid-rl-trader .
docker run -it hyperliquid-rl-trader
```

## ⚙️ 配置

编辑 `configs/config.yaml` 文件来配置项目参数：

```yaml
# 数据配置
data:
  csv_path: data/sample_data.csv
  symbol: "BTC-USD"

# 环境参数
env:
  window_size: 50              # 观察窗口大小
  fee_rate: 0.0005            # 交易手续费率
  leverage: 10                # 杠杆倍数
  max_position_size: 1.0      # 最大仓位

# 训练参数
training:
  total_timesteps: 200000     # 总训练步数
  algo: dqn                   # 算法选择: dqn或ppo
  learning_rate: 0.0003       # 学习率
  batch_size: 256             # 批次大小

# 账户配置
account:
  initial_balance: 1000.0     # 初始资金
  max_drawdown: 0.1          # 最大回撤限制

# 实时交易配置
realtime:
  websocket_url: "wss://api.hyperliquid.xyz/ws"
  symbol: "BTC-USD"
```

## 🎯 快速开始

### 1. 数据准备

项目包含示例数据，也可以获取真实数据：

```bash
# 运行数据加载测试
python data_loader.py
```

### 2. 训练模型

#### 训练DQN模型
```bash
python train_dqn.py
```

#### 训练PPO模型
```bash
python train_ppo.py
```

#### 使用脚本运行回测
```bash
chmod +x scripts/run_backtest.sh
./scripts/run_backtest.sh
```

### 3. 实时交易

使用训练好的模型进行实时交易：

```bash
python scripts/run_realtime.py --model models/dqn_perp_final --model-type dqn
```

## 📊 性能评估

训练完成后，系统会自动生成以下报告：

- **交易记录**: `backtest_results_*.csv`
- **模型检查点**: `models/checkpoints/`
- **最佳模型**: `models/best_model/`
- **TensorBoard日志**: `models/tensorboard/`

### 查看TensorBoard
```bash
tensorboard --logdir=models/tensorboard
```

## 🔧 高级用法

### 自定义环境
可以通过继承 `TradingEnv` 类来创建自定义交易环境：

```python
from env.trading_env import TradingEnv

class MyTradingEnv(TradingEnv):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 自定义初始化
```

### 添加新指标
在 `utils.py` 中添加新的技术指标：

```python
def add_custom_indicators(df):
    df['custom_metric'] = your_calculation(df)
    return df
```

### 多资产交易
支持同时交易多个资产：

```python
# 修改配置
symbols = ["BTC-USD", "ETH-USD", "SOL-USD"]
for symbol in symbols:
    # 训练独立模型
    pass
```


## 📈 性能指标

项目提供以下性能评估指标：

- **夏普比率 (Sharpe Ratio)**: 风险调整收益
- **最大回撤 (Max Drawdown)**: 最大资金回撤
- **胜率 (Win Rate)**: 盈利交易比例
- **盈利因子 (Profit Factor)**: 总盈利/总亏损
- **年化收益率**: 年化投资回报


### 开发计划
- [ ] 添加更多RL算法（A3C, SAC, TD3）
- [ ] 添加订单簿数据支持
- [ ] 实现分布式训练
- [ ] 支持多时间框架