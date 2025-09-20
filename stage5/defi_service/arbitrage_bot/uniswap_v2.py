"""
Uniswap V2 DEX接口实现
支持Uniswap V2、SushiSwap等兼容V2的DEX
"""

import json
from web3 import Web3
from typing import Dict, Optional, Tuple
from .arbitrage_bot import EnhancedDEXInterface

class UniswapV2(EnhancedDEXInterface):
    """Uniswap V2 DEX接口"""
    
    # Uniswap V2 Router ABI (简化版)
    ROUTER_ABI = json.loads('''[
        {
            "inputs": [
                {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                {"internalType": "address[]", "name": "path", "type": "address[]"}
            ],
            "name": "getAmountsOut",
            "outputs": [
                {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}
            ],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [
                {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
                {"internalType": "address[]", "name": "path", "type": "address[]"}
            ],
            "name": "getAmountsIn",
            "outputs": [
                {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}
            ],
            "stateMutability": "view",
            "type": "function"
        }
    ]''')
    
    def __init__(self, w3: Web3, router_address: str, dex_name: str = "UniswapV2"):
        super().__init__(w3, dex_name, {})
        self.router = w3.eth.contract(
            address=Web3.to_checksum_address(router_address),
            abi=self.ROUTER_ABI
        )
    
    async def quote_async(self, token_in: str, token_out: str, amount_in: int) -> Optional[Dict]:
        """获取Uniswap V2报价"""
        try:
            token_in_addr = Web3.to_checksum_address(token_in)
            token_out_addr = Web3.to_checksum_address(token_out)
            
            # 构建交易路径
            path = [token_in_addr, token_out_addr]
            
            # 获取输出金额
            amounts = self.router.functions.getAmountsOut(amount_in, path).call()
            
            if len(amounts) >= 2:
                amount_out = amounts[-1]
                
                return {
                    "dex": self.name,
                    "amount_out": amount_out,
                    "price": amount_out / amount_in if amount_in > 0 else 0,
                    "fee": 30,  # 0.3% fee
                    "gas_estimate": 150000  # 估算gas
                }
            
        except Exception as e:
            self.logger.debug(f"{self.name} quote failed: {e}")
        
        return None
    
    def get_liquidity(self, token_a: str, token_b: str) -> Optional[Tuple[int, int]]:
        """获取流动性（简化实现）"""
        # 在实际应用中，这里应该从链上获取池子信息
        # 简化实现，返回固定值
        return (10**18, 10**18)  # 1 ETH worth of liquidity
    
    def estimate_price_impact(self, token_in: str, token_out: str, amount_in: int) -> float:
        """估算价格影响"""
        # 简化实现
        return 0.2  # 0.2% impact