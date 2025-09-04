// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract SimpleAMM {
    IERC20 public tokenA;
    IERC20 public tokenB;

    uint256 public reserveA;
    uint256 public reserveB;

    constructor(address _tokenA, address _tokenB) {
        tokenA = IERC20(_tokenA);
        tokenB = IERC20(_tokenB);
    }

    function addLiquidity(uint256 amountA, uint256 amountB) public {
        require(amountA > 0 && amountB > 0, "Invalid amounts");
        tokenA.transferFrom(msg.sender, address(this), amountA);
        tokenB.transferFrom(msg.sender, address(this), amountB);
        reserveA += amountA;
        reserveB += amountB;
    }

    function removeLiquidity(uint256 sharePercent) public {
        require(sharePercent > 0 && sharePercent <= 100, "Invalid percent");
        uint256 amountA = (reserveA * sharePercent) / 100;
        uint256 amountB = (reserveB * sharePercent) / 100;

        reserveA -= amountA;
        reserveB -= amountB;

        tokenA.transfer(msg.sender, amountA);
        tokenB.transfer(msg.sender, amountB);
    }

    function getAmountOut(uint256 amountIn, address fromToken) public view returns (uint256) {
        require(amountIn > 0, "Invalid input");
        if (fromToken == address(tokenA)) {
            uint256 amountInWithFee = amountIn * 997 / 1000;
            return (amountInWithFee * reserveB) / (reserveA + amountInWithFee);
        } else {
            uint256 amountInWithFee = amountIn * 997 / 1000;
            return (amountInWithFee * reserveA) / (reserveB + amountInWithFee);
        }
    }

    function swap(address fromToken, uint256 amountIn) public {
        require(amountIn > 0, "Invalid amount");
        if (fromToken == address(tokenA)) {
            uint256 amountOut = getAmountOut(amountIn, fromToken);
            tokenA.transferFrom(msg.sender, address(this), amountIn);
            tokenB.transfer(msg.sender, amountOut);
            reserveA += amountIn;
            reserveB -= amountOut;
        } else {
            uint256 amountOut = getAmountOut(amountIn, fromToken);
            tokenB.transferFrom(msg.sender, address(this), amountIn);
            tokenA.transfer(msg.sender, amountOut);
            reserveB += amountIn;
            reserveA -= amountOut;
        }
    }
}
