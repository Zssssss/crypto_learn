# NFT Game Demo

这是一个简单的 NFT 游戏 Demo，玩家通过 mint NFT 获得游戏身份。

## 📂 项目结构

```
nft-game/
├── contracts/            # Solidity 智能合约
│   └── PlayerNFT.sol
├── scripts/              # 部署脚本
│   └── deploy.js
├── hardhat.config.js     # Hardhat 配置
├── package.json          # Node 配置 (Hardhat)
├── frontend/             # 前端 React 应用
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       └── main.jsx
```

---

## 🚀 部署与运行

### 1. 准备环境
- Node.js >= 18
- npm 或 yarn
- MetaMask 钱包
- Infura 或 Alchemy API Key
- Sepolia 测试网 ETH

### 2. 安装合约依赖
```bash
cd nft-game
npm install
npx hardhat compile
```

### 3. 配置网络
修改 `hardhat.config.js`：

```js
sepolia: {
  url: "https://sepolia.infura.io/v3/YOUR_INFURA_KEY",
  accounts: ["YOUR_PRIVATE_KEY"]
}
```

- `YOUR_INFURA_KEY` 替换为你在 Infura 创建的 key  
- `YOUR_PRIVATE_KEY` 替换为钱包私钥（⚠️ 请勿泄露）

### 4. 部署合约
```bash
npx hardhat run scripts/deploy.js --network sepolia
```

终端会输出合约地址，例如：
```
✅ PlayerNFT deployed to: 0x1234abcd...
```

### 5. 修改前端配置
在 `frontend/src/App.jsx` 里替换：
```js
const contractAddress = "YOUR_DEPLOYED_CONTRACT_ADDRESS";
```

### 6. 运行前端
```bash
cd frontend
npm install
npm run dev
```

浏览器打开 http://localhost:5173 即可使用。

---

## 🎮 游戏玩法
- 连接钱包 → 输入角色名字 → mint 一个 Player NFT  
- 每个 NFT 初始等级为 1  
- 可以调用 `levelUp(tokenId)` 升级角色  

---

## 🔮 扩展思路
- 增加 ERC20 游戏代币奖励
- 增加战斗系统 (PVE/PVP)
- 增加装备 NFT，提升角色属性
