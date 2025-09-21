"""
Hyperliquid数据提供器
用于从Hyperliquid链上获取并处理成强化学习训练所需的数据格式
"""
import asyncio
import aiohttp
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime, timedelta
import json
import time
from dataclasses import dataclass
import websockets

from data_loader import load_csv, prepare_data, validate_data
from utils import add_technical_indicators, create_features

logger = logging.getLogger(__name__)


@dataclass
class HyperliquidConfig:
    """Hyperliquid配置"""
    base_url: str = "https://api.hyperliquid.xyz"
    ws_url: str = "wss://api.hyperliquid.xyz/ws"
    symbol: str = "BTC-USD"
    interval: str = "1m"
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: int = 30


class HyperliquidDataProvider:
    """Hyperliquid数据提供器"""
    
    def __init__(self, config: HyperliquidConfig):
        self.config = config
        self.session = None
        self.ws = None
        self._setup_session()
    
    def _setup_session(self):
        """设置HTTP会话"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=10)
        )
    
    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()
        if self.ws:
            await self.ws.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """发送HTTP请求"""
        url = f"{self.config.base_url}/{endpoint}"
        
        for attempt in range(self.config.max_retries):
            try:
                async with self.session.post(url, json=payload) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"HTTP {response.status}: {await response.text()}")
                        
            except Exception as e:
                logger.error(f"Request attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    raise
    
    async def get_historical_data(
        self,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 1000,
        interval: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取历史K线数据
        
        Args:
            start_time: 开始时间戳（毫秒）
            end_time: 结束时间戳（毫秒）
            limit: 返回数据条数限制
            interval: 时间间隔
            
        Returns:
            DataFrame格式的历史数据
        """
        if interval is None:
            interval = self.config.interval
            
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": self.config.symbol,
                "interval": interval,
                "limit": limit
            }
        }
        
        if start_time:
            payload["req"]["startTime"] = start_time
        if end_time:
            payload["req"]["endTime"] = end_time
        
        try:
            data = await self._make_request("info", payload)
            
            if isinstance(data, list) and len(data) > 0:
                # 转换数据格式
                klines = []
                for item in data:
                    kline = {
                        "timestamp": int(item["t"]),
                        "open": float(item["o"]),
                        "high": float(item["h"]),
                        "low": float(item["l"]),
                        "close": float(item["c"]),
                        "volume": float(item["v"]),
                        "symbol": self.config.symbol
                    }
                    klines.append(kline)
                
                df = pd.DataFrame(klines)
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df = df.sort_values('timestamp').reset_index(drop=True)
                
                logger.info(f"Fetched {len(df)} historical records for {self.config.symbol}")
                return df
                
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return pd.DataFrame()
    
    async def get_market_info(self) -> Dict[str, Any]:
        """获取市场信息"""
        payload = {"type": "metaAndAssetCtxs"}
        
        try:
            data = await self._make_request("info", payload)
            
            if isinstance(data, list) and len(data) > 1:
                meta = data[0]
                asset_ctxs = data[1]
                
                for ctx in asset_ctxs:
                    if ctx.get("coin") == self.config.symbol:
                        return {
                            "symbol": self.config.symbol,
                            "funding_rate": float(ctx.get("funding", 0)),
                            "open_interest": float(ctx.get("openInterest", 0)),
                            "prev_funding_rate": float(ctx.get("prevFunding", 0)),
                            "funding_time": int(ctx.get("fundingTime", 0)),
                            "mark_price": float(ctx.get("markPx", 0)),
                            "mid_price": float(ctx.get("midPx", 0)),
                            "impact_bid": float(ctx.get("impactPxs", [0, 0])[0]),
                            "impact_ask": float(ctx.get("impactPxs", [0, 0])[1])
                        }
                        
        except Exception as e:
            logger.error(f"Error fetching market info: {e}")
        
        return {}
    
    async def get_orderbook_snapshot(self, levels: int = 10) -> Dict[str, Any]:
        """获取订单簿快照"""
        payload = {
            "type": "l2Book",
            "coin": self.config.symbol
        }
        
        try:
            data = await self._make_request("info", payload)
            
            if isinstance(data, dict):
                return {
                    "symbol": self.config.symbol,
                    "timestamp": int(time.time() * 1000),
                    "bids": [[float(level["px"]), float(level["sz"])] for level in data.get("levels", [[], []])[0][:levels]],
                    "asks": [[float(level["px"]), float(level["sz"])] for level in data.get("levels", [[], []])[1][:levels]]
                }
                
        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}")
            return {}
    
    async def get_recent_trades(self, limit: int = 100) -> pd.DataFrame:
        """获取最近交易数据"""
        payload = {
            "type": "recentTrades",
            "coin": self.config.symbol,
            "n": limit
        }
        
        try:
            data = await self._make_request("info", payload)
            
            if isinstance(data, list):
                trades = []
                for trade in data:
                    trades.append({
                        "timestamp": int(trade["time"]),
                        "price": float(trade["px"]),
                        "size": float(trade["sz"]),
                        "side": trade["side"],
                        "symbol": self.config.symbol
                    })
                
                df = pd.DataFrame(trades)
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                return df
                
        except Exception as e:
            logger.error(f"Error fetching recent trades: {e}")
            return pd.DataFrame()
    
    async def connect_websocket(self) -> bool:
        """连接WebSocket"""
        try:
            self.ws = await websockets.connect(self.config.ws_url)
            logger.info(f"Connected to WebSocket: {self.config.ws_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            return False
    
    async def subscribe_realtime_data(self, data_type: str = "candle") -> AsyncGenerator[Dict[str, Any], None]:
        """订阅实时数据"""
        if not self.ws:
            if not await self.connect_websocket():
                return
        
        subscription = {
            "method": "subscribe",
            "subscription": {
                "type": data_type,
                "coin": self.config.symbol
            }
        }
        
        if data_type == "candle":
            subscription["subscription"]["interval"] = self.config.interval
        
        await self.ws.send(json.dumps(subscription))
        logger.info(f"Subscribed to {data_type} data for {self.config.symbol}")
        
        try:
            async for message in self.ws:
                data = json.loads(message)
                
                if data.get("channel") == data_type:
                    yield data.get("data", {})
                    
        except websockets.exceptions.ConnectionClosed:
            logger.error("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error in WebSocket subscription: {e}")


class DataProcessor:
    """数据处理器"""
    
    @staticmethod
    def process_raw_data(raw_df: pd.DataFrame) -> pd.DataFrame:
        """处理原始数据"""
        if raw_df.empty:
            return raw_df
        
        # 确保数据类型正确
        numeric_columns = ["open", "high", "low", "close", "volume"]
        for col in numeric_columns:
            raw_df[col] = pd.to_numeric(raw_df[col], errors='coerce')
        
        # 按时间排序
        raw_df = raw_df.sort_values('timestamp').reset_index(drop=True)
        
        # 添加技术指标
        processed_df = add_technical_indicators(raw_df)
        
        # 验证数据
        if validate_data(processed_df):
            logger.info(f"Processed {len(processed_df)} records successfully")
            return processed_df
        
        return pd.DataFrame()
    
    @staticmethod
    def create_training_data(df: pd.DataFrame, window_size: int = 50) -> Tuple[np.ndarray, np.ndarray]:
        """创建训练数据"""
        if df.empty or len(df) < window_size:
            return np.array([]), np.array([])
        
        # 创建特征
        features = []
        for i in range(window_size, len(df)):
            window = df.iloc[i-window_size:i]
            feature = create_features(window)
            features.append(feature)
        
        features = np.array(features)
        
        # 创建标签（下一个时间段的收益率）
        close_prices = df['close'].values
        returns = (close_prices[window_size:] - close_prices[window_size-1:-1]) / close_prices[window_size-1:-1]
        
        # 将收益率转换为分类标签
        labels = np.digitize(returns, bins=[-0.01, -0.005, 0, 0.005, 0.01])
        
        return features, labels
    
    @staticmethod
    def save_processed_data(df: pd.DataFrame, filepath: str):
        """保存处理后的数据"""
        try:
            df.to_csv(filepath, index=False)
            logger.info(f"Processed data saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving processed data: {e}")


class HyperliquidDataManager:
    """Hyperliquid数据管理器"""
    
    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config = self._load_config(config_path)
        self.provider = None
        self.processor = DataProcessor()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置"""
        import yaml
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    async def initialize(self):
        """初始化数据提供器"""
        hl_config = HyperliquidConfig(
            symbol=self.config.get('realtime', {}).get('symbol', 'BTC-USD'),
            interval=self.config.get('data', {}).get('interval', '1m')
        )
        self.provider = HyperliquidDataProvider(hl_config)
    
    async def fetch_and_process_data(
        self,
        days_back: int = 30,
        save_path: Optional[str] = None
    ) -> pd.DataFrame:
        """获取并处理数据"""
        await self.initialize()
        
        try:
            # 计算时间范围
            end_time = int(time.time() * 1000)
            start_time = end_time - (days_back * 24 * 60 * 60 * 1000)
            
            # 获取历史数据
            raw_df = await self.provider.get_historical_data(
                start_time=start_time,
                end_time=end_time,
                limit=5000
            )
            
            if raw_df.empty:
                logger.error("No data fetched")
                return pd.DataFrame()
            
            # 处理数据
            processed_df = self.processor.process_raw_data(raw_df)
            
            # 保存数据
            if save_path:
                self.processor.save_processed_data(processed_df, save_path)
            
            return processed_df
            
        finally:
            await self.provider.close()
    
    async def get_realtime_data_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """获取实时数据流"""
        await self.initialize()
        
        try:
            async for data in self.provider.subscribe_realtime_data("candle"):
                yield data
        finally:
            await self.provider.close()


# 使用示例
async def main():
    """主函数示例"""
    logging.basicConfig(level=logging.INFO)
    
    # 创建数据管理器
    manager = HyperliquidDataManager()
    
    # 获取并处理历史数据
    print("Fetching historical data...")
    processed_df = await manager.fetch_and_process_data(
        days_back=7,
        save_path="data/hyperliquid_processed.csv"
    )
    
    if not processed_df.empty:
        print(f"Processed {len(processed_df)} records")
        print(processed_df.tail())
    
    # 测试实时数据流（可选）
    # print("Starting real-time data stream...")
    # async for data in manager.get_realtime_data_stream():
    #     print(data)


if __name__ == "__main__":
    asyncio.run(main())