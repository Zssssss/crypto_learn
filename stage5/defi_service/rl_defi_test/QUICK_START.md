# 🚀 快速开始指南

## 1. 一键启动
```bash
# 安装依赖
pip install -r requirements.txt

# 运行测试
python run_test.py

# 获取示例数据
python test_fixed.py
```

## 2. 核心命令
| 命令 | 功能 |
|---|---|
| `python run_test.py` | 运行所有测试 |
| `python test_fixed.py` | 运行集成测试 |
| `python scripts/fetch_hyperliquid_data.py --help` | 查看数据获取帮助 |
| `python train_dqn.py` | 训练DQN模型 |
| `python train_ppo.py` | 训练PPO模型 |

## 3. 项目结构速览
```
📁 rl_defi_test/
├── 🎯 核心功能
│   ├── hyperliquid_data_provider.py  # 数据获取
│   ├── data_formatter.py            # 数据格式化
│   ├── data_validator.py            # 数据验证
│   └── utils.py                     # 工具函数
├── 📊 数据处理
│   ├── data_loader.py               # 数据加载
│   └── data/                        # 数据目录
├── 🧪 测试
│   ├── run_test.py                  # 一键测试
│   └── test_fixed.py                # 集成测试
└── ⚙️ 配置
    ├── requirements.txt             # 依赖
    └── configs/config.yaml          # 配置
```

## 4. 3步上手
### 第1步：安装
```bash
cd stage5/defi_service/rl_defi_test
pip install -r requirements.txt
```

### 第2步：测试
```bash
python run_test.py
# 输出：✓ 所有测试通过
```

### 第3步：使用
```python
# 使用示例数据
from data_loader import load_csv
df = load_csv('data/sample_data.csv')

# 验证数据
from data_validator import DataQualityValidator
validator = DataQualityValidator({})
result = validator.validate_dataframe(df)
```

## 5. 常见问题
| 问题 | 解决方案 |
|---|---|
| 模块导入错误 | 运行`pip install -r requirements.txt` |
| 数据为空 | 使用示例数据`data/sample_data.csv` |
| API错误 | 使用本地测试模式 |

## 6. 下一步
完成快速启动后，可以：
1. 查看完整文档：`README.md`
2. 运行训练：`python train_dqn.py`
3. 自定义配置：`configs/config.yaml`