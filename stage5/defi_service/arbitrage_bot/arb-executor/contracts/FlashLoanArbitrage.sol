// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@uniswap/v3-periphery/contracts/interfaces/ISwapRouter.sol";
import "@uniswap/v2-periphery/contracts/interfaces/IUniswapV2Router02.sol";

// Aave V3 闪电贷接口
interface IFlashLoanSimpleReceiver {
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external returns (bool);
}

interface IPoolAddressesProvider {
    function getPool() external view returns (address);
}

interface IPool {
    function flashLoanSimple(
        address receiverAddress,
        address asset,
        uint256 amount,
        bytes calldata params,
        uint16 referralCode
    ) external;
}

/**
 * @title 闪电贷套利合约
 * @notice 支持 Aave 闪电贷和多 DEX 套利
 * @dev 实现了完整的闪电贷套利流程，包括安全检查和利润提取
 */
contract FlashLoanArbitrage is IFlashLoanSimpleReceiver, Ownable {
    // ========== 状态变量 ==========
    IPoolAddressesProvider public immutable ADDRESSES_PROVIDER;
    IPool public immutable POOL;
    ISwapRouter public immutable swapRouterV3;
    IUniswapV2Router02 public immutable swapRouterV2;
    
    // 重入保护
    uint256 private constant _NOT_ENTERED = 1;
    uint256 private constant _ENTERED = 2;
    uint256 private _status;
    
    // 支持的代币地址
    mapping(address => bool) public supportedTokens;
    
    // 套利参数
    struct ArbParams {
        address tokenBorrow;    // 借入的代币
        uint256 borrowAmount;   // 借入数量
        address tokenIntermediate; // 中间代币
        address dexBuy;        // 购买使用的 DEX
        address dexSell;       // 卖出使用的 DEX
        uint24 feeV3;          // V3 手续费等级
        uint256 minProfit;     // 最小利润要求
    }
    
    // 统计数据
    uint256 public totalArbitrages;
    uint256 public totalProfit;
    mapping(address => uint256) public tokenProfits;
    
    // ========== 事件 ==========
    event ArbitrageExecuted(
        address indexed token,
        uint256 borrowAmount,
        uint256 profit,
        uint256 timestamp
    );
    
    event ProfitWithdrawn(
        address indexed token,
        uint256 amount,
        address indexed recipient
    );
    
    event EmergencyWithdraw(
        address indexed token,
        uint256 amount
    );
    
    // ========== 修饰器 ==========
    modifier onlyPool() {
        require(msg.sender == address(POOL), "Caller must be Pool");
        _;
    }
    
    modifier onlySupportedToken(address token) {
        require(supportedTokens[token], "Token not supported");
        _;
    }
    
    // ========== 修饰器 ==========
    modifier nonReentrant() {
        require(_status != _ENTERED, "ReentrancyGuard: reentrant call");
        _status = _ENTERED;
        _;
        _status = _NOT_ENTERED;
    }
    
    // ========== 构造函数 ==========
    constructor(
        address _addressProvider,
        address _swapRouterV3,
        address _swapRouterV2
    ) Ownable(msg.sender) {
        ADDRESSES_PROVIDER = IPoolAddressesProvider(_addressProvider);
        POOL = IPool(ADDRESSES_PROVIDER.getPool());
        swapRouterV3 = ISwapRouter(_swapRouterV3);
        swapRouterV2 = IUniswapV2Router02(_swapRouterV2);
        _status = _NOT_ENTERED;
    }
    
    // ========== 管理函数 ==========
    
    /**
     * @notice 添加支持的代币
     * @param token 代币地址
     */
    function addSupportedToken(address token) external onlyOwner {
        supportedTokens[token] = true;
    }
    
    /**
     * @notice 移除支持的代币
     * @param token 代币地址
     */
    function removeSupportedToken(address token) external onlyOwner {
        supportedTokens[token] = false;
    }
    
    // ========== 套利执行 ==========
    
    /**
     * @notice 发起闪电贷套利
     * @param params 套利参数
     */
    function initiateArbitrage(ArbParams calldata params) 
        external 
        onlyOwner 
        nonReentrant 
        onlySupportedToken(params.tokenBorrow)
    {
        // 编码参数传递给闪电贷回调
        bytes memory data = abi.encode(params);
        
        // 发起闪电贷
        POOL.flashLoanSimple(
            address(this),
            params.tokenBorrow,
            params.borrowAmount,
            data,
            0
        );
    }
    
    /**
     * @notice Aave 闪电贷回调函数
     * @dev 在这里执行套利逻辑
     */
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external override onlyPool returns (bool) {
        require(initiator == address(this), "Invalid initiator");
        
        // 解码参数
        ArbParams memory arbParams = abi.decode(params, (ArbParams));
        
        // 计算需要偿还的总额
        uint256 amountOwed = amount + premium;
        
        // 执行套利交易
        uint256 profit = _executeArbitrageTrades(arbParams);
        
        // 确保有足够的利润
        require(profit > premium + arbParams.minProfit, "Insufficient profit");
        
        // 批准 Pool 提取偿还金额
        IERC20(asset).approve(address(POOL), amountOwed);
        
        // 更新统计
        totalArbitrages++;
        totalProfit += (profit - premium);
        tokenProfits[asset] += (profit - premium);
        
        // 发出事件
        emit ArbitrageExecuted(
            asset,
            amount,
            profit - premium,
            block.timestamp
        );
        
        return true;
    }
    
    /**
     * @notice 执行套利交易
     * @dev 内部函数，执行实际的 DEX 交易
     */
    function _executeArbitrageTrades(ArbParams memory params) 
        private 
        returns (uint256 profit) 
    {
        uint256 initialBalance = IERC20(params.tokenBorrow).balanceOf(address(this));
        
        // 第一步：在 DEX1 上用借入的代币换取中间代币
        if (params.dexBuy == address(swapRouterV3)) {
            _swapV3(
                params.tokenBorrow,
                params.tokenIntermediate,
                params.borrowAmount,
                params.feeV3
            );
        } else {
            _swapV2(
                params.tokenBorrow,
                params.tokenIntermediate,
                params.borrowAmount,
                params.dexBuy
            );
        }
        
        // 获取中间代币余额
        uint256 intermediateBalance = IERC20(params.tokenIntermediate).balanceOf(address(this));
        require(intermediateBalance > 0, "Swap 1 failed");
        
        // 第二步：在 DEX2 上将中间代币换回借入的代币
        if (params.dexSell == address(swapRouterV3)) {
            _swapV3(
                params.tokenIntermediate,
                params.tokenBorrow,
                intermediateBalance,
                params.feeV3
            );
        } else {
            _swapV2(
                params.tokenIntermediate,
                params.tokenBorrow,
                intermediateBalance,
                params.dexSell
            );
        }
        
        // 计算利润
        uint256 finalBalance = IERC20(params.tokenBorrow).balanceOf(address(this));
        require(finalBalance > initialBalance, "No profit");
        
        profit = finalBalance - initialBalance;
    }
    
    /**
     * @notice Uniswap V3 交换
     */
    function _swapV3(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint24 fee
    ) private {
        IERC20(tokenIn).approve(address(swapRouterV3), amountIn);
        
        ISwapRouter.ExactInputSingleParams memory params = ISwapRouter
            .ExactInputSingleParams({
                tokenIn: tokenIn,
                tokenOut: tokenOut,
                fee: fee,
                recipient: address(this),
                deadline: block.timestamp,
                amountIn: amountIn,
                amountOutMinimum: 0,
                sqrtPriceLimitX96: 0
            });
            
        swapRouterV3.exactInputSingle(params);
    }
    
    /**
     * @notice Uniswap V2 交换
     */
    function _swapV2(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        address router
    ) private {
        IERC20(tokenIn).approve(router, amountIn);
        
        address[] memory path = new address[](2);
        path[0] = tokenIn;
        path[1] = tokenOut;
        
        IUniswapV2Router02(router).swapExactTokensForTokens(
            amountIn,
            0, // 接受任何数量的输出代币
            path,
            address(this),
            block.timestamp
        );
    }
    
    // ========== 利润管理 ==========
    
    /**
     * @notice 提取利润
     * @param token 代币地址
     * @param amount 提取数量
     */
    function withdrawProfit(address token, uint256 amount) 
        external 
        onlyOwner 
        nonReentrant 
    {
        require(amount > 0, "Amount must be greater than 0");
        
        uint256 balance = IERC20(token).balanceOf(address(this));
        require(balance >= amount, "Insufficient balance");
        
        IERC20(token).transfer(owner(), amount);
        
        emit ProfitWithdrawn(token, amount, owner());
    }
    
    /**
     * @notice 紧急提取所有资金
     * @param token 代币地址
     */
    function emergencyWithdraw(address token) 
        external 
        onlyOwner 
        nonReentrant 
    {
        uint256 balance = IERC20(token).balanceOf(address(this));
        if (balance > 0) {
            IERC20(token).transfer(owner(), balance);
            emit EmergencyWithdraw(token, balance);
        }
    }
    
    // ========== 查询函数 ==========
    
    /**
     * @notice 获取合约中的代币余额
     * @param token 代币地址
     */
    function getBalance(address token) external view returns (uint256) {
        return IERC20(token).balanceOf(address(this));
    }
    
    /**
     * @notice 获取统计数据
     */
    function getStats() external view returns (
        uint256 _totalArbitrages,
        uint256 _totalProfit
    ) {
        return (totalArbitrages, totalProfit);
    }
    
    /**
     * @notice 检查套利机会
     * @dev 只读函数，用于链下模拟
     */
    function checkArbitrage(ArbParams calldata params) 
        external 
        view 
        returns (bool profitable, uint256 estimatedProfit) 
    {
        // 这里可以添加链下模拟逻辑
        // 实际实现需要集成 DEX 的报价功能
        return (false, 0);
    }
    
    // ========== 接收 ETH ==========
    receive() external payable {}
    
    fallback() external payable {}
}