const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("🚀 开始部署套利合约...\n");

  // 获取部署账户
  const [deployer] = await hre.ethers.getSigners();
  console.log("部署账户:", deployer.address);
  
  const balance = await deployer.getBalance();
  console.log("账户余额:", hre.ethers.utils.formatEther(balance), "ETH\n");

  // 网络配置
  const network = await hre.ethers.provider.getNetwork();
  console.log("网络:", network.name, "(Chain ID:", network.chainId, ")\n");

  // 合约地址配置（Arbitrum 主网）
  const addresses = {
    arbitrum: {
      aaveProvider: "0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb",
      uniswapV3Router: "0xE592427A0AEce92De3Edee1F18E0157C05861564",
      sushiRouter: "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
      usdt: "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
      usdc: "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
      weth: "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
    },
    arbitrumGoerli: {
      aaveProvider: "0x4dd5ab8Fb385462cf9B0dD6f3aD12F81F8F1F3d3",
      uniswapV3Router: "0xE592427A0AEce92De3Edee1F18E0157C05861564",
      sushiRouter: "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
      usdt: "0x2E8D05e2D7d1dC7e0dC29B5cF3d3b8f3B8f3B8f3",
      usdc: "0x8FB1E3fC51F3b789dED7557E680551d93Ea9d892",
      weth: "0xe39Ab88f8A4777030A534146A9Ca3B52bd5D43A3"
    }
  };

  // 选择网络配置
  let config;
  if (network.chainId === 42161) {
    config = addresses.arbitrum;
    console.log("使用 Arbitrum 主网配置");
  } else if (network.chainId === 421613) {
    config = addresses.arbitrumGoerli;
    console.log("使用 Arbitrum Goerli 测试网配置");
  } else {
    console.error("❌ 不支持的网络！请使用 Arbitrum 主网或 Goerli 测试网");
    process.exit(1);
  }

  console.log("\n📋 合约配置:");
  console.log("  Aave Provider:", config.aaveProvider);
  console.log("  Uniswap V3 Router:", config.uniswapV3Router);
  console.log("  Sushi Router:", config.sushiRouter);
  console.log("  USDT:", config.usdt);
  console.log("  USDC:", config.usdc);
  console.log("  WETH:", config.weth);
  console.log();

  try {
    // 1. 部署简单套利执行器
    console.log("1️⃣ 部署 USDTArbExecutor...");
    const USDTArbExecutor = await hre.ethers.getContractFactory("USDTArbExecutor");
    const usdtExecutor = await USDTArbExecutor.deploy(
      config.usdt,
      config.sushiRouter
    );
    await usdtExecutor.deployed();
    console.log("✅ USDTArbExecutor 部署成功:", usdtExecutor.address);

    // 2. 部署闪电贷套利合约
    console.log("\n2️⃣ 部署 FlashLoanArbitrage...");
    const FlashLoanArbitrage = await hre.ethers.getContractFactory("FlashLoanArbitrage");
    const flashArbitrage = await FlashLoanArbitrage.deploy(
      config.aaveProvider,
      config.uniswapV3Router,
      config.sushiRouter
    );
    await flashArbitrage.deployed();
    console.log("✅ FlashLoanArbitrage 部署成功:", flashArbitrage.address);

    // 3. 配置支持的代币
    console.log("\n3️⃣ 配置支持的代币...");
    const tokens = [config.usdt, config.usdc, config.weth];
    for (const token of tokens) {
      const tx = await flashArbitrage.addSupportedToken(token);
      await tx.wait();
      console.log(`  ✅ 添加代币: ${token}`);
    }

    // 4. 保存部署信息
    const deploymentInfo = {
      network: network.name,
      chainId: network.chainId,
      deployer: deployer.address,
      timestamp: new Date().toISOString(),
      contracts: {
        USDTArbExecutor: {
          address: usdtExecutor.address,
          params: {
            usdt: config.usdt,
            router: config.sushiRouter
          }
        },
        FlashLoanArbitrage: {
          address: flashArbitrage.address,
          params: {
            aaveProvider: config.aaveProvider,
            uniswapV3Router: config.uniswapV3Router,
            sushiRouter: config.sushiRouter
          },
          supportedTokens: tokens
        }
      }
    };

    // 保存到文件
    const deploymentPath = path.join(__dirname, "../deployments");
    if (!fs.existsSync(deploymentPath)) {
      fs.mkdirSync(deploymentPath, { recursive: true });
    }

    const filename = `deployment-${network.chainId}-${Date.now()}.json`;
    const filepath = path.join(deploymentPath, filename);
    fs.writeFileSync(filepath, JSON.stringify(deploymentInfo, null, 2));
    console.log(`\n📁 部署信息已保存到: ${filepath}`);

    // 5. 更新 .env 文件
    console.log("\n4️⃣ 更新环境变量...");
    const envPath = path.join(__dirname, "../../.env");
    const envExample = path.join(__dirname, "../../.env.example");
    
    if (!fs.existsSync(envPath) && fs.existsSync(envExample)) {
      // 如果 .env 不存在，从模板创建
      fs.copyFileSync(envExample, envPath);
    }

    if (fs.existsSync(envPath)) {
      let envContent = fs.readFileSync(envPath, "utf8");
      
      // 更新 EXECUTOR 地址
      if (envContent.includes("EXECUTOR=")) {
        envContent = envContent.replace(
          /EXECUTOR=.*/,
          `EXECUTOR=${flashArbitrage.address}`
        );
      } else {
        envContent += `\nEXECUTOR=${flashArbitrage.address}`;
      }
      
      fs.writeFileSync(envPath, envContent);
      console.log("✅ 已更新 .env 文件中的 EXECUTOR 地址");
    }

    // 6. 验证合约（可选）
    if (network.chainId === 42161 || network.chainId === 421613) {
      console.log("\n5️⃣ 准备验证合约...");
      console.log("请运行以下命令验证合约:");
      console.log(`npx hardhat verify --network ${network.name} ${usdtExecutor.address} ${config.usdt} ${config.sushiRouter}`);
      console.log(`npx hardhat verify --network ${network.name} ${flashArbitrage.address} ${config.aaveProvider} ${config.uniswapV3Router} ${config.sushiRouter}`);
    }

    // 7. 显示总结
    console.log("\n" + "=".repeat(60));
    console.log("🎉 部署完成！");
    console.log("=".repeat(60));
    console.log("\n📊 部署总结:");
    console.log(`  网络: ${network.name} (Chain ID: ${network.chainId})`);
    console.log(`  部署者: ${deployer.address}`);
    console.log(`  USDTArbExecutor: ${usdtExecutor.address}`);
    console.log(`  FlashLoanArbitrage: ${flashArbitrage.address}`);
    console.log("\n💡 下一步:");
    console.log("  1. 确保账户有足够的 ETH 用于 Gas 费用");
    console.log("  2. 如果使用简单套利，确保账户有足够的 USDT");
    console.log("  3. 运行 'python arbitrage_bot_v2.py' 启动套利机器人");
    console.log("=".repeat(60));

  } catch (error) {
    console.error("\n❌ 部署失败:", error);
    process.exit(1);
  }
}

// 错误处理
main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
