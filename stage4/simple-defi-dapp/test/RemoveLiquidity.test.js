const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Remove Liquidity", function () {
  let tokenA, tokenB, amm, owner;

  beforeEach(async () => {
    [owner] = await ethers.getSigners();

    const Token = await ethers.getContractFactory("MockERC20");
    tokenA = await Token.deploy("TokenA", "TKA");
    tokenB = await Token.deploy("TokenB", "TKB");
    await tokenA.deployed();
    await tokenB.deployed();

    const AMM = await ethers.getContractFactory("SimpleAMM");
    amm = await AMM.deploy(tokenA.address, tokenB.address);
    await amm.deployed();

    await tokenA.mint(owner.address, ethers.utils.parseEther("1000"));
    await tokenB.mint(owner.address, ethers.utils.parseEther("1000"));
    await tokenA.approve(amm.address, ethers.utils.parseEther("1000"));
    await tokenB.approve(amm.address, ethers.utils.parseEther("1000"));
  });

  it("should remove liquidity proportionally", async () => {
    await amm.addLiquidity(ethers.utils.parseEther("100"), ethers.utils.parseEther("200"));
    await amm.removeLiquidity(50); // remove 50%

    expect(await tokenA.balanceOf(owner.address)).to.be.gt(ethers.utils.parseEther("900"));
    expect(await tokenB.balanceOf(owner.address)).to.be.gt(ethers.utils.parseEther("900"));
  });
});
