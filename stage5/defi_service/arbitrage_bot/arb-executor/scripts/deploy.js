const hre = require("hardhat");

async function main() {
  const Executor = await hre.ethers.getContractFactory("USDTArbExecutor");
  const executor = await Executor.deploy();
  await executor.deployed();
  console.log("✅ USDTArbExecutor deployed at:", executor.address);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
