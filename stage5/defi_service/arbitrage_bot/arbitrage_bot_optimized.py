#!/usr/bin/env python3
"""
优化版套利机器人
增加更多DEX、代币对和高级检测算法
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

class OptimizedConfig:
    """优化配置"""
    
    def __init__(self):
        self.rpc_url = os.getenv("RPC_URL", "https://arb1.arbitrum.io/rpc")
        self.amount_usdt = int(float(os.getenv("AMOUNT_USDT", "100")) * 1e6)
        self.min_profit_usdt = int(float(os.getenv("MIN_PROFIT_USDT", "0.5")) * 1e6)
        self.scan_interval = float(os.getenv("SCAN_INTERVAL", "1"))
        self.min_price_diff_pct = float(os.getenv("MIN_PRICE_DIFF_PCT", "0.05"))  # 0.05%
        self.max_slippage_bps = int(os.getenv("MAX_SLIPPAGE_BPS", "100"))
        
        # Arbitrum上的DEX配置
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
            }
        }
        
        # 代币配置
        self.tokens = {
            "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
            "USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
            "USDC.e": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
            "DAI": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
            "WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
            "WBTC": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f",
            "ARB": "0x912CE59144191C1204E64559FE8253a0e49E6548",
            "LINK": "0xf97f4df75117a78c1A5a0DBb814Af92458539FB4",
            "UNI": "0xFa7F8980b0f1E64A2062791cc3b0871572f1F7f0",
            "GMX": "0xfc5A1A6EB076a2C7aD06eD22C90d7E710E35ad0a"
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
        
        # 多个手续费等级
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
            
            # 尝试所有手续费等级
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
                    "fee": 30,  # 0.3%
                    "gas_estimate": 150000
                }
                
        except Exception as e:
            self.logger.debug(f"{self.name} quote failed: {e}")
        
        return None

class OptimizedArbitrageBot:
    """优化版套利机器人"""
    
    def __init__(self, config: OptimizedConfig):
        self.config = config
        self.logger = logging.getLogger("OptimizedArbitrageBot")
        
        # 初始化Web3
        self.w3 = Web3(Web3.HTTPProvider(config.rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError("无法连接到RPC节点")
        
        # 初始化DEX
        self.dexes = self._init_dexes()
        
        # 统计数据
        self.stats = defaultdict(int)
        self.opportunities = deque(maxlen=1000)
        self.seen_opportunities = set()  # 记录已发现的机会
        
    def _init_dexes(self) -> Dict[str, DEXInterface]:
        """初始化所有DEX"""
        dexes = {}
        
        # Uniswap V3
        if self.config.dex_configs["uniswap_v3"]["enabled"]:
            dexes["uniswap_v3"] = UniswapV3DEX(
                self.w3, 
                self.config.dex_configs["uniswap_v3"]["quoter"]
            )
        
        # Uniswap V2兼容DEX
        for name, config in self.config.dex_configs.items():
            if name != "uniswap_v3" and config["enabled"]:
                dexes[name] = UniswapV2DEX(
                    self.w3,
                    config["router"],
                    name.replace("_", " ").title()
                )
        
        self.logger.info(f"Initialized {len(dexes)} DEXes: {list(dexes.keys())}")
        return dexes
    
    def generate_token_pairs(self) -> List[Tuple[str, str]]:
        """生成所有可能的代币对"""
        tokens = list(self.config.tokens.items())
        pairs = []
        
        # 稳定币优先
        stablecoins = ["USDT", "USDC", "DAI", "USDC.e"]
        others = [t for t in self.config.tokens.keys() if t not in stablecoins]
        
        # 稳定币对稳定币
        for i, (s1, addr1) in enumerate([(s, self.config.tokens[s]) for s in stablecoins if s in self.config.tokens]):
            for s2, addr2 in [(s, self.config.tokens[s]) for s in stablecoins[i+1:] if s in self.config.tokens]:
                pairs.append((addr1, addr2))
        
        # 其他代币对稳定币
        for token, addr in [(t, self.config.tokens[t]) for t in others]:
            for stable, stable_addr in [(s, self.config.tokens[s]) for s in stablecoins if s in self.config.tokens]:
                pairs.extend([(addr, stable_addr), (stable_addr, addr)])
        
        return pairs
    
    async def scan_arbitrage_opportunities(self) -> List[Dict]:
        """扫描所有套利机会"""
        opportunities = []
        pairs = self.generate_token_pairs()
        
        # 并行扫描所有代币对
        tasks = []
        for token_a, token_b in pairs:
            task = self._scan_pair_opportunities(token_a, token_b)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                opportunities.extend(result)
        
        return opportunities
    
    async def _scan_pair_opportunities(self, token_a: str, token_b: str) -> List[Dict]:
        """扫描单个代币对的套利机会"""
        opportunities = []
        
        # 获取所有DEX的价格
        prices = []
        for dex_name, dex in self.dexes.items():
            try:
                # 两个方向的价格
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
            # 寻找最佳套利路径
            opportunities.extend(self._find_best_arbitrage(prices))
        
        return opportunities
    
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
    
    def _find_best_arbitrage(self, prices: List[Dict]) -> List[Dict]:
        """寻找最佳套利机会"""
        opportunities = []
        
        # 跨DEX套利
        for i, buy_price in enumerate(prices):
            for j, sell_price in enumerate(prices):
                if i != j and buy_price["dex"] != sell_price["dex"]:
                    # 计算利润
                    profit = self._calculate_profit(buy_price, sell_price)
                    if profit and profit["net_profit"] > self.config.min_profit_usdt:
                        opportunities.append(profit)
        
        return opportunities
    
    def _calculate_profit(self, buy_price: Dict, sell_price: Dict) -> Optional[Dict]:
        """计算套利利润"""
        try:
            # 买入路径
            amount_in = self.config.amount_usdt
            amount_mid = int(amount_in * buy_price["price_ab"])
            amount_out = int(amount_mid * sell_price["price_ba"])
            
            # 计算利润
            gross_profit = amount_out - amount_in
            gas_cost = self._estimate_gas_cost(buy_price["gas_ab"] + sell_price["gas_ba"])
            net_profit = gross_profit - gas_cost
            
            if net_profit > self.config.min_profit_usdt:
                return {
                    "type": "cross_dex",
                    "token_pair": [buy_price["token_a"], buy_price["token_b"]],
                    "buy_dex": buy_price["dex"],
                    "sell_dex": sell_price["dex"],
                    "amount_in": amount_in,
                    "amount_out": amount_out,
                    "gross_profit": gross_profit,
                    "gas_cost": gas_cost,
                    "net_profit": net_profit,
                    "profit_percentage": (net_profit / amount_in * 100),
                    "buy_price": buy_price["price_ab"],
                    "sell_price": sell_price["price_ba"],
                    "price_diff_pct": ((sell_price["price_ba"] - buy_price["price_ab"]) / buy_price["price_ab"] * 100),
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.debug(f"Profit calculation failed: {e}")
        
        return None
    
    def _estimate_gas_cost(self, gas_used: int) -> int:
        """优化Gas成本估算"""
        try:
            # 获取实时Gas价格
            gas_price = self.w3.eth.gas_price
            gas_cost_wei = gas_price * gas_used
            gas_cost_eth = gas_cost_wei / 10**18
            
            # 使用WETH价格估算
            weth_price = self._get_weth_price()
            gas_cost_usdt = int(gas_cost_eth * weth_price * 1e6)
            
            return max(gas_cost_usdt, int(0.1 * 1e6))  # 最小0.1 USDT
            
        except Exception:
            return int(0.5 * 1e6)  # 默认值
    
    def _get_weth_price(self) -> float:
        """获取WETH价格（USDT）"""
        try:
            # 简化的WETH价格获取
            return 1800.0  # 固定价格，实际应该从DEX获取
        except:
            return 1800.0
    def _get_opportunity_key(self, opportunity: Dict) -> str:
        """生成机会的唯一标识符"""
        return f"{opportunity['token_pair'][0]}_{opportunity['token_pair'][1]}_{opportunity['buy_dex']}_{opportunity['sell_dex']}_{int(opportunity['buy_price']*1e12)}_{int(opportunity['sell_price']*1e12)}"
    
    def display_opportunity(self, opportunity: Dict):
        """显示套利机会"""
        token_map = {v: k for k, v in self.config.tokens.items()}
        token_names = [token_map.get(addr, addr[-6:]) for addr in opportunity["token_pair"]]
        
        print("=" * 60)
        print("🎯 发现新套利机会!")
        print(f"代币对: {token_names[0]}/{token_names[1]}")
        print(f"买入DEX: {opportunity['buy_dex']} @ {opportunity['buy_price']:.8f}")
        print(f"卖出DEX: {opportunity['sell_dex']} @ {opportunity['sell_price']:.8f}")
        print(f"价差: {opportunity['price_diff_pct']:.3f}%")
        print(f"净利润: ${opportunity['net_profit']/1e6:.4f}")
        print(f"利润率: {opportunity['profit_percentage']:.3f}%")
        print("=" * 60)
        print("=" * 60)
    
    async def run_async(self):
        """异步运行主循环"""
        self.logger.info("🚀 优化版套利机器人启动")
        self.logger.info(f"监控DEX: {list(self.dexes.keys())}")
        self.logger.info(f"监控代币: {list(self.config.tokens.keys())}")
        
        scan_count = 0
        new_opportunities_count = 0
        
        while True:
            try:
                scan_count += 1
                start_time = time.time()
                
                # 扫描套利机会
                opportunities = await self.scan_arbitrage_opportunities()
                
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
                    for opp in new_opportunities[:3]:
                        self.display_opportunity(opp)
                        new_opportunities_count += 1
                        
                        # 保存数据
                        self.opportunities.append(opp)
                
                # 显示统计
                if scan_count % 5 == 0:
                    total_profit = sum(o["net_profit"] for o in self.opportunities) / 1e6
                    print(f"📊 统计: 新机会{new_opportunities_count}, 总机会{len(self.opportunities)}, 总利润${total_profit:.2f}")
                
                # 定期清理旧的机会记录（防止内存增长）
                if scan_count % 50 == 0:
                    # 只保留最近100个唯一机会的记录
                    recent_keys = {self._get_opportunity_key(opp) for opp in list(self.opportunities)[-100:]}
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
                await asyncio.sleep(2)
    
    def run(self):
        """运行机器人"""
        asyncio.run(self.run_async())

def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('./logs/arbitrage_optimized.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    config = OptimizedConfig()
    bot = OptimizedArbitrageBot(config)
    bot.run()

if __name__ == "__main__":
    main()