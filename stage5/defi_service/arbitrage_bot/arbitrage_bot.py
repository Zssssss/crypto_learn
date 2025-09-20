
#!/usr/bin/env python3
"""
增强版套利机器人 V4
支持更多DEX、三角套利、多跳套利、闪电贷等高级功能
"""

import os
import sys
import sys
import time
import json
import logging
import traceback
import asyncio
import aiohttp
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, asdict, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque, defaultdict
import threading
from web3 import Web3
from web3.exceptions import ContractLogicError
from dotenv import load_dotenv
import requests
import pandas as pd
import numpy as np
from itertools import combinations, permutations

# 加载环境变量
# 加载环境变量
load_dotenv()

# ========== 增强配置管理 ==========
@dataclass
class EnhancedConfig:
    """增强配置类"""
    # 网络配置
    rpc_url: str = os.getenv("RPC_URL", "https://arb1.arbitrum.io/rpc")
    backup_rpc_urls: List[str] = field(default_factory=lambda: [
        "https://arbitrum-one.public.blastapi.io",
        "https://arb-mainnet.g.alchemy.com/v2/demo",
        "https://arbitrum.blockpi.network/v1/rpc/public"
    ])
    
    # 账户配置
    account: str = os.getenv("ACCOUNT", "")
    private_key: str = os.getenv("PRIVATE_KEY", "")
    
    # 套利参数
    amount_usdt: int = int(float(os.getenv("AMOUNT_USDT", "1000")) * 1e6)
    min_net_profit_usdt: int = int(float(os.getenv("MIN_NET_PROFIT_USDT", "1")) * 1e6)
    slippage_bps: int = int(os.getenv("SLIPPAGE_BPS", "50"))
    gas_multiplier: float = float(os.getenv("GAS_MULTIPLIER", "1.2"))
    max_hops: int = int(os.getenv("MAX_HOPS", "4"))  # 最大跳数
    
    # 监控配置
    scan_interval: int = int(os.getenv("SCAN_INTERVAL", "0.5"))  # 更快的扫描
    verbose_logging: bool = os.getenv("VERBOSE_LOGGING", "true").lower() == "true"
    enable_triangular: bool = os.getenv("ENABLE_TRIANGULAR", "true").lower() == "true"
    enable_multi_hop: bool = os.getenv("ENABLE_MULTI_HOP", "true").lower() == "true"
    enable_flash_loan: bool = os.getenv("ENABLE_FLASH_LOAN", "false").lower() == "true"
    
    # DEX 配置 - 更多DEX
    dex_configs: Dict = field(default_factory=lambda: {
        "uniswap_v3": {
            "router": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
            "quoter": "0x61FFE014BA17989E743C5F6CB21BF9697530B21E",
            "factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
            "fees": [100, 500, 3000, 10000]  # 0.01%, 0.05%, 0.3%, 1%
        },
        "sushiswap": {
            "router": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
            "factory": "0xc35DADB65012eC5796536bD9864eD8773aBc74C4"
        },
        "curve": {
            "registry": "0x445FE580eF8d70FF569aB36e80c647af338db351",
            "pools": []  # 动态加载
        },
        "balancer": {
            "vault": "0xBA12222222228d8Ba445958a75a0704d566BF2C8",
            "pools": []  # 动态加载
        },
        "gmx": {
            "router": "0xaBBc5F99639c9B6bCb58544ddf04EFA6802F4064",
            "reader": "0x22199a49A999c351eF7927602CFB187ec3cae489"
        },
        "camelot": {
            "router": "0xc873fEcbd354f5A56E00E710B90EF4201db2448d",
            "factory": "0x6EcCab422D763aC031210895C81787E87B43A652"
        },
        "traderjoe": {
            "router": "0xb4315e873dBcf96Ffd0acd8EA43f689D8c20fB30",
            "factory": "0xaE4EC9901c3076D0DdBe76A520F9E90a6227aCB7"
        }
    })
    
    # 代币配置 - 更多代币
    tokens: Dict = field(default_factory=lambda: {
        "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
        "USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",  # USDC.e
        "USDC.e": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
        "WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
        "WBTC": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f",
        "DAI": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
        "ARB": "0x912CE59144191C1204E64559FE8253a0e49E6548",
        "GMX": "0xfc5A1A6EB076a2C7aD06eD22C90d7E710E35ad0a",
        "LINK": "0xf97f4df75117a78c1A5a0DBb814Af92458539FB4",
        "UNI": "0xFa7F8980b0f1E64A2062791cc3b0871572f1F7f0",
        "FRAX": "0x17FC002b466eEc40DaE837Fc4bE5c67993ddBd6F",
        "MIM": "0xFEa7a6a0B346362BF88A9e4A88416B77a57D6c2A",
        "MAGIC": "0x539bdE0d7Dbd336b79148AA742883198BBF60342",
        "RDNT": "0x3082CC23568eA640225c2467653dB90e9250AaA0"
    })
    
    # 闪电贷配置
    flash_loan_providers: Dict = field(default_factory=lambda: {
        "aave": {
            "pool": "0x794a61358D6845594F94dc1DB02A252b5b4814aD",
            "fee": 9  # 0.09%
        },
        "balancer": {
            "vault": "0xBA12222222228d8Ba445958a75a0704d566BF2C8",
            "fee": 0  # 无费用
        }
    })

# ========== 增强DEX接口 ==========
class EnhancedDEXInterface:
    """增强DEX接口基类"""
    
    def __init__(self, w3: Web3, name: str, config: dict):
        self.w3 = w3
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"DEX.{name}")
        self.cache = {}  # 价格缓存
        self.cache_ttl = 1  # 缓存1秒
        
    async def quote_async(self, token_in: str, token_out: str, amount_in: int) -> Optional[Dict]:
        """异步获取报价"""
        raise NotImplementedError
    
    def get_liquidity(self, token_a: str, token_b: str) -> Optional[Tuple[int, int]]:
        """获取流动性"""
        raise NotImplementedError
    
    def estimate_price_impact(self, token_in: str, token_out: str, amount_in: int) -> float:
        """估算价格影响"""
        raise NotImplementedError

class CurveDEX(EnhancedDEXInterface):
    """Curve DEX接口"""
    
    REGISTRY_ABI = json.loads('''[
        {"name": "get_n_coins", "outputs": [{"type": "uint256", "name": ""}],
         "inputs": [{"type": "address", "name": "pool"}], "stateMutability": "view", "type": "function"},
        {"name": "get_coins", "outputs": [{"type": "address[8]", "name": ""}],
         "inputs": [{"type": "address", "name": "pool"}], "stateMutability": "view", "type": "function"},
        {"name": "get_dy", "outputs": [{"type": "uint256", "name": ""}],
         "inputs": [{"type": "address", "name": "pool"}, {"type": "int128", "name": "i"},
                   {"type": "int128", "name": "j"}, {"type": "uint256", "name": "dx"}],
         "stateMutability": "view", "type": "function"}
    ]''')
    
    def __init__(self, w3: Web3, config: dict):
        super().__init__(w3, "Curve", config)
        self.registry = w3.eth.contract(
            address=Web3.to_checksum_address(config["registry"]),
            abi=self.REGISTRY_ABI
        )
        self.pools = self._load_pools()
    
    def _load_pools(self) -> List[str]:
        """加载Curve池"""
        # 这里应该从链上或配置文件加载池地址
        return [
            "0x7f90122BF0700F9E7e1F688fe926940E8839F353",  # 2pool
            "0x960ea3e3C7FB317332d990873d354E18d7645590",  # tricrypto
        ]
    
    async def quote_async(self, token_in: str, token_out: str, amount_in: int) -> Optional[Dict]:
        """获取Curve报价"""
        try:
            # 查找包含这两个代币的池
            for pool in self.pools:
                coins = self.registry.functions.get_coins(pool).call()
                if token_in in coins and token_out in coins:
                    i = coins.index(token_in)
                    j = coins.index(token_out)
                    amount_out = self.registry.functions.get_dy(pool, i, j, amount_in).call()
                    
                    return {
                        "dex": self.name,
                        "pool": pool,
                        "amount_out": amount_out,
                        "price": amount_out / amount_in if amount_in > 0 else 0,
                        "liquidity": None,  # Curve不直接提供流动性
                        "fee": 4  # 0.04% 标准费用
                    }
        except Exception as e:
            self.logger.debug(f"Curve quote failed: {e}")
        return None

class BalancerDEX(EnhancedDEXInterface):
    """Balancer DEX接口"""
    
    VAULT_ABI = json.loads('''[
        {"name": "queryBatchSwap", 
         "inputs": [
            {"name": "kind", "type": "uint8"},
            {"name": "swaps", "type": "tuple[]", "components": [
                {"name": "poolId", "type": "bytes32"},
                {"name": "assetInIndex", "type": "uint256"},
                {"name": "assetOutIndex", "type": "uint256"},
                {"name": "amount", "type": "uint256"},
                {"name": "userData", "type": "bytes"}
            ]},
            {"name": "assets", "type": "address[]"},
            {"name": "funds", "type": "tuple", "components": [
                {"name": "sender", "type": "address"},
                {"name": "fromInternalBalance", "type": "bool"},
                {"name": "recipient", "type": "address"},
                {"name": "toInternalBalance", "type": "bool"}
            ]}
         ],
         "outputs": [{"name": "assetDeltas", "type": "int256[]"}],
         "stateMutability": "nonpayable", "type": "function"}
    ]''')
    
    def __init__(self, w3: Web3, config: dict):
        super().__init__(w3, "Balancer", config)
        self.vault = w3.eth.contract(
            address=Web3.to_checksum_address(config["vault"]),
            abi=self.VAULT_ABI
        )
    
    async def quote_async(self, token_in: str, token_out: str, amount_in: int) -> Optional[Dict]:
        """获取Balancer报价"""
        # 实现Balancer查询逻辑
        return None

# ========== 套利路径查找器 ==========
class ArbitragePathFinder:
    """套利路径查找器"""
    
    def __init__(self, tokens: List[str], max_hops: int = 4):
        self.tokens = tokens
        self.max_hops = max_hops
        self.logger = logging.getLogger("PathFinder")
        
    def find_triangular_paths(self, base_token: str) -> List[List[str]]:
        """查找三角套利路径"""
        paths = []
        other_tokens = [t for t in self.tokens if t != base_token]
        
        # 生成所有可能的三角路径
        for token_b, token_c in combinations(other_tokens, 2):
            # 路径1: A -> B -> C -> A
            paths.append([base_token, token_b, token_c, base_token])
            # 路径2: A -> C -> B -> A
            paths.append([base_token, token_c, token_b, base_token])
        
        return paths
    
    def find_multi_hop_paths(self, start_token: str, end_token: str) -> List[List[str]]:
        """查找多跳套利路径"""
        if start_token == end_token:
            return self.find_circular_paths(start_token)
        
        paths = []
        
        # 2跳路径
        paths.append([start_token, end_token])
        
        # 3跳路径
        for mid_token in self.tokens:
            if mid_token not in [start_token, end_token]:
                paths.append([start_token, mid_token, end_token])
        
        # 4跳路径
        if self.max_hops >= 4:
            for mid1, mid2 in combinations(self.tokens, 2):
                if mid1 not in [start_token, end_token] and mid2 not in [start_token, end_token]:
                    paths.append([start_token, mid1, mid2, end_token])
        
        return paths
    
    def find_circular_paths(self, base_token: str) -> List[List[str]]:
        """查找循环套利路径"""
        paths = []
        other_tokens = [t for t in self.tokens if t != base_token]
        
        # 2跳循环: A -> B -> A
        for token in other_tokens:
            paths.append([base_token, token, base_token])
        
        # 3跳循环: A -> B -> C -> A
        for path in permutations(other_tokens, 2):
            paths.append([base_token] + list(path) + [base_token])
        
        # 4跳循环: A -> B -> C -> D -> A
        if self.max_hops >= 4:
            for path in permutations(other_tokens, 3):
                paths.append([base_token] + list(path) + [base_token])
        
        return paths

# ========== 流动性分析器 ==========
class LiquidityAnalyzer:
    """流动性和滑点分析器"""
    
    def __init__(self, dexes: Dict[str, EnhancedDEXInterface]):
        self.dexes = dexes
        self.logger = logging.getLogger("LiquidityAnalyzer")
        self.liquidity_cache = {}
        
    def analyze_liquidity(self, token_a: str, token_b: str, dex: str) -> Dict:
        """分析流动性"""
        cache_key = f"{dex}_{token_a}_{token_b}"
        
        # 检查缓存
        if cache_key in self.liquidity_cache:
            cached_data, timestamp = self.liquidity_cache[cache_key]
            if time.time() - timestamp < 60:  # 缓存60秒
                return cached_data
        
        try:
            dex_interface = self.dexes.get(dex)
            if not dex_interface:
                return {"liquidity": 0, "depth": 0}
            
            liquidity = dex_interface.get_liquidity(token_a, token_b)
            if liquidity:
                reserve_a, reserve_b = liquidity
                total_liquidity = (reserve_a * reserve_b) ** 0.5
                
                result = {
                    "liquidity": total_liquidity,
                    "reserve_a": reserve_a,
                    "reserve_b": reserve_b,
                    "depth": min(reserve_a, reserve_b)  # 深度
                }
                
                # 更新缓存
                self.liquidity_cache[cache_key] = (result, time.time())
                return result
        except Exception as e:
            self.logger.debug(f"Liquidity analysis failed: {e}")
        
        return {"liquidity": 0, "depth": 0}
    
    def calculate_slippage(self, amount_in: int, liquidity: Dict) -> float:
        """计算滑点"""
        if not liquidity or liquidity["depth"] == 0:
            return 100.0  # 无流动性，最大滑点
        
        # 简化的滑点计算
        impact = (amount_in / liquidity["depth"]) * 100
        return min(impact, 100.0)

# ========== MEV保护 ==========
class MEVProtection:
    """MEV保护和抢先交易检测"""
    
    def __init__(self, w3: Web3):
        self.w3 = w3
        self.logger = logging.getLogger("MEVProtection")
        self.mempool_txs = deque(maxlen=1000)
        self.suspicious_addresses = set()
        
    def monitor_mempool(self):
        """监控内存池"""
        try:
            # 订阅pending交易
            pending_filter = self.w3.eth.filter('pending')
            
            for tx_hash in pending_filter.get_new_entries():
                try:
                    tx = self.w3.eth.get_transaction(tx_hash)
                    self.analyze_transaction(tx)
                except:
                    pass
        except Exception as e:
            self.logger.error(f"Mempool monitoring failed: {e}")
    
    def analyze_transaction(self, tx: Dict) -> bool:
        """分析交易是否为抢先交易"""
        # 检查是否为MEV机器人
        indicators = {
            "high_gas_price": tx['gasPrice'] > self.w3.eth.gas_price * 2,
            "flashloan": self._is_flashloan(tx),
            "sandwich": self._is_sandwich_attack(tx),
            "known_bot": tx['from'] in self.suspicious_addresses
        }
        
        risk_score = sum(indicators.values())
        
        if risk_score >= 2:
            self.suspicious_addresses.add(tx['from'])
            self.logger.warning(f"Potential MEV bot detected: {tx['hash'].hex()}")
            return True
        
        return False
    
    def _is_flashloan(self, tx: Dict) -> bool:
        """检测闪电贷交易"""
        # 检查是否调用了闪电贷合约
        known_flashloan_contracts = [
            "0x794a61358D6845594F94dc1DB02A252b5b4814aD",  # AAVE
            "0xBA12222222228d8Ba445958a75a0704d566BF2C8"   # Balancer
        ]
        return tx.get('to') in known_flashloan_contracts
    
    def _is_sandwich_attack(self, tx: Dict) -> bool:
        """检测三明治攻击"""
        # 简化检测：检查是否在短时间内有相似交易
        return False
    
    def calculate_safe_gas_price(self) -> int:
        """计算安全的gas价格"""
        base_gas = self.w3.eth.gas_price
        
        # 检查最近区块的gas价格
        latest_block = self.w3.eth.get_block('latest', full_transactions=True)
        if latest_block['transactions']:
            gas_prices = [tx['gasPrice'] for tx in latest_block['transactions']]
            median_gas = sorted(gas_prices)[len(gas_prices) // 2]
            
            # 使用中位数的1.2倍作为安全价格
            return int(median_gas * 1.2)
        
        return int(base_gas * 1.2)

# ========== 闪电贷执行器 ==========
class FlashLoanExecutor:
    """闪电贷执行器"""
    
    def __init__(self, w3: Web3, config: EnhancedConfig):
        self.w3 = w3
        self.config = config
        self.logger = logging.getLogger("FlashLoan")
        
    def calculate_flash_loan_profit(self, opportunity: Dict, provider: str) -> Dict:
        """计算闪电贷利润"""
        loan_fee = self.config.flash_loan_providers[provider]["fee"]
        loan_amount = opportunity["amount_in"]
        
        # 计算费用
        fee_amount = (loan_amount * loan_fee) // 10000
        
        # 计算净利润
        gross_profit = opportunity["expected_profit"]
        net_profit = gross_profit - fee_amount - opportunity["gas_cost"]
        
        return {
            "provider": provider,
            "loan_amount": loan_amount,
            "loan_fee": fee_amount,
            "gross_profit": gross_profit,
            "net_profit": net_profit,
            "profitable": net_profit > 0
        }
    
    def find_best_provider(self, opportunity: Dict) -> Optional[str]:
        """找到最佳闪电贷提供者"""
        best_provider = None
        best_profit = 0
        
        for provider in self.config.flash_loan_providers:
            result = self.calculate_flash_loan_profit(opportunity, provider)
            if result["profitable"] and result["net_profit"] > best_profit:
                best_profit = result["net_profit"]
                best_provider = provider
        
        return best_provider

# ========== 增强套利机器人 ==========
class EnhancedArbitrageBot:
    """增强版套利机器人"""
    
    def __init__(self, config: EnhancedConfig):
        self.config = config
        self.logger = logging.getLogger("EnhancedBot")
        
        # 初始化Web3连接池
        self.w3_pool = self._init_web3_pool()
        self.w3 = self.w3_pool[0]  # 主连接
        
        # 初始化所有DEX
        self.dexes = self._init_all_dexes()
        
        # 初始化组件
        self.path_finder = ArbitragePathFinder(
            list(config.tokens.values()),
            config.max_hops
        )
        self.liquidity_analyzer = LiquidityAnalyzer(self.dexes)
        self.mev_protection = MEVProtection(self.w3)
    async def scan_cross_dex_arbitrage(self) -> List[Dict]:
        """扫描跨DEX套利机会"""
        opportunities = []
        
        # 扫描所有代币对
        tokens = list(self.config.tokens.values())
        
        for token_a, token_b in combinations(tokens[:10], 2):  # 限制代币数量
            # 获取所有DEX的价格
            prices = await self._get_all_dex_prices(token_a, token_b)
            
            # 查找价格差异
            if len(prices) >= 2:
                sorted_prices = sorted(prices, key=lambda x: x["price"])
                
                # 检查最低买入和最高卖出之间的差价
                if sorted_prices[-1]["price"] > sorted_prices[0]["price"] * 1.001:  # 0.1%以上差价
                    opportunity = self._create_cross_dex_opportunity(
                        token_a, token_b,
                        sorted_prices[0],  # 最低价买入
                        sorted_prices[-1]  # 最高价卖出
                    )
                    
                    if opportunity and opportunity["net_profit"] > self.config.min_net_profit_usdt:
                        opportunities.append(opportunity)
        
        return opportunities
    
    async def _get_all_dex_prices(self, token_a: str, token_b: str) -> List[Dict]:
        """获取所有DEX的价格"""
        prices = []
        
        # 并发获取所有DEX的报价
        tasks = []
        for dex_name, dex in self.dexes.items():
            if hasattr(dex, 'quote'):
                tasks.append(self._get_dex_price(dex_name, dex, token_a, token_b))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, dict) and result.get("price", 0) > 0:
                prices.append(result)
        
        return prices
    
    async def _get_dex_price(self, dex_name: str, dex: Any, token_a: str, token_b: str) -> Optional[Dict]:
        """获取单个DEX的价格"""
        try:
            # 使用适当的金额
            amount_in = self.config.amount_usdt if token_a == self.config.tokens["USDT"] else 10**18
            
            # 获取报价
            price_data = dex.quote(token_a, token_b, amount_in)
            
            if price_data:
                return {
                    "dex": dex_name,
                    "token_in": token_a,
                    "token_out": token_b,
                    "amount_in": amount_in,
                    "amount_out": price_data.amount_out if hasattr(price_data, 'amount_out') else price_data.get("amount_out", 0),
                    "price": price_data.price if hasattr(price_data, 'price') else price_data.get("price", 0),
                    "gas_estimate": price_data.gas_estimate if hasattr(price_data, 'gas_estimate') else 200000
                }
        except Exception as e:
            self.logger.debug(f"Failed to get price from {dex_name}: {e}")
        
        return None
    
    async def _evaluate_path(self, path: List[str], dex_combo: List[str]) -> Optional[Dict]:
        """评估套利路径"""
        try:
            total_amount_in = self.config.amount_usdt
            current_amount = total_amount_in
            prices = []
            total_gas = 0
            
            # 计算每一跳
            for i in range(len(path) - 1):
                token_in = path[i]
                token_out = path[i + 1]
                dex = dex_combo[i] if i < len(dex_combo) else "uniswap_v3"
                
                # 获取价格
                price_data = await self._get_dex_price(dex, self.dexes.get(dex), token_in, token_out)
                
                if not price_data or price_data["amount_out"] == 0:
                    return None
                
                prices.append(price_data)
                current_amount = price_data["amount_out"]
                total_gas += price_data.get("gas_estimate", 200000)
                
                # 检查流动性和滑点
                liquidity = self.liquidity_analyzer.analyze_liquidity(token_in, token_out, dex)
                slippage = self.liquidity_analyzer.calculate_slippage(current_amount, liquidity)
                
                if slippage > 5:  # 滑点超过5%
                    return None
            
            # 计算利润
            gross_profit = current_amount - total_amount_in
            gas_cost = self._estimate_gas_cost(total_gas)
            net_profit = gross_profit - gas_cost
            
            # 检查闪电贷机会
            flash_loan_info = None
            if self.config.enable_flash_loan and net_profit > 0:
                flash_loan_info = self._evaluate_flash_loan(total_amount_in, net_profit)
            
            return {
                "path": path,
                "dex_combo": dex_combo,
                "amount_in": total_amount_in,
                "amount_out": current_amount,
                "expected_profit": gross_profit,
                "gas_cost": gas_cost,
                "net_profit": net_profit,
                "profit_percentage": (net_profit / total_amount_in * 100) if total_amount_in > 0 else 0,
                "prices": prices,
                "flash_loan": flash_loan_info,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.debug(f"Path evaluation failed: {e}")
            return None
    
    def _generate_dex_combinations(self, num_hops: int) -> List[List[str]]:
        """生成DEX组合"""
        dex_names = list(self.dexes.keys())
        
        if num_hops == 1:
            return [[dex] for dex in dex_names]
        
        # 生成所有可能的DEX组合
        from itertools import product
        combos = list(product(dex_names, repeat=num_hops))
        
        # 限制组合数量，避免过多计算
        return [list(combo) for combo in combos[:20]]
    
    def _create_cross_dex_opportunity(self, token_a: str, token_b: str, 
                                     buy_price: Dict, sell_price: Dict) -> Optional[Dict]:
        """创建跨DEX套利机会"""
        try:
            # 计算套利路径
            amount_in = self.config.amount_usdt
            
            # 在低价DEX买入
            amount_mid = int(amount_in * buy_price["price"])
            
            # 在高价DEX卖出
            amount_out = int(amount_mid / sell_price["price"])
            
            # 计算利润
            gross_profit = amount_out - amount_in
            gas_cost = self._estimate_gas_cost(400000)  # 两次交换的gas
            net_profit = gross_profit - gas_cost
            
            return {
                "type": "cross_dex",
                "token_pair": [token_a, token_b],
                "buy_dex": buy_price["dex"],
                "sell_dex": sell_price["dex"],
                "amount_in": amount_in,
                "amount_out": amount_out,
                "expected_profit": gross_profit,
                "gas_cost": gas_cost,
                "net_profit": net_profit,
                "profit_percentage": (net_profit / amount_in * 100) if amount_in > 0 else 0,
                "buy_price": buy_price["price"],
                "sell_price": sell_price["price"],
                "price_diff_pct": ((sell_price["price"] - buy_price["price"]) / buy_price["price"] * 100),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.debug(f"Failed to create cross-dex opportunity: {e}")
            return None
    
    def _estimate_gas_cost(self, gas_used: int) -> int:
        """估算Gas成本（USDT）"""
        try:
            # 获取当前gas价格
            gas_price = self.mev_protection.calculate_safe_gas_price()
            
            # 计算ETH成本
            gas_cost_wei = gas_price * gas_used
            gas_cost_eth = gas_cost_wei / 10**18
            
            # 获取ETH价格（简化：使用固定价格或从DEX获取）
            eth_price_usdt = 1800  # 简化处理
            
            # 转换为USDT
            gas_cost_usdt = int(gas_cost_eth * eth_price_usdt * 1e6)
            
            return gas_cost_usdt
            
        except Exception as e:
            self.logger.error(f"Gas cost estimation failed: {e}")
            return int(0.5 * 1e6)  # 默认0.5 USDT
    
    def _evaluate_flash_loan(self, loan_amount: int, expected_profit: int) -> Optional[Dict]:
        """评估闪电贷机会"""
        best_provider = None
        best_profit = 0
        
        for provider, config in self.config.flash_loan_providers.items():
            fee = (loan_amount * config["fee"]) // 10000
            net_profit = expected_profit - fee
            
            if net_profit > best_profit:
                best_profit = net_profit
                best_provider = {
                    "provider": provider,
                    "loan_amount": loan_amount,
                    "fee": fee,
                    "net_profit": net_profit,
                    "contract": config.get("pool") or config.get("vault")
                }
        
        return best_provider if best_profit > 0 else None
    
    def display_opportunity(self, opportunity: Dict):
        """显示套利机会"""
        self.logger.info("=" * 80)
        self.logger.info("🎯 发现高级套利机会!")
        
        if opportunity.get("type") == "cross_dex":
            self.logger.info(f"类型: 跨DEX套利")
            self.logger.info(f"代币对: {self._get_token_names(opportunity['token_pair'])}")
            self.logger.info(f"买入DEX: {opportunity['buy_dex']} @ {opportunity['buy_price']:.6f}")
            self.logger.info(f"卖出DEX: {opportunity['sell_dex']} @ {opportunity['sell_price']:.6f}")
            self.logger.info(f"价差: {opportunity['price_diff_pct']:.2f}%")
        else:
            self.logger.info(f"路径: {self._get_token_names(opportunity['path'])}")
            self.logger.info(f"DEX组合: {opportunity['dex_combo']}")
        
        self.logger.info(f"投入金额: ${opportunity['amount_in']/1e6:.2f}")
        self.logger.info(f"预期输出: ${opportunity['amount_out']/1e6:.2f}")
        self.logger.info(f"毛利润: ${opportunity['expected_profit']/1e6:.2f}")
        self.logger.info(f"Gas成本: ${opportunity['gas_cost']/1e6:.2f}")
        self.logger.info(f"净利润: ${opportunity['net_profit']/1e6:.2f}")
        self.logger.info(f"利润率: {opportunity['profit_percentage']:.2f}%")
        
        if opportunity.get("flash_loan"):
            fl = opportunity["flash_loan"]
            self.logger.info(f"💡 闪电贷机会:")
            self.logger.info(f"  提供者: {fl['provider']}")
            self.logger.info(f"  贷款金额: ${fl['loan_amount']/1e6:.2f}")
            self.logger.info(f"  费用: ${fl['fee']/1e6:.2f}")
            self.logger.info(f"  净利润: ${fl['net_profit']/1e6:.2f}")
        
        self.logger.info("=" * 80)
    
    def _get_token_names(self, addresses: List[str]) -> List[str]:
        """获取代币名称"""
        token_map = {v: k for k, v in self.config.tokens.items()}
        return [token_map.get(addr, addr[-6:]) for addr in addresses]
    
    async def run_async(self):
        """异步运行主循环"""
        self.logger.info("🚀 增强版套利机器人启动")
        self.logger.info(f"监控DEX: {list(self.dexes.keys())}")
        self.logger.info(f"监控代币: {list(self.config.tokens.keys())}")
        self.logger.info(f"三角套利: {'启用' if self.config.enable_triangular else '禁用'}")
        self.logger.info(f"多跳套利: {'启用' if self.config.enable_multi_hop else '禁用'}")
        self.logger.info(f"闪电贷: {'启用' if self.config.enable_flash_loan else '禁用'}")
        
        scan_count = 0
        
        # 启动MEV监控
        if hasattr(self.mev_protection, 'monitor_mempool'):
            threading.Thread(target=self.mev_protection.monitor_mempool, daemon=True).start()
        
        while True:
            try:
                scan_count += 1
                start_time = time.time()
                
                # 扫描所有机会
                opportunities = await self.scan_all_opportunities()
                
                if opportunities:
                    # 按利润排序
                    opportunities.sort(key=lambda x: x.get("net_profit", 0), reverse=True)
                    
                    self.logger.info(f"🔍 第{scan_count}次扫描: 发现{len(opportunities)}个机会")
                    
                    # 显示最佳机会
                    for opp in opportunities[:3]:  # 显示前3个
                        self.display_opportunity(opp)
                        
                        # 记录到队列
                        self.opportunities_queue.append(opp)
                        
                        # 更新统计
                        self.stats["total_opportunities"] += 1
                        self.stats["total_profit_potential"] += opp["net_profit"] / 1e6
                    
                    # 保存数据
                    self._save_opportunities(opportunities)
                
                # 定期显示统计
                if scan_count % 20 == 0:
                    self._display_statistics()
                
                # 扫描耗时
                scan_time = time.time() - start_time
                
                # 动态调整扫描间隔
                sleep_time = max(0, self.config.scan_interval - scan_time)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Main loop error: {e}")
                self.logger.error(traceback.format_exc())
                await asyncio.sleep(5)
        
        self.logger.info("机器人已停止")
    
    def _save_opportunities(self, opportunities: List[Dict]):
        """保存套利机会"""
        try:
            filename = f"./data/opportunities_enhanced_{datetime.now().strftime('%Y%m%d')}.json"
            
            # 读取现有数据
            existing_data = []
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    existing_data = json.load(f)
            
            # 添加新数据
            existing_data.extend(opportunities)
            
            # 限制文件大小
            if len(existing_data) > 10000:
                existing_data = existing_data[-10000:]
            
            # 保存
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'w') as f:
                json.dump(existing_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save opportunities: {e}")
    
    def _display_statistics(self):
        """显示统计信息"""
        self.logger.info("=" * 80)
        self.logger.info("📊 套利机器人统计")
        self.logger.info(f"发现机会总数: {self.stats['total_opportunities']}")
        self.logger.info(f"潜在总利润: ${self.stats['total_profit_potential']:.2f}")
        
        # 分析最近的机会
        recent_opps = list(self.opportunities_queue)[-100:]
        if recent_opps:
            avg_profit = sum(o["net_profit"] for o in recent_opps) / len(recent_opps) / 1e6
            max_profit = max(o["net_profit"] for o in recent_opps) / 1e6
            
            self.logger.info(f"最近100个机会:")
            self.logger.info(f"  平均利润: ${avg_profit:.2f}")
            self.logger.info(f"  最大利润: ${max_profit:.2f}")
            
            # DEX统计
            dex_stats = defaultdict(int)
            for opp in recent_opps:
                if "dex_combo" in opp:
                    for dex in opp["dex_combo"]:
                        dex_stats[dex] += 1
                elif "buy_dex" in opp:
                    dex_stats[opp["buy_dex"]] += 1
                    dex_stats[opp["sell_dex"]] += 1
            
            if dex_stats:
                self.logger.info("DEX使用频率:")
                for dex, count in sorted(dex_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
                    self.logger.info(f"  {dex}: {count}次")
        
        self.logger.info("=" * 80)
    
    def run(self):
        """运行机器人"""
        try:
            # 设置异步事件循环
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.run_async())
        except KeyboardInterrupt:
            self.logger.info("收到停止信号")
        finally:
            self.loop.close()
            self._display_statistics()

# ========== 主函数 ==========
def main():
    """主函数"""
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('./logs/arbitrage_enhanced.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 加载配置
    config = EnhancedConfig()
    
    # 创建目录
    os.makedirs('./logs', exist_ok=True)
    os.makedirs('./data', exist_ok=True)
    
    # 创建并运行机器人
    bot = EnhancedArbitrageBot(config)
    bot.run()

if __name__ == "__main__":
    main()
        self.flash_loan_executor = FlashLoanExecutor(self.w3, config)
        
        # 统计数据
        self.stats = defaultdict(int)
        self.opportunities_queue = deque(maxlen=10000)
        
        # 启动异步事件循环
        self.loop = asyncio.new_event_loop()
        self.executor = ThreadPoolExecutor(max_workers=10)
        
    def _init_web3_pool(self) -> List[Web3]:
        """初始化Web3连接池"""
        pool = []
        
        # 主RPC
        try:
            w3 = Web3(Web3.HTTPProvider(self.config.rpc_url))
            if w3.is_connected():
                pool.append(w3)
                self.logger.info(f"Connected to main RPC: {self.config.rpc_url}")
        except:
            pass
        
        # 备用RPC
        for rpc_url in self.config.backup_rpc_urls:
            try:
                w3 = Web3(Web3.HTTPProvider(rpc_url))
                if w3.is_connected():
                    pool.append(w3)
                    self.logger.info(f"Connected to backup RPC: {rpc_url}")
            except:
                pass
        
        if not pool:
            raise ConnectionError("无法连接到任何RPC节点")
        
        return pool
    
    def _init_all_dexes(self) -> Dict[str, EnhancedDEXInterface]:
        """初始化所有DEX"""
        dexes = {}
        
        # UniswapV3
        from arbitrage_bot import UniswapV3
        dexes["uniswap_v3"] = UniswapV3(
            self.w3,
            self.config.dex_configs["uniswap_v3"]["quoter"],
            3000
        )
        
        # SushiSwap
        from arbitrage_bot import UniswapV2
        dexes["sushiswap"] = UniswapV2(
            self.w3,
            self.config.dex_configs["sushiswap"]["router"],
            "SushiSwap"
        )
        
        # Curve
        dexes["curve"] = CurveDEX(self.w3, self.config.dex_configs["curve"])
        
        # Balancer
        dexes["balancer"] = BalancerDEX(self.w3, self.config.dex_configs["balancer"])
        
        # 添加更多DEX...
        
        self.logger.info(f"Initialized {len(dexes)} DEXes")
        return dexes
    
    async def scan_all_opportunities(self) -> List[Dict]:
        """扫描所有套利机会"""
        opportunities = []
        
        # 并发扫描不同类型的套利
        tasks = []
        
        # 三角套利
        if self.config.enable_triangular:
            for base_token in list(self.config.tokens.values())[:5]:  # 限制基础代币数量
                tasks.append(self.scan_triangular_arbitrage(base_token))
        
        # 多跳套利
        if self.config.enable_multi_hop:
            tasks.append(self.scan_multi_hop_arbitrage())
        
        # DEX间套利
        tasks.append(self.scan_cross_dex_arbitrage())
        
        # 执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                opportunities.extend(result)
            elif isinstance(result, Exception):
                self.logger.error(f"Scan error: {result}")
        
        return opportunities
    
    async def scan_triangular_arbitrage(self, base_token: str) -> List[Dict]:
        """扫描三角套利机会"""
        opportunities = []
        paths = self.path_finder.find_triangular_paths(base_token)
        
        for path in paths:
            # 检查每个DEX组合
            for dex_combo in self._generate_dex_combinations(len(path) - 1):
                opportunity = await self._evaluate_path(path, dex_combo)
                if opportunity and opportunity["net_profit"] > self.config.min_net_profit_usdt:
                    opportunities.append(opportunity)
        
        return opportunities
    
    async def scan_multi_hop_arbitrage(self) -> List[Dict]:
        """扫描多跳套利机会"""
        opportunities = []
        
        # 扫描主要稳定币之间的套利
        stable_coins = ["USDT", "USDC", "USDC.e", "DAI", "FRAX"]
        
        for start_token in stable_coins:
            for end_token in stable_coins:
                if start_token != end_token:
                    start_addr = self.config.tokens.get(start_token)
                    end_addr = self.config.tokens.get(end_token)
                    
                    if start_addr and end_addr:
                        paths = self.path_finder.find_multi_hop_paths(start_addr, end_addr)
                        
                        for path in paths[:10]:  # 限制路径数量
                            for dex_combo in self._generate_dex_combinations(len(path) - 1):
                                opportunity = await self._evaluate_path(path, dex_combo)
                                if opportunity and opportunity["net_profit"] > self.config.min_net_profit_usdt:
                                    opportunities.append(opportunity)
        
        return opportunities
    
    