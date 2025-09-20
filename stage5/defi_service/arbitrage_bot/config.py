"""
增强版套利机器人配置文件
支持更多DEX、代币和高级功能
"""

from web3 import Web3
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ========== 网络配置 ==========
# Arbitrum 主网 RPC（可配置多个备用节点）
RPC_URLS = {
    "primary": os.getenv("RPC_URL", "https://arb1.arbitrum.io/rpc"),
    "backup": [
        "https://arbitrum-one.public.blastapi.io",
        "https://arb-mainnet.g.alchemy.com/v2/demo",
        "https://arbitrum.blockpi.network/v1/rpc/public",
        "https://rpc.ankr.com/arbitrum"
    ]
}

# ========== DEX配置 ==========
DEX_CONFIGS = {
    # Uniswap V3
    "uniswap_v3": {
        "router": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
        "quoter": "0x61FFE014BA17989E743C5F6CB21BF9697530B21E",
        "quoter_v2": "0x61fFE014BA17989E743c5F6CB21BF9697530B21E",
        "factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
        "nft_manager": "0xC36442b4a4522E871399CD717aBDD847Ab11FE88",
        "fees": [100, 500, 3000, 10000],  # 0.01%, 0.05%, 0.3%, 1%
        "enabled": True
    },
    
    # Uniswap V2 (在Arbitrum上较少使用)
    "uniswap_v2": {
        "router": "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24",
        "factory": "0xf1D7CC64Fb4452F05c498126312eBE29f30Fbcf9",
        "enabled": False
    },
    
    # SushiSwap
    "sushiswap": {
        "router": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
        "factory": "0xc35DADB65012eC5796536bD9864eD8773aBc74C4",
        "enabled": True
    },
    
    # Curve Finance
    "curve": {
        "registry": "0x445FE580eF8d70FF569aB36e80c647af338db351",
        "address_provider": "0x0000000022D53366457F9d5E68Ec105046FC4383",
        "pools": {
            "2pool": "0x7f90122BF0700F9E7e1F688fe926940E8839F353",
            "tricrypto": "0x960ea3e3C7FB317332d990873d354E18d7645590",
            "frax": "0xf07d553B195080F84F582e88ecdD54bAa122b279"
        },
        "enabled": True
    },
    
    # Balancer V2
    "balancer": {
        "vault": "0xBA12222222228d8Ba445958a75a0704d566BF2C8",
        "weighted_pool_factory": "0x7dFdEF5f355096603419239CE743BfaF1120312B",
        "stable_pool_factory": "0x2433477A10FC5d31B9513C638F19eE85CaED53Fd",
        "enabled": True
    },
    
    # GMX
    "gmx": {
        "router": "0xaBBc5F99639c9B6bCb58544ddf04EFA6802F4064",
        "reader": "0x22199a49A999c351eF7927602CFB187ec3cae489",
        "vault": "0x489ee077994B6658eAfA855C308275EAd8097C4A",
        "enabled": True
    },
    
    # Camelot
    "camelot": {
        "router": "0xc873fEcbd354f5A56E00E710B90EF4201db2448d",
        "factory": "0x6EcCab422D763aC031210895C81787E87B43A652",
        "enabled": True
    },
    
    # TraderJoe (LB)
    "traderjoe": {
        "lb_router": "0xb4315e873dBcf96Ffd0acd8EA43f689D8c20fB30",
        "lb_factory": "0x8e42f2F4101563bF679975178e880FD87d3eFd4e",
        "legacy_router": "0xbeE5Bc4f2d8489a57521D88C19D8c2B10Cd87c8C",
        "enabled": True
    },
    
    # Zyberswap
    "zyberswap": {
        "router": "0x16e71B13fE6079B4312063F7E81F76d165Ad32Ad",
        "factory": "0x9C2ABD632771b433E5E7507BcaA41cA3b25D8544",
        "enabled": True
    },
    
    # Ramses Exchange
    "ramses": {
        "router": "0xAAA87963EFeB6f7E0a2711F397663105Acb1805e",
        "factory": "0xAAA20D08e59F6561f242b08513D36266C5A29415",
        "enabled": True
    },
    
    # Chronos
    "chronos": {
        "router": "0xE708aA9E887980750C040a6A2Cb901c37Aa34f3b",
        "factory": "0xCe9240869391928253Ed9cc9Bcb8cb98CB5B0722",
        "enabled": False
    }
}

# ========== 代币配置 ==========
TOKENS = {
    # 稳定币
    "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
    "USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",  # Native USDC
    "USDC.e": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",  # Bridged USDC
    "DAI": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
    "FRAX": "0x17FC002b466eEc40DaE837Fc4bE5c67993ddBd6F",
    "MIM": "0xFEa7a6a0B346362BF88A9e4A88416B77a57D6c2A",
    "USDD": "0x680447595e8b7b3Aa1B43beB9f6098C79ac2Ab3f",
    
    # 主要资产
    "WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
    "WBTC": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f",
    "ARB": "0x912CE59144191C1204E64559FE8253a0e49E6548",
    "GMX": "0xfc5A1A6EB076a2C7aD06eD22C90d7E710E35ad0a",
    
    # DeFi代币
    "LINK": "0xf97f4df75117a78c1A5a0DBb814Af92458539FB4",
    "UNI": "0xFa7F8980b0f1E64A2062791cc3b0871572f1F7f0",
    "SUSHI": "0xd4d42F0b6DEF4CE0383636770eF773390d85c61A",
    "CRV": "0x11cDb42B0EB46D95f990BeDD4695A6e3fA034978",
    "AAVE": "0xba5DdD1f9d7F570dc94a51479a000E3BCE967196",
    
    # Layer 2 / 游戏代币
    "MAGIC": "0x539bdE0d7Dbd336b79148AA742883198BBF60342",
    "RDNT": "0x3082CC23568eA640225c2467653dB90e9250AaA0",
    "DPX": "0x6C2C06790b3E3E3c38e12Ee22F8183b37a13EE55",
    "GRAIL": "0x3d9907F9a368ad0a51Be60f7Da3b97cf940982D8",
    "JONES": "0x10393c20975cF177a3513071bC110f7962CD67da",
    
    # Meme币
    "PEPE": "0x25d887Ce7a35172C62FeBFD67a1856F20FaEbB00",
    "AIDOGE": "0x09E18590E8f76b6Cf471b3cd75fE1A1a9D2B2c2b",
    
    # 其他
    "PENDLE": "0x0c880f6761F1af8d9Aa9C466984b80DAb9a8c9e8",
    "STG": "0x6694340fc020c5E6B96567843da2df01b2CE1eb6",
    "VELA": "0x088cd8f5eF3652623c22D48b1605DCfE860Cd704",
    "GNS": "0x18c11FD286C5EC11c3b683Caa813B77f5163A122"
}

# ========== 套利参数 ==========
ARBITRAGE_PARAMS = {
    # 基础参数
    "amount_usdt": float(os.getenv("AMOUNT_USDT", "1000")),  # 套利金额(USDT)
    "min_profit_usdt": float(os.getenv("MIN_PROFIT_USDT", "1")),  # 最小利润(USDT)
    "max_slippage_bps": int(os.getenv("MAX_SLIPPAGE_BPS", "50")),  # 最大滑点(基点)
    
    # 高级参数
    "max_hops": int(os.getenv("MAX_HOPS", "4")),  # 最大跳数
    "enable_triangular": os.getenv("ENABLE_TRIANGULAR", "true").lower() == "true",
    "enable_multi_hop": os.getenv("ENABLE_MULTI_HOP", "true").lower() == "true",
    "enable_cross_dex": os.getenv("ENABLE_CROSS_DEX", "true").lower() == "true",
    "enable_flash_loan": os.getenv("ENABLE_FLASH_LOAN", "false").lower() == "true",
    
    # 扫描参数
    "scan_interval": float(os.getenv("SCAN_INTERVAL", "0.5")),  # 扫描间隔(秒)
    "max_concurrent_scans": int(os.getenv("MAX_CONCURRENT_SCANS", "10")),
    "price_cache_ttl": int(os.getenv("PRICE_CACHE_TTL", "1")),  # 价格缓存时间(秒)
    
    # Gas参数
    "max_gas_price_gwei": int(os.getenv("MAX_GAS_PRICE_GWEI", "100")),
    "gas_multiplier": float(os.getenv("GAS_MULTIPLIER", "1.2")),
    "estimated_gas_per_swap": int(os.getenv("ESTIMATED_GAS_PER_SWAP", "200000"))
}

# ========== 闪电贷配置 ==========
FLASH_LOAN_PROVIDERS = {
    "aave_v3": {
        "pool": "0x794a61358D6845594F94dc1DB02A252b5b4814aD",
        "fee_bps": 9,  # 0.09%
        "enabled": True
    },
    "balancer": {
        "vault": "0xBA12222222228d8Ba445958a75a0704d566BF2C8",
        "fee_bps": 0,  # 无费用
        "enabled": True
    },
    "radiant": {
        "pool": "0xF4B1486DD74D07706052A33d31d7c0AAFD0659E1",
        "fee_bps": 9,  # 0.09%
        "enabled": False
    }
}

# ========== MEV保护配置 ==========
MEV_PROTECTION = {
    "enabled": os.getenv("ENABLE_MEV_PROTECTION", "true").lower() == "true",
    "use_flashbots": os.getenv("USE_FLASHBOTS", "false").lower() == "true",
    "min_profit_for_private_tx": float(os.getenv("MIN_PROFIT_PRIVATE_TX", "10")),  # USDT
    "gas_price_multiplier": float(os.getenv("MEV_GAS_MULTIPLIER", "1.5")),
    "monitor_mempool": os.getenv("MONITOR_MEMPOOL", "true").lower() == "true"
}

# ========== 监控和通知 ==========
MONITORING = {
    # 日志配置
    "log_level": os.getenv("LOG_LEVEL", "INFO"),
    "log_file": os.getenv("LOG_FILE", "./logs/arbitrage_enhanced.log"),
    "verbose": os.getenv("VERBOSE", "true").lower() == "true",
    
    # 数据存储
    "data_dir": os.getenv("DATA_DIR", "./data"),
    "save_opportunities": os.getenv("SAVE_OPPORTUNITIES", "true").lower() == "true",
    "max_opportunities_stored": int(os.getenv("MAX_OPPORTUNITIES_STORED", "10000")),
    
    # Telegram通知
    "telegram_enabled": os.getenv("TELEGRAM_ENABLED", "false").lower() == "true",
    "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
    "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
    "telegram_min_profit": float(os.getenv("TELEGRAM_MIN_PROFIT", "10")),  # 最小通知利润
    
    # Discord通知
    "discord_enabled": os.getenv("DISCORD_ENABLED", "false").lower() == "true",
    "discord_webhook": os.getenv("DISCORD_WEBHOOK", ""),
    
    # 统计显示
    "stats_interval": int(os.getenv("STATS_INTERVAL", "20")),  # 每N次扫描显示统计
    "display_top_opportunities": int(os.getenv("DISPLAY_TOP_OPPS", "3"))  # 显示前N个机会
}

# ========== 安全配置 ==========
SECURITY = {
    # 白名单
    "token_whitelist_only": os.getenv("TOKEN_WHITELIST_ONLY", "true").lower() == "true",
    "dex_whitelist_only": os.getenv("DEX_WHITELIST_ONLY", "true").lower() == "true",
    
    # 限制
    "max_position_size": float(os.getenv("MAX_POSITION_SIZE", "10000")),  # 最大持仓(USDT)
    "max_daily_trades": int(os.getenv("MAX_DAILY_TRADES", "100")),
    "max_gas_per_tx": int(os.getenv("MAX_GAS_PER_TX", "1000000")),
    
    # 风控
    "stop_loss_pct": float(os.getenv("STOP_LOSS_PCT", "5")),  # 止损百分比
    "circuit_breaker_enabled": os.getenv("CIRCUIT_BREAKER", "true").lower() == "true",
    "max_consecutive_failures": int(os.getenv("MAX_FAILURES", "5"))
}

# ========== 优化配置 ==========
OPTIMIZATION = {
    # 路径优化
    "use_graph_optimization": os.getenv("USE_GRAPH_OPT", "true").lower() == "true",
    "max_paths_per_pair": int(os.getenv("MAX_PATHS_PER_PAIR", "10")),
    "prune_unprofitable_paths": os.getenv("PRUNE_PATHS", "true").lower() == "true",
    
    # 缓存优化
    "use_price_cache": os.getenv("USE_PRICE_CACHE", "true").lower() == "true",
    "use_liquidity_cache": os.getenv("USE_LIQUIDITY_CACHE", "true").lower() == "true",
    "cache_size_mb": int(os.getenv("CACHE_SIZE_MB", "100")),
    
    # 并发优化
    "use_async": os.getenv("USE_ASYNC", "true").lower() == "true",
    "thread_pool_size": int(os.getenv("THREAD_POOL_SIZE", "10")),
    "async_batch_size": int(os.getenv("ASYNC_BATCH_SIZE", "20"))
}

# ========== 实验性功能 ==========
EXPERIMENTAL = {
    # AI/ML功能
    "use_ml_predictions": os.getenv("USE_ML", "false").lower() == "true",
    "ml_model_path": os.getenv("ML_MODEL_PATH", "./models/arbitrage_predictor.pkl"),
    
    # 跨链套利
    "enable_cross_chain": os.getenv("ENABLE_CROSS_CHAIN", "false").lower() == "true",
    "bridge_contracts": {},
    
    # 期权套利
    "enable_options": os.getenv("ENABLE_OPTIONS", "false").lower() == "true",
    "options_protocols": ["dopex", "jones_dao"],
    
    # 自动做市商
    "enable_amm_lp": os.getenv("ENABLE_AMM_LP", "false").lower() == "true",
    "lp_strategies": ["impermanent_loss_hedge", "fee_farming"]
}

# ========== 辅助函数 ==========
def get_web3_instance(url=None):
    """获取Web3实例"""
    if url is None:
        url = RPC_URLS["primary"]
    return Web3(Web3.HTTPProvider(url))

def get_enabled_dexes():
    """获取启用的DEX列表"""
    return [name for name, config in DEX_CONFIGS.items() if config.get("enabled", False)]

def get_token_address(symbol):
    """根据符号获取代币地址"""
    return TOKENS.get(symbol.upper())

def get_token_symbol(address):
    """根据地址获取代币符号"""
    address = Web3.to_checksum_address(address)
    for symbol, addr in TOKENS.items():
        if Web3.to_checksum_address(addr) == address:
            return symbol
    return None

def validate_config():
    """验证配置"""
    errors = []
    
    # 检查RPC连接
    try:
        w3 = get_web3_instance()
        if not w3.is_connected():
            errors.append("无法连接到主RPC节点")
    except Exception as e:
        errors.append(f"RPC连接错误: {e}")
    
    # 检查必要参数
    if ARBITRAGE_PARAMS["amount_usdt"] <= 0:
        errors.append("套利金额必须大于0")
    
    if ARBITRAGE_PARAMS["min_profit_usdt"] <= 0:
        errors.append("最小利润必须大于0")
    
    # 检查DEX配置
    enabled_dexes = get_enabled_dexes()
    if len(enabled_dexes) < 2:
        errors.append("至少需要启用2个DEX")
    
    return len(errors) == 0, errors

# ========== 导出配置 ==========
__all__ = [
    'RPC_URLS',
    'DEX_CONFIGS',
    'TOKENS',
    'ARBITRAGE_PARAMS',
    'FLASH_LOAN_PROVIDERS',
    'MEV_PROTECTION',
    'MONITORING',
    'SECURITY',
    'OPTIMIZATION',
    'EXPERIMENTAL',
    'get_web3_instance',
    'get_enabled_dexes',
    'get_token_address',
    'get_token_symbol',
    'validate_config'
]