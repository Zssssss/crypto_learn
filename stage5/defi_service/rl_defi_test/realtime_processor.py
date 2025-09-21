"""
实时数据处理器
用于处理Hyperliquid实时数据流并转换为训练格式
"""
import asyncio
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, AsyncGenerator, Any
import logging
from datetime import datetime, timedelta
from collections import deque
import threading
import time

from hyperliquid_data_provider import HyperliquidDataProvider, HyperliquidConfig
from data_formatter import DataFormatter
from utils import add_technical_indicators

logger = logging.getLogger(__name__)


class RealtimeDataProcessor:
    """实时数据处理器"""
    
    def __init__(self, config: Dict[str, Any], buffer_size: int = 1000):
        self.config = config
        self.buffer_size = buffer_size
        self.data_buffer = deque(maxlen=buffer_size)
        self.feature_buffer = deque(maxlen=buffer_size)
        self.is_running = False
        self.processor_task = None
        self.formatter = DataFormatter(config)
        self.window_size = config.get('env', {}).get('window_size', 50)
        
        # 配置
        hl_config = HyperliquidConfig(
            symbol=config.get('realtime', {}).get('symbol', 'BTC-USD'),
            interval=config.get('data', {}).get('interval', '1m')
        )
        self.provider = HyperliquidDataProvider(hl_config)
        
        # 统计数据
        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'errors': 0,
            'last_update': None
        }
    
    async def start(self):
        """启动实时处理器"""
        if self.is_running:
            logger.warning("Realtime processor already running")
            return
        
        self.is_running = True
        logger.info("Starting realtime data processor...")
        
        try:
            await self.provider.initialize()
            self.processor_task = asyncio.create_task(self._process_loop())
            logger.info("Realtime data processor started")
        except Exception as e:
            logger.error(f"Failed to start processor: {e}")
            self.is_running = False
    
    async def stop(self):
        """停止实时处理器"""
        if not self.is_running:
            return
        
        self.is_running = False
        logger.info("Stopping realtime data processor...")
        
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        
        await self.provider.close()
        logger.info("Realtime data processor stopped")
    
    async def _process_loop(self):
        """处理循环"""
        try:
            async for raw_data in self.provider.subscribe_realtime_data("candle"):
                if not self.is_running:
                    break
                
                try:
                    await self._process_message(raw_data)
                    self.stats['messages_processed'] += 1
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    self.stats['errors'] += 1
                
                self.stats['messages_received'] += 1
                self.stats['last_update'] = datetime.now()
                
        except Exception as e:
            logger.error(f"Error in processing loop: {e}")
            self.is_running = False
    
    async def _process_message(self, raw_data: Dict[str, Any]):
        """处理单个消息"""
        if not raw_data:
            return
        
        # 转换数据格式
        candle_data = {
            'timestamp': int(raw_data.get('t', 0)),
            'open': float(raw_data.get('o', 0)),
            'high': float(raw_data.get('h', 0)),
            'low': float(raw_data.get('l', 0)),
            'close': float(raw_data.get('c', 0)),
            'volume': float(raw_data.get('v', 0)),
            'symbol': self.config.get('realtime', {}).get('symbol', 'BTC-USD')
        }
        
        # 添加到缓冲区
        self.data_buffer.append(candle_data)
        
        # 当缓冲区有足够数据时创建特征
        if len(self.data_buffer) >= self.window_size:
            df = pd.DataFrame(list(self.data_buffer))
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # 添加技术指标
            enriched_df = add_technical_indicators(df)
            
            # 创建特征
            if len(enriched_df) >= self.window_size:
                features = self.formatter.create_state_features(enriched_df)
                if features.size > 0:
                    self.feature_buffer.append(features[-1])
    
    def get_latest_features(self, n: int = 1) -> List[np.ndarray]:
        """获取最新特征"""
        if not self.feature_buffer:
            return []
        
        return list(self.feature_buffer)[-n:]
    
    def get_buffer_data(self) -> pd.DataFrame:
        """获取缓冲区数据"""
        if not self.data_buffer:
            return pd.DataFrame()
        
        df = pd.DataFrame(list(self.data_buffer))
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'buffer_size': len(self.data_buffer),
            'feature_buffer_size': len(self.feature_buffer)
        }


class RealtimeDataAggregator:
    """实时数据聚合器"""
    
    def __init__(self, config: Dict[str, Any], aggregation_period: str = '1H'):
        self.config = config
        self.aggregation_period = aggregation_period
        self.current_bar = None
        self.last_update = None
        self.data_callback = None
        
    def set_callback(self, callback):
        """设置数据回调"""
        self.data_callback = callback
    
    def process_tick(self, tick_data: Dict[str, Any]):
        """处理tick数据"""
        timestamp = datetime.fromtimestamp(tick_data['timestamp'] / 1000)
        
        if self.current_bar is None:
            self.current_bar = self._create_new_bar(timestamp, tick_data)
        elif self._should_create_new_bar(timestamp):
            # 完成当前bar并创建新的
            if self.data_callback:
                self.data_callback(self.current_bar)
            self.current_bar = self._create_new_bar(timestamp, tick_data)
        else:
            # 更新当前bar
            self._update_bar(tick_data)
        
        self.last_update = timestamp
    
    def _create_new_bar(self, timestamp: datetime, tick_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建新的K线bar"""
        period_start = timestamp.replace(
            minute=0 if self.aggregation_period.endswith('H') else timestamp.minute,
            second=0,
            microsecond=0
        )
        
        return {
            'timestamp': int(period_start.timestamp() * 1000),
            'open': tick_data['price'],
            'high': tick_data['price'],
            'low': tick_data['price'],
            'close': tick_data['price'],
            'volume': tick_data.get('size', 0),
            'symbol': tick_data.get('symbol', 'BTC-USD')
        }
    
    def _update_bar(self, tick_data: Dict[str, Any]):
        """更新当前bar"""
        price = tick_data['price']
        size = tick_data.get('size', 0)
        
        self.current_bar['high'] = max(self.current_bar['high'], price)
        self.current_bar['low'] = min(self.current_bar['low'], price)
        self.current_bar['close'] = price
        self.current_bar['volume'] += size
    
    def _should_create_new_bar(self, timestamp: datetime) -> bool:
        """判断是否应该创建新的bar"""
        if not self.current_bar:
            return True
        
        current_time = datetime.fromtimestamp(self.current_bar['timestamp'] / 1000)
        
        if self.aggregation_period == '1H':
            return timestamp.hour != current_time.hour
        elif self.aggregation_period == '1m':
            return timestamp.minute != current_time.minute
        else:
            return False


class RealtimeFeatureEngine:
    """实时特征引擎"""
    
    def __init__(self, config: Dict[str, Any], feature_window: int = 100):
        self.config = config
        self.feature_window = feature_window
        self.formatter = DataFormatter(config)
        self.feature_cache = {}
        
    def update_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """更新特征"""
        if df.empty or len(df) < self.config.get('env', {}).get('window_size', 50):
            return {}
        
        try:
            # 添加技术指标
            enriched_df = add_technical_indicators(df)
            
            # 创建特征
            features = self.formatter.create_state_features(enriched_df)
            
            if features.size > 0:
                latest_features = features[-1]
                
                # 创建特征字典
                feature_dict = {
                    'features': latest_features.tolist(),
                    'timestamp': df.iloc[-1]['timestamp'],
                    'price': df.iloc[-1]['close'],
                    'volume': df.iloc[-1]['volume']
                }
                
                return feature_dict
                
        except Exception as e:
            logger.error(f"Error updating features: {e}")
        
        return {}
    
    def get_feature_names(self) -> List[str]:
        """获取特征名称"""
        base_features = [f'price_{i}' for i in range(self.config.get('env', {}).get('window_size', 50))]
        
        technical_features = [
            'ma5_ratio', 'ma10_ratio', 'ma20_ratio', 'ma50_ratio',
            'rsi_norm', 'macd_norm', 'volatility', 'volume_ratio',
            'volume_std', 'price_momentum'
        ]
        
        return base_features + technical_features


class RealtimeDataExporter:
    """实时数据导出器"""
    
    def __init__(self, output_dir: str = "data/realtime"):
        self.output_dir = output_dir
        self.current_file = None
        self.writer = None
        self.record_count = 0
        self.max_records_per_file = 10000
        
    async def export_data(self, data: Dict[str, Any], data_type: str = "features"):
        """导出数据"""
        try:
            timestamp = datetime.now()
            filename = f"{data_type}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jsonl"
            filepath = f"{self.output_dir}/{filename}"
            
            with open(filepath, 'a') as f:
                json.dump({
                    **data,
                    'export_time': timestamp.isoformat()
                }, f)
                f.write('\n')
                
            self.record_count += 1
            
            if self.record_count >= self.max_records_per_file:
                self.record_count = 0
                
        except Exception as e:
            logger.error(f"Error exporting data: {e}")


# 使用示例
async def main():
    """主函数示例"""
    logging.basicConfig(level=logging.INFO)
    
    # 加载配置
    import yaml
    with open('configs/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # 创建实时处理器
    processor = RealtimeDataProcessor(config)
    
    try:
        # 启动处理器
        await processor.start()
        
        # 运行一段时间
        start_time = time.time()
        while time.time() - start_time < 30:  # 运行30秒
            stats = processor.get_stats()
            print(f"Stats: {stats}")
            await asyncio.sleep(5)
            
    except KeyboardInterrupt:
        logger.info("Stopping...")
    finally:
        await processor.stop()


if __name__ == "__main__":
    asyncio.run(main())