"""
实时数据适配器 - Hyperliquid WebSocket适配器
用于连接Hyperliquid交易所的WebSocket API获取实时数据
"""
import asyncio
import json
import websockets
import aiohttp
import pandas as pd
from typing import AsyncGenerator, Dict, Any, Optional
import logging
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class HyperliquidRealtimeAdapter:
    """Hyperliquid实时数据适配器"""
    
    def __init__(self, symbol: str = "BTC-USD"):
        self.symbol = symbol
        self.ws_url = "wss://api.hyperliquid.xyz/ws"
        self.http_url = "https://api.hyperliquid.xyz/info"
        self.websocket = None
        self.is_connected = False
        
    async def connect(self) -> bool:
        """建立WebSocket连接"""
        try:
            self.websocket = await websockets.connect(self.ws_url)
            self.is_connected = True
            logger.info(f"Connected to Hyperliquid WebSocket: {self.ws_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("Disconnected from WebSocket")
    
    async def subscribe_klines(self, interval: str = "1m") -> AsyncGenerator[Dict[str, Any], None]:
        """
        订阅K线数据
        
        Args:
            interval: 时间间隔 (1m, 5m, 15m, 1h, 4h, 1d)
        
        Yields:
            K线数据字典
        """
        if not self.is_connected:
            await self.connect()
        
        # 构建订阅消息
        subscription = {
            "method": "subscribe",
            "subscription": {
                "type": "candle",
                "coin": self.symbol,
                "interval": interval
            }
        }
        
        await self.websocket.send(json.dumps(subscription))
        logger.info(f"Subscribed to {interval} candles for {self.symbol}")
        
        async for message in self.websocket:
            try:
                data = json.loads(message)
                
                if data.get("channel") == "candle":
                    candle_data = data.get("data", {})
                    
                    # 转换数据格式
                    kline = {
                        "timestamp": int(candle_data.get("t", 0)),
                        "open": float(candle_data.get("o", 0)),
                        "high": float(candle_data.get("h", 0)),
                        "low": float(candle_data.get("l", 0)),
                        "close": float(candle_data.get("c", 0)),
                        "volume": float(candle_data.get("v", 0)),
                        "symbol": self.symbol
                    }
                    
                    yield kline
                    
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                continue
    
    async def subscribe_ticker(self) -> AsyncGenerator[Dict[str, Any], None]:
        """订阅实时价格数据"""
        if not self.is_connected:
            await self.connect()
        
        subscription = {
            "method": "subscribe",
            "subscription": {
                "type": "l2Book",
                "coin": self.symbol
            }
        }
        
        await self.websocket.send(json.dumps(subscription))
        logger.info(f"Subscribed to ticker for {self.symbol}")
        
        async for message in self.websocket:
            try:
                data = json.loads(message)
                
                if data.get("channel") == "l2Book":
                    levels = data.get("data", {})
                    
                    # 获取最优买卖价
                    best_bid = levels.get("levels", [[], []])[0][0]["px"] if levels.get("levels", [[], []])[0] else 0
                    best_ask = levels.get("levels", [[], []])[1][0]["px"] if levels.get("levels", [[], []])[1] else 0
                    
                    ticker = {
                        "timestamp": int(time.time() * 1000),
                        "bid": float(best_bid),
                        "ask": float(best_ask),
                        "mid": (float(best_bid) + float(best_ask)) / 2,
                        "symbol": self.symbol
                    }
                    
                    yield ticker
                    
            except Exception as e:
                logger.error(f"Error processing ticker message: {e}")
                continue
    
    async def get_historical_klines(self, interval: str = "1m", limit: int = 1000) -> pd.DataFrame:
        """
        获取历史K线数据
        
        Args:
            interval: 时间间隔
            limit: 返回数据条数
        
        Returns:
            DataFrame格式的K线数据
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "type": "candleSnapshot",
                    "req": {
                        "coin": self.symbol,
                        "interval": interval,
                        "startTime": int((time.time() - limit * 60) * 1000)
                    }
                }
                
                async with session.post(self.http_url, json=payload) as response:
                    data = await response.json()
                    
                    if isinstance(data, list) and len(data) > 0:
                        klines = []
                        for item in data:
                            kline = {
                                "timestamp": int(item["t"]),
                                "open": float(item["o"]),
                                "high": float(item["h"]),
                                "low": float(item["l"]),
                                "close": float(item["c"]),
                                "volume": float(item["v"]),
                                "symbol": self.symbol
                            }
                            klines.append(kline)
                        
                        df = pd.DataFrame(klines)
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                        return df
                    
        except Exception as e:
            logger.error(f"Error fetching historical klines: {e}")
            return pd.DataFrame()
    
    async def get_funding_rate(self) -> Optional[Dict[str, Any]]:
        """获取资金费率"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "type": "metaAndAssetCtxs"
                }
                
                async with session.post(self.http_url, json=payload) as response:
                    data = await response.json()
                    
                    if isinstance(data, list) and len(data) > 1:
                        meta = data[0]
                        asset_ctxs = data[1]
                        
                        for ctx in asset_ctxs:
                            if ctx.get("coin") == self.symbol:
                                return {
                                    "symbol": self.symbol,
                                    "funding_rate": float(ctx.get("funding", 0)),
                                    "open_interest": float(ctx.get("openInterest", 0)),
                                    "prev_funding_rate": float(ctx.get("prevFunding", 0)),
                                    "funding_time": int(ctx.get("fundingTime", 0))
                                }
                                
        except Exception as e:
            logger.error(f"Error fetching funding rate: {e}")
        
        return None


class MockRealtimeAdapter:
    """模拟实时数据适配器，用于测试"""
    
    def __init__(self, symbol: str = "BTC-USD"):
        self.symbol = symbol
        self.df = None
        self.current_index = 0
        
    def load_mock_data(self, df: pd.DataFrame):
        """加载模拟数据"""
        self.df = df.reset_index(drop=True)
        self.current_index = 0
        
    async def subscribe_klines(self, interval: str = "1m") -> AsyncGenerator[Dict[str, Any], None]:
        """生成模拟K线数据"""
        if self.df is None:
            logger.error("Mock data not loaded")
            return
            
        while self.current_index < len(self.df):
            row = self.df.iloc[self.current_index]
            
            kline = {
                "timestamp": int(row.get("timestamp", self.current_index)),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
                "symbol": self.symbol
            }
            
            yield kline
            self.current_index += 1
            
            # 模拟实时延迟
            await asyncio.sleep(1)


# 使用示例
async def main():
    """测试实时适配器"""
    adapter = HyperliquidRealtimeAdapter("BTC-USD")
    
    try:
        # 获取历史数据
        hist_df = await adapter.get_historical_klines("1m", 100)
        print(f"Historical data: {len(hist_df)} rows")
        
        # 订阅实时数据
        async for kline in adapter.subscribe_klines("1m"):
            print(f"New kline: {kline}")
            
    except KeyboardInterrupt:
        logger.info("Stopping...")
    finally:
        await adapter.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())