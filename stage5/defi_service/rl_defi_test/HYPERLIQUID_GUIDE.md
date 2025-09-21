# Hyperliquid数据获取和处理指南

本文档描述了如何从Hyperliquid链上获取数据并处理成强化学习训练所需的格式。

## 概述

本项目提供了完整的Hyperliquid数据获取和处理解决方案，包括：
- 历史数据获取
- 实时数据流处理
- 数据验证和质量检查
- 特征工程
- 训练数据格式化

## 架构组件

### 1. HyperliquidDataProvider
主要的数据提供器，负责从Hyperliquid API获取数据。

### 2. DataFormatter
数据格式转换器，将原始数据转换为训练格式。

### 3. RealtimeDataProcessor
实时数据处理器，处理WebSocket数据流。

### 4. DataValidator
数据验证器，确保数据质量。

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 获取历史数据

```bash
# 获取30天的BTC-USD数据
python scripts/fetch_hyperliquid_data.py --days 30 --symbol BTC-USD

# 获取多个交易对的数据
python scripts/fetch_hyperliquid_data.py --symbols BTC-USD ETH-USD SOL-USD --days 7

# 自定义输出目录
python scripts/fetch_hyperliquid_data.py --days 30 --output data/my_data
```

### 运行测试

```bash
# 运行集成测试
python test_hyperliquid_integration.py

# 运行特定测试
pytest test_hyperliquid_integration.py::TestHyperliquidIntegration::test_data_provider_connection -v
```

## 使用示例

### 1. 基本数据获取

```python
import asyncio
from hyperliquid_data_provider import HyperliquidDataManager

async def main():
    manager = HyperliquidDataManager("configs/config.yaml")
    df = await manager.fetch_and_process_data(days_back=7)
    print(f"获取了 {len(df)} 条记录")
    
if __name__ == "__main__":
"
    asyncio.run(main())
```

### 2. 实时数据处理

```python
import asyncio
from realtime_processor import RealtimeDataProcessor

async def main():
    config = {
        'realtime': {'symbol': 'BTC-USD'},
        'env': {'window_size': 50}
    }
    
    processor = RealtimeDataProcessor(config)
    await processor.start()
    
    # 获取最新特征
    features = processor.get_latest_features(5)
    print(f"获取了 {len(features)} 个最新特征")
    
    await processor.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. 数据验证和清理

```python
from data_validator import DataQualityValidator, DataHealthMonitor
import pandas as pd

# 加载数据
df = pd.read_csv('data/raw_data.csv')

# 验证数据质量
validator = DataQualityValidator(config)
result = validator.validate_dataframe(df)

if result['valid']:
    print("数据验证通过")
    
    # 清理数据
    cleaned_df = validator.clean_data(df)
    
    # 监控数据健康
    monitor = DataHealthMonitor(config)
    health_report = monitor.monitor_data_quality(cleaned_df)
    print(f"数据健康分数: {health_report['health_score']}")
else:
    print("数据验证失败:", result['errors'])
```

## 配置说明

### 配置文件 (configs/config.yaml)

```yaml
data:
  csv_path: data/sample_data.csv
  symbol: "BTC-USD"
  interval: "1m"
  
env:
  window_size: 50  # 特征窗口大小
  
realtime:
  websocket_url: "wss://api.hyperliquid.xyz/ws"
  symbol: "BTC-USD"
```

## 数据格式

### 原始数据格式
```json
{
  "timestamp": 1640995200000,
  "open": 50000.0,
  "high": 51000.0,
  "low": 49500.0,
  "close": 50500.0,
  "volume": 1000.0,
  "symbol": "BTC-USD"
}
```

### 训练数据格式
- 特征维度: (window_size + 技术特征数量)
- 标签: 离散动作 (0: 空仓, 1: 做多, 2: 做空)

## API参考

### HyperliquidDataProvider

#### 方法
- `get_historical_data()`: 获取历史K线数据
- `get_market_info()`: 获取市场信息
- `get_orderbook_snapshot()`: 获取订单簿快照
- `get_recent_trades()`: 获取最近交易

### DataFormatter

#### 方法
- `format_hyperliquid_data()`: 格式化原始数据
- `create_state_features()`: 创建状态特征
- `prepare_training_dataset()`: 准备训练数据集

### RealtimeDataProcessor

#### 方法
- `start()`: 启动实时处理
- `stop()`: 停止实时处理
- `get_latest_features()`: 获取最新特征
- `get_stats()`: 获取统计信息

## 故障排除

### 常见问题

1. **连接超时**
   - 检查网络连接
   - 确认Hyperliquid API可用
   - 增加超时时间

2. **数据质量问题**
   - 使用DataValidator验证数据
   - 检查数据时间范围
   - 验证价格关系

3. **内存使用过高**
   - 减少缓冲区大小
   - 定期清理历史数据
   - 使用分批处理

### 错误处理

所有模块都包含完整的错误处理和重试机制。关键错误会记录到日志中。

## 性能优化

### 数据获取优化
- 使用批量请求减少API调用
- 实现请求缓存
- 支持断点续传

### 内存优化
- 使用生成器处理大数据
- 定期清理缓存
- 优化数据存储格式

## 监控和日志

### 日志配置
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 监控指标
- 数据获取成功率
- 数据处理延迟
- 内存使用情况
- 错误率统计

## 扩展开发

### 添加新的数据源
1. 创建新的数据提供器类
2. 实现数据获取方法
3. 添加数据验证规则
4. 更新配置选项

### 添加新的特征
1. 扩展DataFormatter类
2. 在create_state_features中添加新特征
3. 更新特征标准化逻辑
4. 测试新特征的有效性

## 最佳实践

1. **数据验证**: 始终验证数据质量
2. **错误处理**: 实现适当的重试机制
3. **监控**: 设置数据健康监控
4. **备份**: 定期备份处理后的数据
5. **测试**: 运行集成测试确保功能正常

## 支持

如有问题，请检查日志文件或提交issue。