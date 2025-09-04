async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying contracts with:", deployer.address);

  const Token = await ethers.getContractFactory("MockERC20");
  const tokenA = await Token.deploy("TokenA", "TKA");
  const tokenB = await Token.deploy("TokenB", "TKB");

  await tokenA.deployed();
  await tokenB.deployed();

  const AMM = await ethers.getContractFactory("SimpleAMM");
  const amm = await AMM.deploy(tokenA.address, tokenB.address);
  await amm.deployed();

  console.log("TokenA:", tokenA.address);
  console.log("TokenB:", tokenB.address);
  console.log("AMM:", amm.address);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
