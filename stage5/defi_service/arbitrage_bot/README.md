# 🚀 DeFi 套利机器人

一个功能完善的去中心化金融（DeFi）套利机器人，支持多 DEX 套利、闪电贷和实时监控。

## 📋 目录

- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [使用指南](#使用指南)
- [智能合约](#智能合约)
- [安全考虑](#安全考虑)
- [性能优化](#性能优化)
- [故障排除](#故障排除)
- [开发路线图](#开发路线图)

## ✨ 功能特性

### 核心功能
- **多 DEX 支持**：Uniswap V2/V3、SushiSwap、Curve、Balancer
- **闪电贷集成**：支持 Aave V3 闪电贷，无需初始资金
- **实时监控**：毫秒级价格监控和套利机会发现
- **智能路由**：自动寻找最优套利路径
- **风险管理**：滑点保护、Gas 价格限制、最小利润阈值

### 高级功能
- **MEV 保护**：防止抢跑和三明治攻击
- **多链支持**：Ethereum、Arbitrum、Optimism、Polygon
- **性能监控**：详细的统计数据和性能指标
- **通知系统**：Telegram 实时通知
- **故障恢复**：自动重连和错误恢复机制

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                     套利机器人系统                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   价格监控    │  │   套利引擎    │  │   执行模块    │ │
│  │              │  │              │  │              │ │
│  │ • DEX 监控   │  │ • 机会识别   │  │ • 交易执行   │ │
│  │ • 价格聚合   │  │ • 路径优化   │  │ • Gas 优化   │ │
│  │ • 实时更新   │  │ • 利润计算   │  │ • 状态管理   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │                  智能合约层                        │  │
│  │                                                   │  │
│  │  • FlashLoanArbitrage.sol - 闪电贷套利合约        │  │
│  │  • USDTArbExecutor.sol - USDT 套利执行器          │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │                  区块链网络                        │  │
│  │                                                   │  │
│  │  Ethereum / Arbitrum / Optimism / Polygon         │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 前置要求

- Python 3.8+
- Node.js 16+
- Git

### 1. 克隆项目

```bash
git clone https://github.com/your-repo/arbitrage-bot.git
cd arbitrage-bot
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 3. 安装 Node.js 依赖（智能合约）

```bash
cd arb-executor
npm install
```

### 4. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的配置
```

### 5. 部署智能合约

```bash
cd arb-executor
npx hardhat compile
npx hardhat run scripts/deploy.js --network arbitrum
```

### 6. 运行机器人

```bash
# 运行基础版本
python arbitrage_bot.py

# 或运行高级版本
python arbitrage_bot_v2.py
```

## ⚙️ 配置说明

### 环境变量配置

创建 `.env` 文件并配置以下参数：

```env
# 网络配置
RPC_URL=https://arb1.arbitrum.io/rpc
BACKUP_RPC_URL=https://arbitrum-mainnet.infura.io/v3/YOUR_KEY

# 账户配置
ACCOUNT=0xYourWalletAddress
PRIVATE_KEY=0xYourPrivateKey
EXECUTOR=0xYourExecutorContract

# 套利参数
AMOUNT_USDT=100          # 每次套利金额
MIN_NET_PROFIT_USDT=0.5  # 最小净利润
SLIPPAGE_BPS=50          # 滑点容忍度（基点）
GAS_MULTIPLIER=1.2       # Gas 倍数

# 监控配置
SCAN_INTERVAL=1          # 扫描间隔（秒）
VERBOSE_LOGGING=true     # 详细日志
LOG_FILE_PATH=./logs/arbitrage.log

# 通知配置（可选）
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 支持的代币

默认支持以下代币（Arbitrum 网络）：

| 代币 | 合约地址 |
|------|----------|
| USDT | 0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9 |
| USDC | 0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8 |
| WETH | 0x82aF49447D8a07e3bd95BD0d56f35241523fBab1 |
| WBTC | 0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f |
| DAI  | 0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1 |

## 📖 使用指南

### 基础套利流程

1. **监控价格**：机器人持续监控多个 DEX 的价格
2. **识别机会**：当发现价格差异超过阈值时，识别套利机会
3. **计算利润**：考虑 Gas 费用和滑点，计算净利润
4. **执行交易**：如果利润满足要求，执行套利交易
5. **记录结果**：记录交易结果和统计数据

### 闪电贷套利

使用闪电贷可以在没有初始资金的情况下进行套利：

```python
# 配置闪电贷参数
FLASH_LOAN_ENABLED=true
AAVE_POOL_ADDRESS=0x794a61358D6845594F94dc1DB02A252b5b4814aD
```

### 监控和统计

机器人提供详细的监控和统计功能：

```python
# 查看实时统计
bot.print_stats()

# 输出示例：
# ==================================================
# 套利机器人统计
# 运行时间: 2.45 小时
# 发现机会: 156
# 执行交易: 12
# 成功交易: 10
# 总利润: 125.32 USDT
# ==================================================
```

## 📜 智能合约

### FlashLoanArbitrage.sol

支持 Aave V3 闪电贷的高级套利合约：

```solidity
// 主要功能
- initiateArbitrage(): 发起闪电贷套利
- executeOperation(): 闪电贷回调，执行套利
- withdrawProfit(): 提取利润
- emergencyWithdraw(): 紧急提取
```

### USDTArbExecutor.sol

简单的 USDT 套利执行器：

```solidity
// 主要功能
- executeArb(): 执行套利交易
- 支持 USDT -> 中间代币 -> USDT 路径
```

### 部署脚本

```javascript
// scripts/deploy.js
async function main() {
    const [deployer] = await ethers.getSigners();
    
    // 部署闪电贷套利合约
    const FlashLoanArbitrage = await ethers.getContractFactory("FlashLoanArbitrage");
    const arbitrage = await FlashLoanArbitrage.deploy(
        AAVE_PROVIDER,
        UNISWAP_V3_ROUTER,
        SUSHI_ROUTER
    );
    
    console.log("FlashLoanArbitrage deployed to:", arbitrage.address);
}
```

## 🔒 安全考虑

### 私钥安全
- **永远不要**将私钥硬编码在代码中
- 使用环境变量或安全的密钥管理服务
- 考虑使用硬件钱包进行生产环境

### 合约安全
- 所有合约都包含 `onlyOwner` 修饰符
- 实现了重入保护（ReentrancyGuard）
- 包含紧急提取功能

### 交易安全
- 设置最大 Gas 价格限制
- 实现滑点保护
- 使用 MEV 保护（可选）

### 风险管理
- 设置最小利润阈值
- 限制每次交易金额
- 实现自动停损机制

## ⚡ 性能优化

### 1. 并发处理
使用多线程同时监控多个 DEX：

```python
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(dex.quote, ...) for dex in dexes]
```

### 2. 缓存优化
缓存常用数据减少 RPC 调用：

```python
@lru_cache(maxsize=128)
def get_token_decimals(token_address):
    return token_contract.functions.decimals().call()
```

### 3. Gas 优化
- 批量处理交易
- 使用最优 Gas 价格
- 避免不必要的存储操作

### 4. 网络优化
- 使用多个 RPC 节点
- 实现自动故障转移
- 使用 WebSocket 连接

## 🔧 故障排除

### 常见问题

#### 1. RPC 连接失败
```
错误: 无法连接到 RPC 节点
解决: 检查 RPC_URL 配置，尝试使用备用节点
```

#### 2. Gas 价格过高
```
错误: Gas 价格超过限制
解决: 调整 MAX_GAS_PRICE_GWEI 或等待 Gas 价格下降
```

#### 3. 交易失败
```
错误: 交易被回滚
解决: 增加滑点容忍度，检查流动性
```

#### 4. 余额不足
```
错误: 账户余额不足
解决: 确保账户有足够的代币和 ETH（用于 Gas）
```

### 日志分析

查看详细日志：

```bash
tail -f logs/arbitrage.log

# 过滤错误日志
grep ERROR logs/arbitrage.log

# 查看特定时间段
grep "2024-01-15" logs/arbitrage.log
```

## 📊 性能指标

### 关键指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 扫描延迟 | < 100ms | 价格更新延迟 |
| 交易成功率 | > 80% | 成功执行的交易比例 |
| 平均利润 | > 1 USDT | 每笔交易平均利润 |
| Gas 效率 | < 500k | 每笔交易 Gas 使用量 |

### 监控仪表板

可以集成 Grafana 进行可视化监控：

1. 安装 Prometheus 和 Grafana
2. 配置数据源
3. 导入仪表板模板

## 🗺️ 开发路线图

### 已完成 ✅
- [x] 基础套利功能
- [x] 多 DEX 支持
- [x] 闪电贷集成
- [x] 错误处理和日志
- [x] 环境配置模板

### 进行中 🚧
- [ ] Curve 和 Balancer 集成
- [ ] 多链支持
- [ ] Web 界面
- [ ] 高级 MEV 保护

### 计划中 📋
- [ ] 机器学习价格预测
- [ ] 自动参数优化
- [ ] 去中心化部署
- [ ] 移动应用

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## ⚠️ 免责声明

**重要提示**：
- 本软件仅供教育和研究目的
- 加密货币交易存在高风险
- 使用本软件进行真实交易需自行承担风险
- 开发者不对任何损失负责

## 📞 联系方式

- GitHub: [your-github](https://github.com/your-username)
- Email: your-email@example.com
- Telegram: @your-telegram

## 🙏 致谢

- [Uniswap](https://uniswap.org/)
- [Aave](https://aave.com/)
- [OpenZeppelin](https://openzeppelin.com/)
- [Web3.py](https://web3py.readthedocs.io/)

---

**Happy Arbitraging! 🚀**