import { ethers } from "ethers";

// 1. RPC 与钱包
const provider = new ethers.JsonRpcProvider("https://mainnet.infura.io/v3/YOUR_INFURA_KEY");
const wallet = new ethers.Wallet("YOUR_PRIVATE_KEY", provider);

// 2. 合约地址
const swapRouterAddress = "0xE592427A0AEce92De3Edee1F18E0157C05861564";
const quoterAddress = "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6";

// 3. ABI
const swapRouterABI = [
  "function exactInputSingle(tuple(address tokenIn, address tokenOut, uint24 fee, address recipient, uint256 deadline, uint256 amountIn, uint256 amountOutMinimum, uint160 sqrtPriceLimitX96)) external payable returns (uint256 amountOut)"
];

const quoterABI = [
  "function quoteExactInputSingle(address tokenIn, address tokenOut, uint24 fee, uint256 amountIn, uint160 sqrtPriceLimitX96) external returns (uint256 amountOut)"
];

const erc20ABI = [
  "function approve(address spender, uint256 value) external returns (bool)",
  "function allowance(address owner, address spender) view returns (uint256)"
];

// 4. 初始化合约
const swapRouter = new ethers.Contract(swapRouterAddress, swapRouterABI, wallet);
const quoter = new ethers.Contract(quoterAddress, quoterABI, provider);

// 5. Token 地址
const DAI = "0x6B175474E89094C44Da98b954EedeAC495271d0F";
const WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2";

// 6. Swap with Quoter
async function swapExactInputSingle() {
  const amountIn = ethers.parseUnits("10", 18); // 输入 10 DAI
  const fee = 3000; // 0.3%
  const recipient = await wallet.getAddress();
  const deadline = Math.floor(Date.now() / 1000) + (60 * 10); // 10分钟有效

  // 先用 Quoter 估算可得到多少 WETH
  const quotedAmountOut = await quoter.quoteExactInputSingle(
    DAI,
    WETH,
    fee,
    amountIn,
    0 // 不设价格限制
  );

  // 设置最小接收（例如取 95% 防滑点）
  const amountOutMin = quotedAmountOut * 95n / 100n;

  console.log(`预计可得到 ${ethers.formatUnits(quotedAmountOut, 18)} WETH`);
  console.log(`设置最小接收 ${ethers.formatUnits(amountOutMin, 18)} WETH`);

  // 批准 Router 花费 DAI
  const dai = new ethers.Contract(DAI, erc20ABI, wallet);
  const allowance = await dai.allowance(recipient, swapRouterAddress);
  if (allowance < amountIn) {
    console.log("Approving DAI...");
    const approvalTx = await dai.approve(swapRouterAddress, amountIn);
    await approvalTx.wait();
  }

  // 构造参数
  const params = {
    tokenIn: DAI,
    tokenOut: WETH,
    fee: fee,
    recipient: recipient,
    deadline: deadline,
    amountIn: amountIn,
    amountOutMinimum: amountOutMin,
    sqrtPriceLimitX96: 0,
  };

  // 执行 swap
  console.log("Swapping...");
  const tx = await swapRouter.exactInputSingle(params);
  console.log("Tx hash:", tx.hash);

  const receipt = await tx.wait();
  console.log("Swap 成功 ✅, 区块:", receipt.blockNumber);
}

swapExactInputSingle().catch(console.error);
