async function main() {
  const PlayerNFT = await ethers.getContractFactory("PlayerNFT");
  const nft = await PlayerNFT.deploy();
  await nft.deployed();
  console.log("✅ PlayerNFT deployed to:", nft.address);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
