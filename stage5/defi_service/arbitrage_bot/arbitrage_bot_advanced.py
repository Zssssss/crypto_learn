#!/usr/bin/env python3
"""
高级版套利机器人
超低阈值检测 + 三角套利 + 多路径优化
"""

import os
import sys
import time
import json
import logging
import traceback
import asyncio
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque
from web3 import Web3
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class AdvancedConfig:
    """高级配置"""
    
    def __init__(self):
        self.rpc_url = os.getenv("RPC_URL", "https://arb1.arbitrum.io/rpc")
        self.amount_usdt = int(float(os.getenv("AMOUNT_USDT", "50")) * 1e6)  # 降低金额
        self.min_profit_usdt = int(float(os.getenv("MIN_PROFIT_USDT", "0.1")) * 1e6)  # 更低门槛
        self.scan_interval = float(os.getenv("SCAN_INTERVAL", "0.5"))  # 更快扫描
        self.min_price_diff_pct = float(os.getenv("MIN_PRICE_DIFF_PCT", "0.01"))  # 0.01%
        self.max_slippage_bps = int(os.getenv("MAX_SLIPPAGE_BPS", "200"))
        
        # 扩展DEX配置
        self.dex_configs = {
            "uniswap_v3": {
                "quoter": "0x61FFE014BA17989E743C5F6CB21BF9697530B21E",
                "router": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "enabled": True
            },
            "sushiswap": {
                "router": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
                "factory": "0xc35DADB65012eC5796536bD9864eD8773aBc74C4",
                "enabled": True
            },
            "camelot": {
                "router": "0xc873fEcbd354f5A56E00E710B90EF4201db2448d",
                "factory": "0x6EcCab422D763aC031210895C81787E87B43A652",
                "enabled": True
            },
            "traderjoe": {
                "router": "0xbeE5Bc4f2d8489a57521D88C19D8c2B10Cd87c8C",
                "factory": "0x8e42f2F4101563bF679975178e880FD87d3eFd4e",
                "enabled": True
            },
            "zyberswap": {
                "router": "0x16e71B13fE6079B4312063F7E81F76d165Ad32Ad",
                "factory": "0x9C2ABD632771b433E5E7507BcaA41cA3b25D8544",
                "enabled": True
            },
            "ramses": {
                "router": "0xAAA87963EFeB6f7E0a2711F397663105Acb1805e",
                "factory": "0xAAA20D08e59F6561f242b08513D36266C5A29415",
                "enabled": True
            }
        }
        
        # 扩展代币配置 - 包含更多稳定币和热门代币
        self.tokens = {
            # 稳定币
            "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
            "USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
            "USDC.e": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
            "DAI": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
            "FRAX": "0x17FC002b466eEc40DaE837Fc4bE5c67993ddBd6F",
            "MIM": "0xFEa7a6a0B346362BF88A9e4A88416B77a57D6c2A",
            "LUSD": "0x93b346b6BC2548dA6A1E7d98E9a421B42541425b",
            
            # 主要资产
            "WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
            "WBTC": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f",
            "ARB": "0x912CE59144191C1204E64559FE8253a0e49E6548",
            
            # DeFi代币
            "GMX": "0xfc5A1A6EB076a2C7aD06eD22C90d7E710E35ad0a",
            "LINK": "0xf97f4df75117a78c1A5a0DBb814Af92458539FB4",
            "UNI": "0xFa7F8980b0f1E64A2062791cc3b0871572f1F7f0",
            "CRV": "0x11cDb42B0EB46D95f990BeDD4695A6e3fA034978",
            "AAVE": "0xba5DdD1f9d7F570dc94a51479a000E3BCE967196",
            "SUSHI": "0xd4d42F0b6DEF4CE0383636770eF773390d85c61A",
            
            # Layer 2代币
            "MAGIC": "0x539bdE0d7Dbd336b79148AA742883198BBF60342",
            "RDNT": "0x3082CC23568eA640225c2467653dB90e9250AaA0",
            "GRAIL": "0x3d9907F9a368ad0a51Be60f7Da3b97cf940982D8",
            
            # 热门代币
            "PEPE": "0x25d887Ce7a35172C62FeBFD67a1856F20FaEbB00",
            "PENDLE": "0x0c880f6761F1af8d9Aa9C466984b80DAb9a8c9e8"
        }

class DEXInterface:
    """DEX接口基类"""
    
    def __init__(self, w3: Web3, name: str, config: dict):
        self.w3 = w3
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"DEX.{name}")
        
    def quote(self, token_in: str, token_out: str, amount_in: int) -> Optional[Dict]:
        """获取报价"""
        raise NotImplementedError

class UniswapV3DEX(DEXInterface):
    """Uniswap V3实现"""
    
    def __init__(self, w3: Web3, quoter_address: str):
        super().__init__(w3, "UniswapV3", {"quoter": quoter_address})
        
        self.fees = [100, 500, 3000, 10000]
        self.quoter = w3.eth.contract(
            address=w3.to_checksum_address(quoter_address),
            abi=[{
                "name": "quoteExactInputSingle",
                "inputs": [
                    {"name": "tokenIn", "type": "address"},
                    {"name": "tokenOut", "type": "address"},
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "fee", "type": "uint24"},
                    {"name": "sqrtPriceLimitX96", "type": "uint160"}
                ],
                "outputs": [{"name": "amountOut", "type": "uint256"}],
                "stateMutability": "view", "type": "function"
            }]
        )
    
    def quote(self, token_in: str, token_out: str, amount_in: int) -> Optional[Dict]:
        """获取最佳报价"""
        try:
            token_in_addr = self.w3.to_checksum_address(token_in)
            token_out_addr = self.w3.to_checksum_address(token_out)
            
            best_amount = 0
            best_fee = 0
            
            for fee in self.fees:
                try:
                    amount_out = self.quoter.functions.quoteExactInputSingle(
                        token_in_addr, token_out_addr, amount_in, fee, 0
                    ).call()
                    
                    if amount_out > best_amount:
                        best_amount = amount_out
                        best_fee = fee
                        
                except:
                    continue
            
            if best_amount > 0:
                return {
                    "amount_out": best_amount,
                    "price": best_amount / amount_in,
                    "fee": best_fee,
                    "gas_estimate": 180000
                }
                
        except Exception as e:
            self.logger.debug(f"UniswapV3 quote failed: {e}")
        
        return None

class UniswapV2DEX(DEXInterface):
    """Uniswap V2兼容DEX"""
    
    def __init__(self, w3: Web3, router_address: str, name: str):
        super().__init__(w3, name, {"router": router_address})
        
        self.router = w3.eth.contract(
            address=w3.to_checksum_address(router_address),
            abi=[{
                "name": "getAmountsOut",
                "inputs": [
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "path", "type": "address[]"}
                ],
                "outputs": [{"name": "amounts", "type": "uint256[]"}],
                "stateMutability": "view", "type": "function"
            }]
        )
    
    def quote(self, token_in: str, token_out: str, amount_in: int) -> Optional[Dict]:
        """获取报价"""
        try:
            path = [self.w3.to_checksum_address(token_in), self.w3.to_checksum_address(token_out)]
            amounts = self.router.functions.getAmountsOut(amount_in, path).call()
            
            if len(amounts) >= 2 and amounts[-1] > 0:
                return {
                    "amount_out": amounts[-1],
                    "price": amounts[-1] / amount_in,
                    "fee": 30,
                    "gas_estimate": 150000
                }
                
        except Exception as e:
            self.logger.debug(f"{self.name} quote failed: {e}")
        
        return None

class AdvancedArbitrageBot:
    """高级套利机器人"""
    
    def __init__(self, config: AdvancedConfig):
        self.config = config
        self.logger = logging.getLogger("AdvancedArbitrageBot")
        
        # 初始化Web3
        self.w3 = Web3(Web3.HTTPProvider(config.rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError("无法连接到RPC节点")
        
        # 初始化DEX
        self.dexes = self._init_dexes()
        
        # 统计数据
        self.stats = defaultdict(int)
        self.opportunities = deque(maxlen=2000)
        self.seen_opportunities = set()
        
    def _init_dexes(self) -> Dict[str, DEXInterface]:
        """初始化所有DEX"""
        dexes = {}
        
        for name, config in self.config.dex_configs.items():
            if config["enabled"]:
                if name == "uniswap_v3":
                    dexes[name] = UniswapV3DEX(self.w3, config["quoter"])
                else:
                    dexes[name] = UniswapV2DEX(self.w3, config["router"], name.replace("_", " ").title())
        
        self.logger.info(f"Initialized {len(dexes)} DEXes: {list(dexes.keys())}")
        return dexes
    
    def generate_token_pairs(self) -> List[Tuple[str, str]]:
        """生成所有可能的代币对"""
        tokens = list(self.config.tokens.items())
        pairs = []
        
        # 创建所有可能的组合
        for i, (name1, addr1) in enumerate(tokens):
            for name2, addr2 in tokens[i+1:]:
                pairs.extend([(addr1, addr2), (addr2, addr1)])
        
        return pairs
    
    def generate_triangular_paths(self) -> List[List[str]]:
        """生成三角套利路径"""
        tokens = list(self.config.tokens.keys())
        paths = []
        
        # 生成 USDT -> Token -> Token -> USDT 路径
        usdt = self.config.tokens["USDT"]
        for token1 in ["USDC", "DAI", "WETH", "WBTC", "ARB"]:
            for token2 in ["USDC", "DAI", "WETH", "WBTC", "ARB"]:
                if token1 != token2:
                    path = [usdt, self.config.tokens[token1], self.config.tokens[token2], usdt]
                    paths.append(path)
        
        return paths
    
    async def scan_all_opportunities(self) -> List[Dict]:
        """扫描所有套利机会"""
        opportunities = []
        
        # 扫描直接套利
        direct_opps = await self.scan_direct_arbitrage()
        opportunities.extend(direct_opps)
        
        # 扫描三角套利
        triangular_opps = await self.scan_triangular_arbitrage()
        opportunities.extend(triangular_opps)
        
        return opportunities
    
    async def scan_direct_arbitrage(self) -> List[Dict]:
        """扫描直接套利"""
        opportunities = []
        pairs = self.generate_token_pairs()
        
        tasks = []
        for token_a, token_b in pairs:
            task = self._scan_direct_pair(token_a, token_b)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                opportunities.extend(result)
        
        return opportunities
    
    async def scan_triangular_arbitrage(self) -> List[Dict]:
        """扫描三角套利"""
        opportunities = []
        paths = self.generate_triangular_paths()
        
        tasks = []
        for path in paths:
            task = self._scan_triangular_path(path)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, dict):
                opportunities.append(result)
        
        return opportunities
    
    async def _scan_direct_pair(self, token_a: str, token_b: str) -> List[Dict]:
        """扫描直接代币对"""
        opportunities = []
        prices = []
        
        # 获取所有DEX的价格
        for dex_name, dex in self.dexes.items():
            try:
                price_ab = await self._get_price_async(dex, token_a, token_b)
                price_ba = await self._get_price_async(dex, token_b, token_a)
                
                if price_ab and price_ba:
                    prices.append({
                        "dex": dex_name,
                        "token_a": token_a,
                        "token_b": token_b,
                        "price_ab": price_ab["price"],
                        "price_ba": price_ba["price"],
                        "amount_out_ab": price_ab["amount_out"],
                        "amount_out_ba": price_ba["amount_out"],
                        "gas_ab": price_ab["gas_estimate"],
                        "gas_ba": price_ba["gas_estimate"]
                    })
                    
            except Exception as e:
                self.logger.debug(f"Failed to get price from {dex_name}: {e}")
        
        if len(prices) >= 2:
            opportunities.extend(self._find_direct_arbitrage(prices))
        
        return opportunities
    
    async def _scan_triangular_path(self, path: List[str]) -> Optional[Dict]:
        """扫描三角套利路径"""
        try:
            amount_in = self.config.amount_usdt
            
            # 计算三角套利
            best_profit = 0
            best_path = []
            
            for dex1_name, dex1 in self.dexes.items():
                for dex2_name, dex2 in self.dexes.items():
                    for dex3_name, dex3 in self.dexes.items():
                        try:
                            # 路径: A -> B -> C -> A
                            price1 = dex1.quote(path[0], path[1], amount_in)
                            if not price1:
                                continue
                                
                            price2 = dex2.quote(path[1], path[2], price1["amount_out"])
                            if not price2:
                                continue
                                
                            price3 = dex3.quote(path[2], path[3], price2["amount_out"])
                            if not price3:
                                continue
                            
                            final_amount = price3["amount_out"]
                            profit = final_amount - amount_in
                            
                            if profit > self.config.min_profit_usdt:
                                gas_cost = self._estimate_gas_cost(
                                    price1["gas_estimate"] + price2["gas_estimate"] + price3["gas_estimate"]
                                )
                                net_profit = profit - gas_cost
                                
                                if net_profit > 0:
                                    return {
                                        "type": "triangular",
                                        "path": [path[0], path[1], path[2], path[3]],
                                        "dexes": [dex1_name, dex2_name, dex3_name],
                                        "amount_in": amount_in,
                                        "amount_out": final_amount,
                                        "net_profit": net_profit,
                                        "profit_percentage": (net_profit / amount_in * 100),
                                        "timestamp": datetime.now().isoformat()
                                    }
                                    
                        except Exception as e:
                            continue
            
        except Exception as e:
            self.logger.debug(f"Triangular arbitrage failed: {e}")
        
        return None
    
    async def _get_price_async(self, dex: DEXInterface, token_in: str, token_out: str) -> Optional[Dict]:
        """异步获取价格"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            dex.quote, 
            token_in, 
            token_out, 
            self.config.amount_usdt
        )
    
    def _find_direct_arbitrage(self, prices: List[Dict]) -> List[Dict]:
        """寻找直接套利机会"""
        opportunities = []
        
        for i, buy_price in enumerate(prices):
            for j, sell_price in enumerate(prices):
                if i != j and buy_price["dex"] != sell_price["dex"]:
                    profit = self._calculate_direct_profit(buy_price, sell_price)
                    if profit and profit["net_profit"] > self.config.min_profit_usdt:
                        opportunities.append(profit)
        
        return opportunities
    
    def _calculate_direct_profit(self, buy_price: Dict, sell_price: Dict) -> Optional[Dict]:
        """计算直接套利利润"""
        try:
            amount_in = self.config.amount_usdt
            amount_mid = int(amount_in * buy_price["price_ab"])
            amount_out = int(amount_mid * sell_price["price_ba"])
            
            gross_profit = amount_out - amount_in
            gas_cost = self._estimate_gas_cost(buy_price["gas_ab"] + sell_price["gas_ba"])
            net_profit = gross_profit - gas_cost
            
            if net_profit > self.config.min_profit_usdt:
                token_map = {v: k for k, v in self.config.tokens.items()}
                token_names = [token_map.get(addr, addr[-6:]) for addr in [buy_price["token_a"], buy_price["token_b"]]]
                
                return {
                    "type": "direct",
                    "token_pair": token_names,
                    "buy_dex": buy_price["dex"],
                    "sell_dex": sell_price["dex"],
                    "amount_in": amount_in,
                    "amount_out": amount_out,
                    "net_profit": net_profit,
                    "profit_percentage": (net_profit / amount_in * 100),
                    "price_diff_pct": ((sell_price["price_ba"] - buy_price["price_ab"]) / buy_price["price_ab"] * 100),
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.debug(f"Direct profit calculation failed: {e}")
        
        return None
    
    def _estimate_gas_cost(self, gas_used: int) -> int:
        """优化Gas成本估算"""
        try:
            gas_price = self.w3.eth.gas_price
            gas_cost_wei = gas_price * gas_used
            gas_cost_eth = gas_cost_wei / 10**18
            
            # 使用固定ETH价格，实际应该从DEX获取
            eth_price = 1800.0
            gas_cost_usdt = int(gas_cost_eth * eth_price * 1e6)
            
            return max(gas_cost_usdt, int(0.05 * 1e6))  # 更低的最小值
            
        except Exception:
            return int(0.2 * 1e6)
    
    def _get_opportunity_key(self, opportunity: Dict) -> str:
        """生成机会的唯一标识符"""
        if opportunity["type"] == "direct":
            return f"direct_{opportunity['token_pair'][0]}_{opportunity['token_pair'][1]}_{opportunity['buy_dex']}_{opportunity['sell_dex']}"
        else:
            return f"triangular_{'_'.join(opportunity['path'])}_{'_'.join(opportunity['dexes'])}"
    
    def display_opportunity(self, opportunity: Dict):
        """显示套利机会"""
        print("=" * 70)
        print("🎯 发现新套利机会!")
        
        if opportunity["type"] == "direct":
            print(f"类型: 直接套利")
            print(f"代币对: {opportunity['token_pair'][0]}/{opportunity['token_pair'][1]}")
            print(f"买入DEX: {opportunity['buy_dex']}")
            print(f"卖出DEX: {opportunity['sell_dex']}")
        else:
            print(f"类型: 三角套利")
            print(f"路径: {' -> '.join(opportunity['path'])}")
            print(f"DEX: {' -> '.join(opportunity['dexes'])}")
        
        print(f"净利润: ${opportunity['net_profit']/1e6:.6f} USDT")
        print(f"利润率: {opportunity['profit_percentage']:.4f}%")
        print("=" * 70)
    
    async def run_async(self):
        """异步运行主循环"""
        self.logger.info("🚀 高级套利机器人启动")
        self.logger.info(f"监控DEX: {list(self.dexes.keys())}")
        self.logger.info(f"监控代币: {len(self.config.tokens)}个")
        
        scan_count = 0
        new_opportunities_count = 0
        
        while True:
            try:
                scan_count += 1
                start_time = time.time()
                
                # 扫描所有套利机会
                opportunities = await self.scan_all_opportunities()
                
                # 筛选新机会
                new_opportunities = []
                for opp in opportunities:
                    key = self._get_opportunity_key(opp)
                    if key not in self.seen_opportunities:
                        self.seen_opportunities.add(key)
                        new_opportunities.append(opp)
                
                if new_opportunities:
                    # 按利润排序
                    new_opportunities.sort(key=lambda x: x["net_profit"], reverse=True)
                    
                    print(f"🔍 第{scan_count}次扫描: 发现{len(new_opportunities)}个新机会")
                    
                    # 显示新机会
                    for opp in new_opportunities[:5]:  # 显示前5个
                        self.display_opportunity(opp)
                        new_opportunities_count += 1
                
                # 显示统计
                if scan_count % 3 == 0:
                    total_profit = sum(o["net_profit"] for o in self.opportunities) / 1e6
                    print(f"📊 统计: 新机会{new_opportunities_count}, 总机会{len(self.opportunities)}, 总利润${total_profit:.4f}")
                
                # 定期清理
                if scan_count % 30 == 0:
                    recent_keys = {self._get_opportunity_key(opp) for opp in list(self.opportunities)[-200:]}
                    self.seen_opportunities = recent_keys
                
                # 等待
                elapsed = time.time() - start_time
                sleep_time = max(0, self.config.scan_interval - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"扫描错误: {e}")
                await asyncio.sleep(1)
    
    def run(self):
        """运行机器人"""
        asyncio.run(self.run_async())

def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('./logs/arbitrage_advanced.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    config = AdvancedConfig()
    bot = AdvancedArbitrageBot(config)
    bot.run()

if __name__ == "__main__":
    main()