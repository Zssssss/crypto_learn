// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

interface IERC20 {
    function transfer(address to, uint amount) external returns (bool);
    function approve(address spender, uint amount) external returns (bool);
    function balanceOf(address account) external view returns (uint);
    function transferFrom(address sender, address recipient, uint amount) external returns (bool);
}

interface IUniswapV2Router {
    function swapExactTokensForTokens(
        uint amountIn,
        uint amountOutMin,
        address[] calldata path,
        address to,
        uint deadline
    ) external returns (uint[] memory amounts);
}

interface IUniswapV3Router {
    struct ExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        uint24 fee;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
    }

    function exactInputSingle(ExactInputSingleParams calldata params)
        external
        payable
        returns (uint256 amountOut);
}

contract USDTArbExecutor {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner {
        require(msg.sender == owner, "not owner");
        _;
    }

    function arb_USDT_V3_V2(
        address usdt,
        address midToken,
        address v3Router,
        address v2Router,
        uint24 v3Fee,
        uint amountIn,
        uint minProfit,
        uint v3MinOut,
        uint v2MinOut
    ) external {
        // pull USDT
        require(IERC20(usdt).transferFrom(msg.sender, address(this), amountIn), "transferFrom failed");

        // approve v3 router
        IERC20(usdt).approve(v3Router, amountIn);

        // swap USDT -> midToken on v3
        uint amountMid = IUniswapV3Router(v3Router).exactInputSingle(
            IUniswapV3Router.ExactInputSingleParams({
                tokenIn: usdt,
                tokenOut: midToken,
                fee: v3Fee,
                recipient: address(this),
                deadline: block.timestamp,
                amountIn: amountIn,
                amountOutMinimum: v3MinOut,
                sqrtPriceLimitX96: 0
            })
        );

        // approve v2 router
        IERC20(midToken).approve(v2Router, amountMid);

        // swap midToken -> USDT on v2
        address ;
        path[0] = midToken;
        path[1] = usdt;
        uint[] memory amounts = IUniswapV2Router(v2Router).swapExactTokensForTokens(
            amountMid,
            v2MinOut,
            path,
            address(this),
            block.timestamp
        );

        uint amountOut = amounts[amounts.length - 1];

        require(amountOut >= amountIn + minProfit, "no profit");

        // send back USDT
        IERC20(usdt).transfer(msg.sender, amountOut);
    }

    function withdrawToken(address token, uint amount) external onlyOwner {
        IERC20(token).transfer(owner, amount);
    }
}
