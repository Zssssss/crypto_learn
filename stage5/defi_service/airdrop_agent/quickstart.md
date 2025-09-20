# 🚀 快速开始指南

## 1分钟上手

### 1. 安装并启动
```bash
# 进入项目目录
cd stage5/defi_service/airdrop_agent

# 一键启动
./start.sh
```

### 2. 配置钱包
编辑 `.env` 文件：
```bash
# 复制示例配置
cp .env.example .env

# 编辑配置文件
nano .env
```

### 3. 添加钱包
在 `.env` 中添加：
```
PRIVATE_KEYS=your_private_key_here
WALLET_ADDRESSES=your_wallet_address_here
```

### 4. 启动狩猎
```bash
# 开始空投狩猎
python3 main.py start

# 或使用Makefile
make start
```

## 5分钟完整配置

### 1. 获取RPC节点
- **免费节点**:
  - Alchemy: https://alchemy.com
  - Infura: https://infura.io
  - QuickNode: https://quicknode.com

### 2. 配置节点
```bash
# 编辑 .env 文件
ETH_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
BSC_RPC_URL=https://bsc-dataseed.binance.org/
POLYGON_RPC_URL=https://polygon-rpc.com
```

### 3. 设置ChromeDriver
```bash
# 自动下载（Linux）
wget -O chromedriver.zip https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$(google-chrome --version | sed -E 's/.* ([0-9]+(\.[0-9]+){3}).*/\1/')/chromedriver_linux64.zip
unzip chromedriver.zip
chmod +x chromedriver
```

### 4. 高级配置
```bash
# 调整检查频率（每小时检查一次）
CHECK_INTERVAL=3600

# 设置最大gas价格
MAX_GAS_PRICE=50

# 设置最小收益阈值
MIN_PROFIT_THRESHOLD=10.0

# 启用自动执行
AUTO_EXECUTE=true
```

## 常用命令速查

| 命令 | 说明 |
|------|------|
| `./start.sh` | 一键启动 |
| `python3 main.py start` | 启动空投狩猎 |
| `python3 main.py status` | 查看状态 |
| `python3 main.py wallets` | 查看钱包 |
| `python3 main.py history` | 查看历史 |
| `make start` | 使用Makefile启动 |
| `make status` | 查看状态 |
| `make clean` | 清理缓存 |

## Docker快速部署

### 1. 使用Docker
```bash
# 构建镜像
docker build -t airdrop-hunter .

# 运行容器
docker run -d \
  --name airdrop-hunter \
  -v $(pwd)/.env:/app/.env:ro \
  -v $(pwd)/logs:/app/logs \
  airdrop-hunter
```

### 2. 使用Docker Compose
```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f airdrop-hunter
```

## 故障排除

### 常见问题

1. **ChromeDriver版本不匹配**
   ```bash
   # 查看Chrome版本
   google-chrome --version
   
   # 下载对应版本
   wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$(google-chrome --version | sed -E 's/.* ([0-9]+(\.[0-9]+){3}).*/\1/')
   ```

2. **权限问题**
   ```bash
   chmod +x start.sh
   chmod +x chromedriver
   ```

3. **依赖问题**
   ```bash
   # 重新安装依赖
   pip install -r requirements.txt --force-reinstall
   ```

## 监控面板

### 1. 本地监控
```bash
# 查看实时日志
tail -f logs/airdrop_agent.log

# 查看空投数据
cat airdrops.json | jq '.[] | {name: .name, value: .estimated_value}'
```

### 2. Docker监控
```bash
# 访问Grafana
open http://localhost:3000
# 用户名: admin
```

## 安全建议

### 1. 钱包安全
- 使用专用钱包进行空投
- 分散资金到多个钱包
- 定期检查余额

### 2. 风险控制
- 设置合理的gas限制
- 启用小额测试模式
- 监控异常活动

### 3. 隐私保护
- 使用不同的IP地址
- 随机化操作时间
- 避免模式化行为

## 收益优化

### 1. 策略建议
- 优先高价值空投
- 分散投资多个项目
- 关注新兴网络

### 2. 时间管理
- 设置合理的检查频率
- 避免网络拥堵时段
- 及时跟进截止日期

## 社区支持

- 📧 问题反馈: 提交GitHub Issue
- 💬 技术讨论: 加入Discord群组
- 📖 文档更新: 关注README更新

---

**⚡ 开始使用，祝你狩猎愉快！**