from web3 import Web3

# Arbitrum 主网 RPC
RPC_URL = "https://arb1.arbitrum.io/rpc"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# USDT (Arbitrum 合约地址，6位小数)
USDT = Web3.to_checksum_address("0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9")
# WETH (Arbitrum 合约地址，18位小数)
WETH = Web3.to_checksum_address("0x82af49447d8a07e3bd95bd0d56f35241523fbab1")

# Uniswap v3 Router
UNISWAP_ROUTER = Web3.to_checksum_address("0xe592427a0aece92de3edee1f18e0157c05861564")

# SushiSwap Router (Arbitrum)
SUSHI_ROUTER = Web3.to_checksum_address("0x1b02da8cb0d097eb8d57a175b88c7d8b47997506")

# ERC20 ABI (只要 balanceOf/decimals 就够)
ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}],
     "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals",
     "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
]

# Uniswap v2 Router ABI (Sushi 用)
UNISWAP_V2_ROUTER_ABI = [
    {"name": "getAmountsOut", "outputs": [{"type": "uint256[]", "name": "amounts"}],
     "inputs": [{"type": "uint256", "name": "amountIn"},
                {"type": "address[]", "name": "path"}],
     "stateMutability": "view", "type": "function"},
]

# Uniswap v3 Quoter (独立合约)
UNISWAP_QUOTER = Web3.to_checksum_address("0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6")
UNISWAP_V3_QUOTER_ABI = [
    {"inputs": [
        {"internalType": "address", "name": "tokenIn", "type": "address"},
        {"internalType": "address", "name": "tokenOut", "type": "address"},
        {"internalType": "uint24", "name": "fee", "type": "uint24"},
        {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
        {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
    ],
     "name": "quoteExactInputSingle",
     "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
     "stateMutability": "nonpayable", "type": "function"}
]
