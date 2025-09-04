const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("SimpleAMM", function () {
  let tokenA, tokenB, amm, owner, user;

  beforeEach(async () => {
    [owner, user] = await ethers.getSigners();

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

  it("should add liquidity", async () => {
    await amm.addLiquidity(ethers.utils.parseEther("100"), ethers.utils.parseEther("200"));
    expect(await tokenA.balanceOf(amm.address)).to.equal(ethers.utils.parseEther("100"));
    expect(await tokenB.balanceOf(amm.address)).to.equal(ethers.utils.parseEther("200"));
  });

  it("should swap TokenA for TokenB", async () => {
    await amm.addLiquidity(ethers.utils.parseEther("100"), ethers.utils.parseEther("100"));
    await tokenA.mint(user.address, ethers.utils.parseEther("10"));
    await tokenA.connect(user).approve(amm.address, ethers.utils.parseEther("10"));

    await amm.connect(user).swap(tokenA.address, ethers.utils.parseEther("10"));
    expect(await tokenB.balanceOf(user.address)).to.be.gt(0);
  });
});
