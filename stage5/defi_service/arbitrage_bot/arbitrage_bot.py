
#!/usr/bin/env python3
"""
基础套利机器人
支持Uniswap V2/V3的基本套利功能
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
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from web3 import Web3
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ========== 配置适配器 ==========
class ConfigAdapter:
    """适配config.py配置"""
    
    def __init__(self):
        from config import (
            RPC_URLS, DEX_CONFIGS, TOKENS, ARBITRAGE_PARAMS
        )
        
        self.rpc_url = RPC_URLS["primary"]
        self.dex_configs = {k: v for k, v in DEX_CONFIGS.items() if v.get("enabled", False)}
        self.tokens = TOKENS
        self.amount_usdt = int(ARBITRAGE_PARAMS["amount_usdt"] * 1e6)
        self.min_net_profit_usdt = int(ARBITRAGE_PARAMS["min_profit_usdt"] * 1e6)
        self.slippage_bps = ARBITRAGE_PARAMS["max_slippage_bps"]
        self.scan_interval = ARBITRAGE_PARAMS["scan_interval"]

# ========== DEX接口 ==========
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

# ========== Uniswap V2接口 ==========
class UniswapV2(DEXInterface):
    """Uniswap V2接口"""
    
    ROUTER_ABI = json.loads('''[
        {"name": "getAmountsOut", 
         "inputs": [{"name": "amountIn", "type": "uint256"}, {"name": "path", "type": "address[]"}],
         "outputs": [{"name": "amounts", "type": "uint256[]"}],
         "stateMutability": "view", "type": "function"}
    ]''')
    
    def __init__(self, w3: Web3, router_address: str, name: str = "UniswapV2"):
        config = {"router": router_address}
        super().__init__(w3, name, config)
        self.router = w3.eth.contract(
            address=Web3.to_checksum_address(router_address),
            abi=self.ROUTER_ABI
        )
    
    def quote(self, token_in: str, token_out: str, amount_in: int) -> Optional[Dict]:
        """获取报价"""
        try:
            path = [Web3.to_checksum_address(token_in), Web3.to_checksum_address(token_out)]
            amounts = self.router.functions.getAmountsOut(amount_in, path).call()
            
            if len(amounts) >= 2 and amounts[1] > 0:
                return {
                    "amount_out": amounts[1],
                    "price": amounts[1] / amount_in if amount_in > 0 else 0,
                    "gas_estimate": 150000
                }
        except Exception as e:
            self.logger.debug(f"Quote failed: {e}")
        return None

# ========== Uniswap V3接口 ==========
class UniswapV3(DEXInterface):
    """Uniswap V3接口"""
    
    QUOTER_ABI = json.loads('''[
        {"name": "quoteExactInputSingle", 
         "inputs": [
            {"name": "tokenIn", "type": "address"},
            {"name": "tokenOut", "type": "address"},
            {"name": "amountIn", "type": "uint256"},
            {"name": "fee", "type": "uint24"},
            {"name": "sqrtPriceLimitX96", "type": "uint160"}
         ],
         "outputs": [{"name": "amountOut", "type": "uint256"}],
         "stateMutability": "nonpayable", "type": "function"}
    ]''')
    
    def __init__(self, w3: Web3, quoter_address: str, fee: int = 3000):
        config = {"quoter": quoter_address, "fee": fee}
        super().__init__(w3, "UniswapV3", config)
        self.quoter = w3.eth.contract(
            address=Web3.to_checksum_address(quoter_address),
            abi=self.QUOTER_ABI
        )
        self.fee = fee
    
    def quote(self, token_in: str, token_out: str, amount_in: int) -> Optional[Dict]:
        """获取报价"""
        try:
            amount_out = self.quoter.functions.quoteExactInputSingle(
                Web3.to_checksum_address(token_in),
                Web3.to_checksum_address(token_out),
                amount_in,
                self.fee,
                0
            ).call()
            
            if amount_out > 0:
                return {
                    "amount_out": amount_out,
                    "price": amount_out / amount_in if amount_in > 0 else 0,
                    "gas_estimate": 200000
                }
        except Exception as e:
            self.logger.debug(f"Quote failed: {e}")
        return None

# ========== 套利机器人 ==========
class ArbitrageBot:
    """套利机器人"""
    
    def __init__(self, config: ConfigAdapter):
        self.config = config
        self.logger = logging.getLogger("ArbitrageBot")
        
        # 初始化Web3连接
        self.w3 = self._init_web3()
        
        # 初始化DEX
        self.dexes = self._init_dexes()
        
        # 统计数据
        self.stats = defaultdict(int)
        self.opportunities_queue = deque(maxlen=1000)
    
    def _init_web3(self) -> Web3:
        """初始化Web3连接"""
        try:
            w3 = Web3(Web3.HTTPProvider(self.config.rpc_url))
            if w3.is_connected():
                self.logger.info(f"Connected to RPC: {self.config.rpc_url}")
                return w3
        except Exception as e:
            self.logger.error(f"Failed to connect to RPC: {e}")
        
        raise ConnectionError("无法连接到RPC节点")
    
    def _init_dexes(self) -> Dict[str, DEXInterface]:
        """初始化DEX"""
        dexes = {}
        
        # Uniswap V3
        try:
            uniswap_v3_config = self.config.dex_configs.get("uniswap_v3", {})
            if uniswap_v3_config.get("enabled", False):
                dexes["uniswap_v3"] = UniswapV3(
                    self.w3,
                    uniswap_v3_config["quoter"],
                    uniswap_v3_config.get("fee", 3000)
                )
        except Exception as e:
            self.logger.warning(f"Failed to init UniswapV3: {e}")
        
        # SushiSwap (UniswapV2兼容)
        try:
            sushiswap_config = self.config.dex_configs.get("sushiswap", {})
            if sushiswap_config.get("enabled", False):
                dexes["sushiswap"] = UniswapV2(
                    self.w3,
                    sushiswap_config["router"],
                    "SushiSwap"
                )
        except Exception as e:
            self.logger.warning(f"Failed to init SushiSwap: {e}")
        
        self.logger.info(f"Initialized {len(dexes)} DEXes: {list(dexes.keys())}")
        return dexes
    
    async def scan_cross_dex_arbitrage(self) -> List[Dict]:
        """扫描跨DEX套利机会"""
        opportunities = []
        tokens = list(self.config.tokens.values())
        
        # 扫描主要代币对
        for token_a, token_b in [("USDT", "USDC"), ("USDT", "DAI"), ("USDC", "DAI")]:
            token_a_addr = self.config.tokens.get(token_a)
            token_b_addr = self.config.tokens.get(token_b)
            
            if not token_a_addr or not token_b_addr:
                continue
            
            # 获取所有DEX的价格
            prices = []
            for dex_name, dex in self.dexes.items():
                price_data = await self._get_dex_price(dex_name, dex, token_a_addr, token_b_addr)
                if price_data:
                    prices.append(price_data)
            
            # 查找价格差异
            if len(prices) >= 2:
                sorted_prices = sorted(prices, key=lambda x: x["price"])
                
                # 检查最低买入和最高卖出之间的差价
                if sorted_prices[-1]["price"] > sorted_prices[0]["price"] * 1.001:  # 0.1%以上差价
                    opportunity = self._create_cross_dex_opportunity(
                        token_a_addr, token_b_addr,
                        sorted_prices[0],  # 最低价买入
                        sorted_prices[-1]  # 最高价卖出
                    )
                    
                    if opportunity and opportunity["net_profit"] > self.config.min_net_profit_usdt:
                        opportunities.append(opportunity)
        
        return opportunities
    
    async def _get_dex_price(self, dex_name: str, dex: DEXInterface, token_a: str, token_b: str) -> Optional[Dict]:
        """获取DEX价格"""
        try:
            amount_in = self.config.amount_usdt
            
            # 获取报价
            price_data = dex.quote(token_a, token_b, amount_in)
            
            if price_data:
                return {
                    "dex": dex_name,
                    "token_in": token_a,
                    "token_out": token_b,
                    "amount_in": amount_in,
                    "amount_out": price_data["amount_out"],
                    "price": price_data["price"],
                    "gas_estimate": price_data.get("gas_estimate", 200000)
                }
        except Exception as e:
            self.logger.debug(f"Failed to get price from {dex_name}: {e}")
        
        return None
    
    def _create_cross_dex_opportunity(self, token_a: str, token_b: str, 
                                     buy_price: Dict, sell_price: Dict) -> Optional[Dict]:
        """创建跨DEX套利机会"""
        try:
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
            gas_price = self.w3.eth.gas_price
            
            # 计算ETH成本
            gas_cost_wei = gas_price * gas_used
            gas_cost_eth = gas_cost_wei / 10**18
            
            # 使用固定ETH价格
            eth_price_usdt = 1800
            gas_cost_usdt = int(gas_cost_eth * eth_price_usdt * 1e6)
            
            return gas_cost_usdt
            
        except Exception as e:
            self.logger.error(f"Gas cost estimation failed: {e}")
            return int(0.5 * 1e6)  # 默认0.5 USDT
    
    def display_opportunity(self, opportunity: Dict):
        """显示套利机会"""
        self.logger.info("=" * 60)
        self.logger.info("🎯 发现套利机会!")
        
        self.logger.info(f"类型: 跨DEX套利")
        self.logger.info(f"代币对: {self._get_token_names(opportunity['token_pair'])}")
        self.logger.info(f"买入DEX: {opportunity['buy_dex']} @ {opportunity['buy_price']:.6f}")
        self.logger.info(f"卖出DEX: {opportunity['sell_dex']} @ {opportunity['sell_price']:.6f}")
        self.logger.info(f"价差: {opportunity['price_diff_pct']:.2f}%")
        
        self.logger.info(f"投入金额: ${opportunity['amount_in']/1e6:.2f}")
        self.logger.info(f"预期输出: ${opportunity['amount_out']/1e6:.2f}")
        self.logger.info(f"毛利润: ${opportunity['expected_profit']/1e6:.2f}")
        self.logger.info(f"Gas成本: ${opportunity['gas_cost']/1e6:.2f}")
        self.logger.info(f"净利润: ${opportunity['net_profit']/1e6:.2f}")
        self.logger.info(f"利润率: {opportunity['profit_percentage']:.2f}%")
        
        self.logger.info("=" * 60)
    
    def _get_token_names(self, addresses: List[str]) -> List[str]:
        """获取代币名称"""
        token_map = {v: k for k, v in self.config.tokens.items()}
        return [token_map.get(addr, addr[-6:]) for addr in addresses]
    
    def _save_opportunities(self, opportunities: List[Dict]):
        """保存套利机会"""
        try:
            filename = f"./data/opportunities_{datetime.now().strftime('%Y%m%d')}.json"
            
            # 读取现有数据
            existing_data = []
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    existing_data = json.load(f)
            
            # 添加新数据
            existing_data.extend(opportunities)
            
            # 限制文件大小
            if len(existing_data) > 1000:
                existing_data = existing_data[-1000:]
            
            # 保存
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'w') as f:
                json.dump(existing_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save opportunities: {e}")
    
    def _display_statistics(self):
        """显示统计信息"""
        self.logger.info("=" * 60)
        self.logger.info("📊 套利机器人统计")
        self.logger.info(f"发现机会总数: {self.stats['total_opportunities']}")
        self.logger.info(f"潜在总利润: ${self.stats['total_profit_potential']:.2f}")
        
        # 分析最近的机会
        recent_opps = list(self.opportunities_queue)[-50:]
        if recent_opps:
            avg_profit = sum(o["net_profit"] for o in recent_opps) / len(recent_opps) / 1e6
            max_profit = max(o["net_profit"] for o in recent_opps) / 1e6
            
            self.logger.info(f"最近50个机会:")
            self.logger.info(f"  平均利润: ${avg_profit:.2f}")
            self.logger.info(f"  最大利润: ${max_profit:.2f}")
            
            # DEX统计
            dex_stats = defaultdict(int)
            for opp in recent_opps:
                dex_stats[opp["buy_dex"]] += 1
                dex_stats[opp["sell_dex"]] += 1
            
            if dex_stats:
                self.logger.info("DEX使用频率:")
                for dex, count in sorted(dex_stats.items(), key=lambda x: x[1], reverse=True)[:3]:
                    self.logger.info(f"  {dex}: {count}次")
        
        self.logger.info("=" * 60)
    
    async def run_async(self):
        """异步运行主循环"""
        self.logger.info("🚀 套利机器人启动")
        self.logger.info(f"监控DEX: {list(self.dexes.keys())}")
        self.logger.info(f"监控代币: {list(self.config.tokens.keys())}")
        
        scan_count = 0
        
        while True:
            try:
                scan_count += 1
                start_time = time.time()
                
                # 扫描机会
                opportunities = await self.scan_cross_dex_arbitrage()
                
                if opportunities:
                    # 按利润排序
                    opportunities.sort(key=lambda x: x.get("net_profit", 0), reverse=True)
                    
                    self.logger.info(f"🔍 第{scan_count}次扫描: 发现{len(opportunities)}个机会")
                    
                    # 显示最佳机会
                    for opp in opportunities[:2]:  # 显示前2个
                        self.display_opportunity(opp)
                        
                        # 记录到队列
                        self.opportunities_queue.append(opp)
                        
                        # 更新统计
                        self.stats["total_opportunities"] += 1
                        self.stats["total_profit_potential"] += opp["net_profit"] / 1e6
                    
                    # 保存数据
                    self._save_opportunities(opportunities)
                
                # 定期显示统计
                if scan_count % 10 == 0:
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
    
    def run(self):
        """运行机器人"""
        try:
            # 设置异步事件循环
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            self.logger.info("收到停止信号")
        finally:
            self._display_statistics()

# ========== 主函数 ==========
def main():
    """主函数"""
    # 设置日志
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('./logs/arbitrage.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    # 加载配置
    config = ConfigAdapter()
    
    # 创建目录
    os.makedirs('./logs', exist_ok=True)
    os.makedirs('./data', exist_ok=True)
    
    # 创建并运行机器人
    bot = ArbitrageBot(config)
    bot.run()

if __name__ == "__main__":
    main()