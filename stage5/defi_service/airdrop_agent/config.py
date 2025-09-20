"""配置文件管理模块"""
import os
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class NetworkConfig(BaseModel):
    """网络配置"""
    name: str
    rpc_url: str
    chain_id: int
    native_token: str = "ETH"
    block_explorer: str = ""

class WalletConfig(BaseModel):
    """钱包配置"""
    private_keys: List[str] = Field(default_factory=list)
    addresses: List[str] = Field(default_factory=list)
    min_balance: float = 0.01  # 最小余额要求

class AirdropConfig(BaseModel):
    """空投配置"""
    enabled_sources: List[str] = Field(default_factory=lambda: ["coingecko", "defillama", "twitter"])
    check_interval: int = 3600  # 检查间隔(秒)
    max_gas_price: int = 50  # 最大gas价格(gwei)
    min_profit_threshold: float = 10.0  # 最小收益阈值(USD)
    auto_execute: bool = False  # 是否自动执行

class SeleniumConfig(BaseModel):
    """Selenium配置"""
    headless: bool = True
    user_data_dir: str = "./chrome_data"
    driver_path: str = "./chromedriver"
    page_load_timeout: int = 30
    implicit_wait: int = 10

class Config(BaseModel):
    """主配置类"""
    networks: Dict[str, NetworkConfig] = Field(default_factory=dict)
    wallets: WalletConfig = Field(default_factory=WalletConfig)
    airdrop: AirdropConfig = Field(default_factory=AirdropConfig)
    selenium: SeleniumConfig = Field(default_factory=SeleniumConfig)
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置"""
        config = cls()
        
        # 网络配置
        config.networks = {
            "ethereum": NetworkConfig(
                name="Ethereum",
                rpc_url=os.getenv("ETH_RPC_URL", "https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY"),
                chain_id=1,
                block_explorer="https://etherscan.io"
            ),
            "bsc": NetworkConfig(
                name="Binance Smart Chain",
                rpc_url=os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org/"),
                chain_id=56,
                block_explorer="https://bscscan.com"
            ),
            "polygon": NetworkConfig(
                name="Polygon",
                rpc_url=os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com"),
                chain_id=137,
                block_explorer="https://polygonscan.com"
            ),
            "arbitrum": NetworkConfig(
                name="Arbitrum",
                rpc_url=os.getenv("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc"),
                chain_id=42161,
                block_explorer="https://arbiscan.io"
            ),
            "optimism": NetworkConfig(
                name="Optimism",
                rpc_url=os.getenv("OPTIMISM_RPC_URL", "https://mainnet.optimism.io"),
                chain_id=10,
                block_explorer="https://optimistic.etherscan.io"
            )
        }
        
        # 钱包配置
        private_keys_str = os.getenv("PRIVATE_KEYS", "")
        if private_keys_str:
            config.wallets.private_keys = [key.strip() for key in private_keys_str.split(",") if key.strip()]
        
        addresses_str = os.getenv("WALLET_ADDRESSES", "")
        if addresses_str:
            config.wallets.addresses = [addr.strip() for addr in addresses_str.split(",") if addr.strip()]
        
        # 空投配置
        config.airdrop.check_interval = int(os.getenv("CHECK_INTERVAL", "3600"))
        config.airdrop.max_gas_price = int(os.getenv("MAX_GAS_PRICE", "50"))
        config.airdrop.min_profit_threshold = float(os.getenv("MIN_PROFIT_THRESHOLD", "10.0"))
        config.airdrop.auto_execute = os.getenv("AUTO_EXECUTE", "false").lower() == "true"
        
        return config

# 全局配置实例
config = Config.from_env()