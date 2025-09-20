"""
Uniswap V3 DEX接口实现
"""

import json
from web3 import Web3
from typing import Dict, Optional, Tuple
from .arbitrage_bot import EnhancedDEXInterface

class UniswapV3(EnhancedDEXInterface):
    """Uniswap V3 DEX接口"""
    
    # Uniswap V3 Quoter ABI
    QUOTER_ABI = json.loads('''[
        {
            "inputs": [
                {"internalType": "bytes", "name": "path", "type": "bytes"},
                {"internalType": "uint256", "name": "amountIn", "type": "uint256"}
            ],
            "name": "quoteExactInput",
            "outputs": [
                {"internalType": "uint256", "name": "amountOut", "type": "uint256"}
            ],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [
                {"internalType": "address", "name": "tokenIn", "type": "address"},
                {"internalType": "address", "name": "tokenOut", "type": "address"},
                {"internalType": "uint24", "name": "fee", "type": "uint24"},
                {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
            ],
            "name": "quoteExactInputSingle",
            "outputs": [
                {"internalType": "uint256", "name": "amountOut", "type": "uint256"}
            ],
            "stateMutability": "view",
            "type": "function"
        }
    ]''')
    
    def __init__(self, w3: Web3, quoter_address: str, default_fee: int = 3000):
        super().__init__(w3, "UniswapV3", {})
        self.quoter = w3.eth.contract(
            address=Web3.to_checksum_address(quoter_address),
            abi=self.QUOTER_ABI
        )
        self.default_fee = default_fee
    
    async def quote_async(self, token_in: str, token_out: str, amount_in: int) -> Optional[Dict]:
        """获取Uniswap V3报价"""
        try:
            # 使用单币报价
            token_in_addr = Web3.to_checksum_address(token_in)
            token_out_addr = Web3.to_checksum_address(token_out)
            
            amount_out = self.quoter.functions.quoteExactInputSingle(
                token_in_addr,
                token_out_addr,
                self.default_fee,
                amount_in,
                0  # 无价格限制
            ).call()
            
            return {
                "dex": self.name,
                "amount_out": amount_out,
                "price": amount_out / amount_in if amount_in > 0 else 0,
                "fee": self.default_fee,
                "gas_estimate": 200000  # 估算gas
            }
            
        except Exception as e:
            self.logger.debug(f"UniswapV3 quote failed: {e}")
            return None
    
    def get_liquidity(self, token_a: str, token_b: str) -> Optional[Tuple[int, int]]:
        """获取流动性（Uniswap V3需要更复杂的实现）"""
        # 简化实现，返回固定值
        return (10**18, 10**18)  # 1 ETH worth of liquidity
    
    def estimate_price_impact(self, token_in: str, token_out: str, amount_in: int) -> float:
        """估算价格影响"""
        # 简化实现
        return 0.1  # 0.1% impact