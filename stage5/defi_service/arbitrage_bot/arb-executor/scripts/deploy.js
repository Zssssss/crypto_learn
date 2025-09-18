const { ethers } = require("hardhat");

async function main() {
  // 修改为 Arbitrum USDT 和 UniswapV2 Router 地址
  const USDT = "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9"; // Arbitrum USDT
  const ROUTER = "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506"; // SushiSwap Router (UniswapV2 兼容)

  const Executor = await ethers.getContractFactory("USDTArbExecutor");
  const executor = await Executor.deploy(USDT, ROUTER);

  await executor.deployed();

  console.log("USDTArbExecutor 部署完成:", executor.address);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
