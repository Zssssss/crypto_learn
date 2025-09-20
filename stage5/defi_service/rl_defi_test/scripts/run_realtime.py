#!/usr/bin/env python3
"""
实时交易脚本
用于运行训练好的模型进行实时交易
"""
import asyncio
import yaml
import logging
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import signal
import sys

from stable_baselines3 import DQN, PPO

from env.trading_env import TradingEnv
from realtime_adapter import HyperliquidRealtimeAdapter, subscribe_klines
from utils import add_technical_indicators

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/realtime_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RealtimeTrader:
    """实时交易类"""
    
    def __init__(self, config_path: str, model_path: str, model_type: str = "dqn"):
        self.config_path = config_path
        self.model_path = model_path
        self.model_type = model_type.lower()
        
        # 加载配置
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # 加载模型
        if self.model_type == "dqn":
            self.model = DQN.load(model_path)
        elif self.model_type == "ppo":
            self.model = PPO.load(model_path)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
        
        # 初始化数据缓冲区
        self.data_buffer = []
        self.window_size = self.config["env"]["window_size"]
        
        # 初始化适配器
        self.adapter = HyperliquidRealtimeAdapter(
            self.config["realtime"]["websocket_url"]
        )
        
        self.running = False
        
    async def initialize_data(self):
        """初始化历史数据"""
        logger.info("Initializing historical data...")
        
        # 获取历史数据
        from data_loader import create_sample_data
        
        try:
            df = create_sample_data()
            df = add_technical_indicators(df)
            
            # 填充数据缓冲区
            self.data_buffer = df.tail(self.window_size).to_dict('records')
            logger.info(f"Initialized with {len(self.data_buffer)} data points")
            
        except Exception as e:
            logger.error(f"Failed to initialize data: {e}")
            
    def prepare_observation(self) -> np.ndarray:
        """准备观察向量"""
        if len(self.data_buffer) < self.window_size:
            logger.warning("Insufficient data for observation")
            return None
            
        # 创建DataFrame
        df = pd.DataFrame(self.data_buffer)
        
        # 获取价格窗口
        closes = df["close"].values[-self.window_size:]
        if len(closes) < self.window_size:
            return None
            
        # 标准化价格
        base = closes[-1]
        norm_closes = closes / base - 1.0
        
        # 账户状态特征
        account_features = np.array([
            0.0,  # position_side
            0.0,  # position
            closes[-1],  # entry_price
            self.config["account"]["initial_balance"],  # balance
            0.0,  # unrealized_pnl
            0.0   # margin_ratio
        ])
        
        return np.concatenate([norm_closes, account_features])
        
    async def execute_trade(self, action: int, current_price: float):
        """执行交易"""
        actions = {
            0: "HOLD",
            1: "OPEN_LONG",
            2: "OPEN_SHORT",
            3: "CLOSE_POSITION"
        }
        
        logger.info(f"Action: {actions[action]} at price {current_price}")
        
        # 记录交易
        trade_record = {
            "timestamp": datetime.now(),
            "action": actions[action],
            "price": current_price,
            "balance": self.config["account"]["initial_balance"]
        }
        
        return trade_record
        
    async def run_trading_loop(self):
        """运行实时交易循环"""
        logger.info("Starting real-time trading loop...")
        
        await self.initialize_data()
        
        # 连接到WebSocket
        if not await self.adapter.connect():
            logger.error("Failed to connect to WebSocket")
            return
            
        try:
            # 订阅K线数据
            symbol = self.config["realtime"]["symbol"]
            async for kline in self.adapter.subscribe_klines(symbol, "1m"):
                # 添加新数据
                self.data_buffer.append(kline)
                
                # 保持缓冲区大小
                if len(self.data_buffer) > self.window_size * 2:
                    self.data_buffer = self.data_buffer[-self.window_size:]
                
                # 准备观察
                obs = self.prepare_observation()
                if obs is None:
                    continue
                
                # 预测动作
                action, _ = self.model.predict(obs, deterministic=True)
                
                # 执行交易
                await self.execute_trade(action, kline["close"])
                
        except KeyboardInterrupt:
            logger.info("Trading loop interrupted by user")
        except Exception as e:
            logger.error(f"Error in trading loop: {e}")
        finally:
            await self.adapter.disconnect()
            
    def stop(self):
        """停止交易"""
        self.running = False
        logger.info("Stopping realtime trader...")


def signal_handler(signum, frame):
    """信号处理"""
    logger.info("Received interrupt signal, shutting down...")
    sys.exit(0)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Run realtime trading")
    parser.add_argument("--config", type=str, default="configs/config.yaml", help="Config file path")
    parser.add_argument("--model", type=str, required=True, help="Model file path")
    parser.add_argument("--model-type", type=str, choices=["dqn", "ppo"], default="dqn", help="Model type")
    
    args = parser.parse_args()
    
    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建交易者
    trader = RealtimeTrader(args.config, args.model, args.model_type)
    
    try:
        await trader.run_trading_loop()
    except KeyboardInterrupt:
        trader.stop()


if __name__ == "__main__":
    asyncio.run(main())