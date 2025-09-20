# 🪂 Airdrop Hunter Agent

自动化的空投狩猎和交互执行系统，支持多链、多钱包的自动化空投交互。

## ✨ 功能特性

- **🔍 智能发现**: 自动从多个平台发现空投机会
- **🤖 自动交互**: 智能执行桥接、交易、流动性添加等任务
- **💰 多钱包管理**: 支持多个钱包的统一管理
- **🌐 多链支持**: 支持 Ethereum、BSC、Polygon、Arbitrum、Optimism 等主流网络
- **⚡ 实时监控**: 定时检查新的空投机会
- **📊 数据分析**: 详细的任务执行记录和收益分析
- **🛡️ 安全机制**: 内置风险控制和安全检查

## 🚀 快速开始

### 1. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd airdrop_agent

# 运行启动脚本
./start.sh
```

### 2. 配置环境

复制配置文件并编辑：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# RPC节点配置
ETH_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_KEY
BSC_RPC_URL=https://bsc-dataseed.binance.org/
POLYGON_RPC_URL=https://polygon-rpc.com

# 钱包配置
PRIVATE_KEYS=your_private_key_1,your_private_key_2,...
WALLET_ADDRESSES=your_wallet_address_1,your_wallet_address_2,...

# 运行配置
CHECK_INTERVAL=3600  # 检查间隔(秒)
MAX_GAS_PRICE=50  # 最大gas价格(gwei)
MIN_PROFIT_THRESHOLD=10.0  # 最小收益阈值(USD)
AUTO_EXECUTE=false  # 是否自动执行
```

### 3. 安装 ChromeDriver

下载对应版本的 ChromeDriver：
- 访问 https://chromedriver.chromium.org/
- 下载与你的Chrome版本匹配的驱动
- 放在项目根目录或添加到系统PATH

## 📖 使用方法

### 启动空投狩猎
```bash
# 启动完整服务
python3 main.py start

# 或使用启动脚本
./start.sh
```

### 查看状态
```bash
python3 main.py status
```

### 查看钱包信息
```bash
python3 main.py wallets
```

### 查看任务历史
```bash
python3 main.py history
```

### 显示帮助
```bash
python3 main.py help
```

## ⚙️ 配置说明

### 网络配置
在 `config.py` 中配置支持的网络：

- **Ethereum**: 主网
- **BSC**: 币安智能链
- **Polygon**: Polygon网络
- **Arbitrum**: Arbitrum二层网络
- **Optimism**: Optimism二层网络

### 空投发现源
系统支持从以下平台发现空投：

- **CoinGecko**: 官方空投列表
- **DeFiLlama**: DeFi协议空投
- **Twitter**: 社交媒体空投信息
- **Discord**: 社区空投
- **Telegram**: 频道空投信息

### 任务类型
支持的任务类型：

- **桥接任务**: 跨链桥接资产
- **交易任务**: 在DEX上进行交易
- **流动性任务**: 添加流动性到池子
- **铸造任务**: 铸造NFT或代币
- **通用任务**: 其他类型的交互

## 🔧 开发指南

### 项目结构
```
airdrop_agent/
├── main.py                 # 主程序入口
├── config.py              # 配置文件
├── requirements.txt       # 依赖列表
├── start.sh              # 启动脚本
├── wallet_manager.py      # 钱包管理
├── airdrop_finder.py      # 空投发现
├── interaction_executor.py # 交互执行
├── utils/
│   ├── __init__.py
│   └── logger.py          # 日志工具
├── logs/                 # 日志目录
├── data/                 # 数据目录
├── chrome_data/          # Chrome用户数据
├── airdrops.json         # 空投数据
├── task_results.json     # 任务结果
└── task_history.json     # 任务历史
```

### 添加新的空投源
在 `airdrop_finder.py` 中添加新的发现方法：

```python
async def _get_airdrops_from_new_source(self) -> List[Airdrop]:
    """从新的源获取空投"""
    airdrops = []
    # 实现获取逻辑
    return airdrops
```

### 添加新的任务类型
在 `interaction_executor.py` 中添加新的执行方法：

```python
def _execute_new_task_type(self, airdrop: Any, wallet_address: str) -> Dict[str, Any]:
    """执行新类型的任务"""
    result = {'success': False, 'tx_hash': None, 'gas_used': 0, 'message': ''}
    # 实现执行逻辑
    return result
```

## ⚠️ 安全提醒

1. **私钥安全**: 请妥善保管私钥，不要上传到公共仓库
2. **风险控制**: 建议先用小额测试
3. **网络选择**: 确保使用正确的网络配置
4. **Gas费用**: 设置合理的gas价格限制
5. **智能合约**: 谨慎交互未知合约

## 📊 监控和日志

### 日志文件
- `logs/airdrop_agent.log`: 详细运行日志
- `airdrops.json`: 发现的空投列表
- `task_results.json`: 任务执行结果
- `task_history.json`: 历史任务记录

### 监控指标
- 空投发现数量
- 任务执行成功率
- Gas费用消耗
- 钱包余额变化

## 🐛 故障排除

### 常见问题

1. **ChromeDriver版本不匹配**
   ```bash
   # 检查Chrome版本
   google-chrome --version
   # 下载对应版本的ChromeDriver
   ```

2. **网络连接问题**
   - 检查RPC节点配置
   - 确保网络连接正常
   - 验证API密钥有效性

3. **钱包连接失败**
   - 检查私钥格式
   - 确认钱包有足够余额
   - 验证网络配置

4. **空投发现失败**
   - 检查网络连接
   - 验证目标网站可访问
   - 查看详细日志

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 开发环境
```bash
# 创建开发环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 运行测试
python -m pytest tests/
```

## 📄 许可证

MIT License - 详见 LICENSE 文件

## 📞 联系方式

- 项目Issues: [GitHub Issues](https://github.com/your-repo/issues)
- 技术支持: [Discord](https://discord.gg/your-server)

---

⚡ **使用本项目即表示您同意承担所有相关风险，开发者不对任何损失负责**