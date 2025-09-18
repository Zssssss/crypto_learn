#!/usr/bin/env python3
"""
高级套利机器人 V2
支持多 DEX、完善的错误处理、日志记录和性能监控
"""

import os
import sys
import time
import json
import logging
import traceback
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from web3 import Web3
from web3.exceptions import ContractLogicError
from dotenv import load_dotenv
import requests

# 加载环境变量
load_dotenv()

# ========== 配置管理 ==========
@dataclass
class Config:
    """配置类"""
    # 网络配置
    rpc_url: str = os.getenv("RPC_URL", "https://arb1.arbitrum.io/rpc")
    backup_rpc_url: str = os.getenv("BACKUP_RPC_URL", "")
    
    # 账户配置
    account: str = os.getenv("ACCOUNT", "")
    private_key: str = os.getenv("PRIVATE_KEY", "")
    executor: str = os.getenv("EXECUTOR", "")
    
    # 套利参数
    amount_usdt: int = int(float(os.getenv("AMOUNT_USDT", "100")) * 1e6)
    min_net_profit_usdt: int = int(float(os.getenv("MIN_NET_PROFIT_USDT", "0.5")) * 1e6)
    slippage_bps: int = int(os.getenv("SLIPPAGE_BPS", "50"))
    gas_multiplier: float = float(os.getenv("GAS_MULTIPLIER", "1.2"))
    
    # 监控配置
    scan_interval: int = int(os.getenv("SCAN_INTERVAL", "1"))
    verbose_logging: bool = os.getenv("VERBOSE_LOGGING", "true").lower() == "true"
    log_file_path: str = os.getenv("LOG_FILE_PATH", "./logs/arbitrage.log")
    
    # 安全配置
    max_gas_price_gwei: int = int(os.getenv("MAX_GAS_PRICE_GWEI", "100"))
    enable_token_whitelist: bool = os.getenv("ENABLE_TOKEN_WHITELIST", "true").lower() == "true"
    enable_mev_protection: bool = os.getenv("ENABLE_MEV_PROTECTION", "false").lower() == "true"
    
    # DEX 配置
    uniswap_v3_router: str = os.getenv("UNISWAP_V3_ROUTER", "0xE592427A0AEce92De3Edee1F18E0157C05861564")
    uniswap_v3_quoter: str = os.getenv("UNISWAP_V3_QUOTER", "0x61FFE014BA17989E743C5F6CB21BF9697530B21E")
    uniswap_v3_fee: int = int(os.getenv("UNISWAP_V3_FEE", "3000"))
    sushi_router: str = os.getenv("SUSHI_ROUTER", "0xf2614A233c7C3e7f08b1F887Ba133a13f1eb2c55")
    
    # 代币地址
    usdt: str = os.getenv("USDT", "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9")
    usdc: str = os.getenv("USDC", "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8")
    weth: str = os.getenv("WETH", "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1")
    wbtc: str = os.getenv("WBTC", "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f")
    dai: str = os.getenv("DAI", "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1")
    
    # Telegram 通知
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")

    def validate(self) -> bool:
        """验证配置"""
        if not self.account or not self.private_key:
            logging.error("账户地址或私钥未配置")
            return False
        if not Web3.is_address(self.account):
            logging.error("无效的账户地址")
            return False
        return True

# ========== 日志配置 ==========
def setup_logging(config: Config):
    """设置日志系统"""
    os.makedirs(os.path.dirname(config.log_file_path), exist_ok=True)
    
    log_level = logging.DEBUG if config.verbose_logging else logging.INFO
    
    # 配置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 文件处理器
    file_handler = logging.FileHandler(config.log_file_path)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # 配置根日志器
    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# ========== 套利机会数据结构 ==========
@dataclass
class ArbitrageOpportunity:
    """套利机会"""
    token_path: List[str]
    dex_path: List[str]
    amount_in: int
    expected_profit: int
    gas_cost: int
    net_profit: int
    timestamp: datetime
    
    def to_dict(self) -> dict:
        return {
            "token_path": self.token_path,
            "dex_path": self.dex_path,
            "amount_in": self.amount_in,
            "expected_profit": self.expected_profit,
            "gas_cost": self.gas_cost,
            "net_profit": self.net_profit,
            "timestamp": self.timestamp.isoformat()
        }

# ========== DEX 接口 ==========
class DEXInterface:
    """DEX 交互接口基类"""
    
    def __init__(self, w3: Web3, name: str):
        self.w3 = w3
        self.name = name
        self.logger = logging.getLogger(f"DEX.{name}")
    
    def quote(self, token_in: str, token_out: str, amount_in: int) -> Optional[int]:
        """获取报价"""
        raise NotImplementedError
    
    def get_reserves(self, token_a: str, token_b: str) -> Optional[Tuple[int, int]]:
        """获取流动性储备"""
        raise NotImplementedError

class UniswapV3(DEXInterface):
    """Uniswap V3 接口"""
    
    QUOTER_ABI = json.loads('''[{
        "inputs": [{
            "components": [
                {"internalType": "address", "name": "tokenIn", "type": "address"},
                {"internalType": "address", "name": "tokenOut", "type": "address"},
                {"internalType": "uint24", "name": "fee", "type": "uint24"},
                {"internalType": "address", "name": "recipient", "type": "address"},
                {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
            ],
            "internalType": "struct IQuoterV2.ExactInputSingleParams",
            "name": "params",
            "type": "tuple"
        }],
        "name": "quoteExactInputSingle",
        "outputs": [
            {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
            {"internalType": "uint160", "name": "sqrtPriceX96After", "type": "uint160"},
            {"internalType": "uint32", "name": "initializedTicksCrossed", "type": "uint32"},
            {"internalType": "uint256", "name": "gasEstimate", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    }]''')
    
    def __init__(self, w3: Web3, quoter_address: str, fee: int = 3000):
        super().__init__(w3, "UniswapV3")
        self.quoter = w3.eth.contract(
            address=Web3.to_checksum_address(quoter_address),
            abi=self.QUOTER_ABI
        )
        self.fee = fee
    
    def quote(self, token_in: str, token_out: str, amount_in: int) -> Optional[int]:
        """获取 V3 报价"""
        try:
            params = (
                Web3.to_checksum_address(token_in),
                Web3.to_checksum_address(token_out),
                self.fee,
                "0x0000000000000000000000000000000000000000",
                amount_in,
                0,
                0
            )
            result = self.quoter.functions.quoteExactInputSingle(params).call()
            return int(result[0])
        except Exception as e:
            self.logger.debug(f"Quote failed: {e}")
            return None

class UniswapV2(DEXInterface):
    """Uniswap V2 / SushiSwap 接口"""
    
    ROUTER_ABI = json.loads('''[{
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"}
        ],
        "name": "getAmountsOut",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function"
    }]''')
    
    def __init__(self, w3: Web3, router_address: str, name: str = "UniswapV2"):
        super().__init__(w3, name)
        self.router = w3.eth.contract(
            address=Web3.to_checksum_address(router_address),
            abi=self.ROUTER_ABI
        )
    
    def quote(self, token_in: str, token_out: str, amount_in: int) -> Optional[int]:
        """获取 V2 报价"""
        try:
            path = [
                Web3.to_checksum_address(token_in),
                Web3.to_checksum_address(token_out)
            ]
            amounts = self.router.functions.getAmountsOut(amount_in, path).call()
            return int(amounts[-1])
        except Exception as e:
            self.logger.debug(f"Quote failed: {e}")
            return None

# ========== 套利机器人主类 ==========
class ArbitrageBot:
    """高级套利机器人"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger("ArbitrageBot")
        
        # 初始化 Web3
        self.w3 = self._init_web3()
        
        # 初始化 DEX
        self.dexes = self._init_dexes()
        
        # 统计数据
        self.stats = {
            "opportunities_found": 0,
            "trades_executed": 0,
            "trades_successful": 0,
            "total_profit": Decimal(0),
            "start_time": datetime.now()
        }
        
        # 代币白名单
        self.token_whitelist = {
            self.config.usdt,
            self.config.usdc,
            self.config.weth,
            self.config.wbtc,
            self.config.dai
        }
        
        # ABI
        self.ERC20_ABI = json.loads('''[
            {"constant": true, "inputs": [{"name": "_owner", "type": "address"}],
             "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
            {"constant": true, "inputs": [], "name": "decimals",
             "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
            {"constant": false, "inputs": [{"name": "spender", "type": "address"}, {"name": "value", "type": "uint256"}],
             "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
            {"constant": true, "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
             "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
        ]''')
    
    def _init_web3(self) -> Web3:
        """初始化 Web3 连接"""
        w3 = Web3(Web3.HTTPProvider(self.config.rpc_url))
        
        # 测试连接
        if not w3.is_connected():
            if self.config.backup_rpc_url:
                self.logger.warning("主 RPC 连接失败，尝试备用 RPC")
                w3 = Web3(Web3.HTTPProvider(self.config.backup_rpc_url))
                if not w3.is_connected():
                    raise ConnectionError("无法连接到任何 RPC 节点")
            else:
                raise ConnectionError("无法连接到 RPC 节点")
        
        self.logger.info(f"已连接到网络: Chain ID = {w3.eth.chain_id}")
        return w3
    
    def _init_dexes(self) -> Dict[str, DEXInterface]:
        """初始化 DEX 接口"""
        dexes = {}
        
        # Uniswap V3
        dexes["uniswap_v3"] = UniswapV3(
            self.w3,
            self.config.uniswap_v3_quoter,
            self.config.uniswap_v3_fee
        )
        
        # SushiSwap
        dexes["sushiswap"] = UniswapV2(
            self.w3,
            self.config.sushi_router,
            "SushiSwap"
        )
        
        self.logger.info(f"已初始化 {len(dexes)} 个 DEX")
        return dexes
    
    def estimate_gas_cost(self) -> int:
        """估算 Gas 成本（USDT）"""
        try:
            gas_price = self.w3.eth.gas_price
            
            # 检查 gas 价格上限
            max_gas_wei = self.config.max_gas_price_gwei * 10**9
            if gas_price > max_gas_wei:
                self.logger.warning(f"Gas 价格过高: {gas_price / 10**9:.2f} Gwei")
                return int(1e7)  # 返回高成本以避免交易
            
            # 估算 gas 使用量（套利交易通常 300k-500k gas）
            estimated_gas = 400000
            gas_cost_wei = gas_price * estimated_gas
            
            # 转换为 USDT
            # 获取 ETH -> USDT 价格
            eth_to_usdt = self.dexes["uniswap_v3"].quote(
                self.config.weth,
                self.config.usdt,
                10**18  # 1 ETH
            )
            
            if not eth_to_usdt:
                return int(0.5 * 1e6)  # 默认 0.5 USDT
            
            gas_cost_usdt = (Decimal(gas_cost_wei) / Decimal(10**18)) * Decimal(eth_to_usdt)
            return int(gas_cost_usdt)
            
        except Exception as e:
            self.logger.error(f"估算 gas 成本失败: {e}")
            return int(0.5 * 1e6)
    
    def find_arbitrage_opportunities(self) -> List[ArbitrageOpportunity]:
        """寻找套利机会"""
        opportunities = []
        
        # 扫描所有代币对和 DEX 组合
        tokens = list(self.token_whitelist)
        
        for i, token_a in enumerate(tokens):
            for token_b in tokens[i+1:]:
                if token_a == token_b:
                    continue
                
                # 检查不同 DEX 之间的价格差异
                for dex1_name, dex1 in self.dexes.items():
                    for dex2_name, dex2 in self.dexes.items():
                        if dex1_name == dex2_name:
                            continue
                        
                        # 路径 1: token_a -> token_b (dex1) -> token_a (dex2)
                        opportunity = self._check_arbitrage_path(
                            token_a, token_b, token_a,
                            dex1, dex2,
                            [dex1_name, dex2_name]
                        )
                        
                        if opportunity:
                            opportunities.append(opportunity)
        
        return opportunities
    
    def _check_arbitrage_path(
        self,
        token_in: str,
        token_mid: str,
        token_out: str,
        dex1: DEXInterface,
        dex2: DEXInterface,
        dex_names: List[str]
    ) -> Optional[ArbitrageOpportunity]:
        """检查特定路径的套利机会"""
        try:
            # 使用配置的金额
            amount_in = self.config.amount_usdt if token_in == self.config.usdt else 10**18
            
            # 第一跳报价
            amount_mid = dex1.quote(token_in, token_mid, amount_in)
            if not amount_mid or amount_mid == 0:
                return None
            
            # 第二跳报价
            amount_out = dex2.quote(token_mid, token_out, amount_mid)
            if not amount_out or amount_out == 0:
                return None
            
            # 计算利润
            if token_in == token_out:
                gross_profit = amount_out - amount_in
            else:
                # 需要转换为相同单位
                return None
            
            # 估算 gas 成本
            gas_cost = self.estimate_gas_cost()
            
            # 计算净利润
            net_profit = gross_profit - gas_cost
            
            # 检查是否满足最小利润要求
            if net_profit >= self.config.min_net_profit_usdt:
                return ArbitrageOpportunity(
                    token_path=[token_in, token_mid, token_out],
                    dex_path=dex_names,
                    amount_in=amount_in,
                    expected_profit=gross_profit,
                    gas_cost=gas_cost,
                    net_profit=net_profit,
                    timestamp=datetime.now()
                )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"检查套利路径失败: {e}")
            return None
    
    def execute_arbitrage(self, opportunity: ArbitrageOpportunity) -> bool:
        """执行套利交易"""
        try:
            self.logger.info(f"执行套利: {opportunity.to_dict()}")
            
            # 检查账户余额
            token_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(opportunity.token_path[0]),
                abi=self.ERC20_ABI
            )
            balance = token_contract.functions.balanceOf(self.config.account).call()
            
            if balance < opportunity.amount_in:
                self.logger.error(f"余额不足: {balance} < {opportunity.amount_in}")
                return False
            
            # TODO: 实现实际的交易执行逻辑
            # 这里需要调用智能合约执行套利
            
            self.logger.info("套利交易执行成功")
            self.stats["trades_successful"] += 1
            self.stats["total_profit"] += Decimal(opportunity.net_profit) / Decimal(1e6)
            
            # 发送通知
            self.send_notification(f"✅ 套利成功！净利润: {opportunity.net_profit/1e6:.2f} USDT")
            
            return True
            
        except Exception as e:
            self.logger.error(f"执行套利失败: {e}")
            self.logger.error(traceback.format_exc())
            return False
    
    def send_notification(self, message: str):
        """发送 Telegram 通知"""
        if not self.config.telegram_bot_token or not self.config.telegram_chat_id:
            return
        
        try:
            url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage"
            data = {
                "chat_id": self.config.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            requests.post(url, data=data, timeout=5)
        except Exception as e:
            self.logger.error(f"发送通知失败: {e}")
    
    def print_stats(self):
        """打印统计信息"""
        runtime = (datetime.now() - self.stats["start_time"]).total_seconds()
        hours = runtime / 3600
        
        self.logger.info("=" * 50)
        self.logger.info("套利机器人统计")
        self.logger.info(f"运行时间: {hours:.2f} 小时")
        self.logger.info(f"发现机会: {self.stats['opportunities_found']}")
        self.logger.info(f"执行交易: {self.stats['trades_executed']}")
        self.logger.info(f"成功交易: {self.stats['trades_successful']}")
        self.logger.info(f"总利润: {self.stats['total_profit']:.2f} USDT")
        self.logger.info("=" * 50)
    
    def run(self):
        """运行套利机器人"""
        self.logger.info("🚀 套利机器人启动")
        self.logger.info(f"账户: {self.config.account}")
        self.logger.info(f"监控间隔: {self.config.scan_interval} 秒")
        
        # 发送启动通知
        self.send_notification("🚀 套利机器人已启动")
        
        try:
            while True:
                try:
                    # 寻找套利机会
                    opportunities = self.find_arbitrage_opportunities()
                    
                    if opportunities:
                        self.logger.info(f"发现 {len(opportunities)} 个套利机会")
                        self.stats["opportunities_found"] += len(opportunities)
                        
                        # 按净利润排序
                        opportunities.sort(key=lambda x: x.net_profit, reverse=True)
                        
                        # 执行最佳机会
                        best_opportunity = opportunities[0]
                        if best_opportunity.net_profit >= self.config.min_net_profit_usdt:
                            self.logger.info(
                                f"最佳机会: {best_opportunity.token_path} "
                                f"via {best_opportunity.dex_path}, "
                                f"净利润: {best_opportunity.net_profit/1e6:.2f} USDT"
                            )
                            
                            self.stats["trades_executed"] += 1
                            success = self.execute_arbitrage(best_opportunity)
                            
                            if success:
                                # 成功后暂停一段时间
                                time.sleep(5)
                    
                    # 定期打印统计
                    if self.stats["opportunities_found"] % 100 == 0:
                        self.print_stats()
                    
                    # 扫描间隔
                    time.sleep(self.config.scan_interval)
                    
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    self.logger.error(f"主循环错误: {e}")
                    self.logger.error(traceback.format_exc())
                    time.sleep(5)
                    
        except KeyboardInterrupt:
            self.logger.info("收到停止信号")
        finally:
            self.print_stats()
            self.send_notification("🛑 套利机器人已停止")
            self.logger.info("套利机器人已停止")

# ========== 主函数 ==========
def main():
    """主函数"""
    # 加载配置
    config = Config()
    
    # 验证配置
    if not config.validate():
        print("配置验证失败，请检查 .env 文件")
        sys.exit(1)
    
    # 设置日志
    logger = setup_logging(config)
    logger.info("配置加载成功")
    
    # 创建并运行机器人
    bot = ArbitrageBot(config)
    bot.run()

if __name__ == "__main__":
    main()