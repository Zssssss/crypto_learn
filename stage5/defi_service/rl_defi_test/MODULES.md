# 📦 模块说明文档

## 🔧 核心模块一览

### 1. 数据获取层
#### `hyperliquid_data_provider.py`
**功能**：连接Hyperliquid API获取数据
```python
# 使用示例
from hyperliquid_data_provider import HyperliquidDataProvider
provider = HyperliquidDataProvider(config)
data = await provider.fetch_historical_data("BTC-USD", 30)
```

**主要方法**：
- `fetch_historical_data()` - 获取历史数据
- `fetch_realtime_data()` - 获取实时数据
- `process_raw_data()` - 处理原始数据

### 2. 数据验证层
#### `data_validator.py`
**功能**：验证数据质量和完整性
```python
# 使用示例
from data_validator import DataQualityValidator
validator = DataQualityValidator(config)
result = validator.validate_dataframe(df)
```

**验证内容**：
- ✅ 必需列检查
- ✅ 数据类型验证
- ✅ 价格关系验证
- ✅ 异常值检测
- ✅ 时间序列完整性

### 3. 数据格式化层
#### `data_formatter.py`
**功能**：将原始数据转换为训练格式
```python
# 使用示例
from data_formatter import DataFormatter
formatter = DataFormatter(config)
X, y = formatter.prepare_training_dataset(df)
```

**功能特性**：
- 添加技术指标（MA, RSI, MACD等）
- 创建特征向量
- 生成训练标签
- 数据标准化

### 4. 数据加载层
#### `data_loader.py`
**功能**：加载和预处理CSV数据
```python
# 使用示例
from data_loader import load_csv, prepare_data
df = load_csv('data.csv')
df = prepare_data(df)
train_df, val_df, test_df = split_data(df)
```

### 5. 工具函数层
#### `utils.py`
**功能**：提供通用工具函数
```python
# 使用示例
from utils import add_technical_indicators, create_features
df = add_technical_indicators(df)
features = create_features(df)
```

**包含功能**：
- 技术指标计算（MA, RSI, MACD等）
- 特征向量创建
- 数据标准化
- 收益计算和标签生成

## 🎯 使用场景示例

### 场景1：完整数据流程
```python
from data_loader import load_csv, prepare_data
from data_validator import DataQualityValidator
from data_formatter import DataFormatter

# 1. 加载数据
df = load_csv('data.csv')
df = prepare_data(df)

# 2. 验证数据
validator = DataQualityValidator({})
result = validator.validate_dataframe(df)
df_clean = validator.clean_data(df)

# 3. 格式化训练数据
formatter = DataFormatter({})
X_train, X_val, X_test, y_train, y_val, y_test = formatter.prepare_training_dataset(df_clean)
```

### 场景2：使用示例数据
```python
from data_loader import create_sample_data
from data_formatter import DataFormatter

# 创建示例数据
create_sample_data('data/sample.csv', 1000)

# 加载并处理
df = load_csv('data/sample.csv')
formatter = DataFormatter({})
X, y = formatter.prepare_training_dataset(df)
```

### 场景3：自定义技术指标
```python
from utils import add_technical_indicators, create_features

# 添加技术指标
df = add_technical_indicators(df)

# 创建特征
features = create_features(df)

# 数据标准化
from utils import normalize_data
normalized = normalize_data(features)
```

## 📊 技术指标说明

项目自动计算以下技术指标：

| 指标 | 描述 | 用途 |
|---|---|---|
| **MA5/10/20/50** | 移动平均线 | 趋势识别 |
| **EMA12/26** | 指数移动平均 | 短期趋势 |
| **MACD** | 移动平均收敛发散 | 动量指标 |
| **RSI** | 相对强弱指标 | 超买超卖 |
| **BB** | 布林带 | 波动性 |
| **ATR** | 平均真实波幅 | 波动性 |
| **Stochastic** | 随机指标 | 动量 |
| **Williams %R** | 威廉指标 | 超买超卖 |

## 🔍 调试指南

### 常见问题排查
1. **模块导入错误**
   ```python
   # 检查导入
   python -c "from data_validator import DataQualityValidator; print('OK')"
   ```

2. **数据验证失败**
   ```python
   # 查看验证结果
   result = validator.validate_dataframe(df)
   print(result['errors'])
   ```

3. **特征创建问题**
   ```python
   # 检查特征维度
   features = create_features(df)
   print(f"特征维度: {features.shape}")
   ```

## 🚀 快速集成
将以下代码复制到您的项目中即可开始使用：

```python
# 完整数据管道
import sys
sys.path.append('rl_defi_test')

from data_loader import load_csv, prepare_data
from data_validator import DataQualityValidator
from data_formatter import DataFormatter

# 1. 加载数据
df = load_csv('your_data.csv')
df = prepare_data(df)

# 2. 验证和清理
validator = DataQualityValidator({})
df = validator.clean_data(df)

# 3. 准备训练数据
formatter = DataFormatter({})
X_train, X_val, X_test, y_train, y_val, y_test = formatter.prepare_training_dataset(df)