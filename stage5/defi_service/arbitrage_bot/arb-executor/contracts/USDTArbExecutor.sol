// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@uniswap/v2-periphery/contracts/interfaces/IUniswapV2Router02.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title USDT Arbitrage Executor
 * @notice 简单的套利执行器：USDT -> midToken -> USDT
 */
contract USDTArbExecutor is Ownable {
    address public usdt;
    address public router;

    constructor(address _usdt, address _router) {
        usdt = _usdt;
        router = _router;
    }

    function executeArb(
        address midToken,
        uint amountIn,
        uint amountOutMin
    ) external onlyOwner {
        // step 1: 收用户的 USDT
        require(
            IERC20(usdt).transferFrom(msg.sender, address(this), amountIn),
            "Transfer failed"
        );

        // step 2: 授权给 router
        IERC20(usdt).approve(router, amountIn);

        // step 3: swap USDT -> midToken
        address[] memory path = new address[](2);
        path[0] = usdt;
        path[1] = midToken;

        IUniswapV2Router02(router).swapExactTokensForTokens(
            amountIn,
            amountOutMin, // 可设置更大以降低滑点风险
            path,
            address(this),
            block.timestamp
        );

        uint midBalance = IERC20(midToken).balanceOf(address(this));
        require(midBalance > 0, "Swap to midToken failed");

        // step 4: swap midToken -> USDT
        IERC20(midToken).approve(router, midBalance);

        address[] memory pathBack = new address[](2);
        pathBack[0] = midToken;
        pathBack[1] = usdt;

        IUniswapV2Router02(router).swapExactTokensForTokens(
            midBalance,
            0, // 不设限制，直接换回
            pathBack,
            msg.sender,
            block.timestamp
        );
    }
}
