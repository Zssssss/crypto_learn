"""
数据加载模块
用于加载和预处理CSV数据
"""
import pandas as pd
import numpy as np
from typing import Optional, Tuple
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def load_csv(filepath: str) -> pd.DataFrame:
    """从CSV文件加载数据"""
    try:
        df = pd.read_csv(filepath)
        logger.info(f"Loaded {len(df)} records from {filepath}")
        return df
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error loading CSV: {e}")
        return pd.DataFrame()


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """准备数据用于训练"""
    if df.empty:
        return df
    
    # 确保时间戳格式正确
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # 确保数值列是数值类型
    numeric_columns = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 按时间排序
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # 填充缺失值
    df = df.fillna(method='ffill').fillna(0)
    
    return df


def validate_data(df: pd.DataFrame) -> bool:
    """验证数据有效性"""
    if df.empty:
        return False
    
    # 检查必需列
    required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        logger.warning(f"Missing columns: {missing_columns}")
        return False
    
    # 检查NaN值
    if df[required_columns].isnull().any().any():
        logger.warning("Data contains NaN values")
        return False
    
    # 检查价格关系
    if 'high' in df.columns and 'low' in df.columns:
        invalid = df[df['high'] < df['low']]
        if not invalid.empty:
            logger.warning("Invalid price relationship: high < low")
            return False
    
    # 检查非负值
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns and (df[col] < 0).any():
            logger.warning(f"Negative values in {col}")
            return False
    
    return True


def split_data(df: pd.DataFrame, train_ratio: float = 0.7, val_ratio: float = 0.15) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """分割数据集"""
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    total_len = len(df)
    train_len = int(total_len * train_ratio)
    val_len = int(total_len * val_ratio)
    
    train_df = df[:train_len]
    val_df = df[train_len:train_len + val_len]
    test_df = df[train_len + val_len:]
    
    logger.info(f"Data split - Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
    
    return train_df, val_df, test_df


def create_sample_data(filepath: str, num_records: int = 1000):
    """创建示例数据用于测试"""
    # 生成时间戳
    start_time = datetime.now() - timedelta(days=30)
    timestamps = [start_time + timedelta(minutes=i) for i in range(num_records)]
    
    # 生成价格数据
    np.random.seed(42)
    base_price = 40000
    
    prices = [base_price]
    for i in range(1, num_records):
        change = np.random.normal(0, 0.001)
        new_price = max(prices[-1] * (1 + change), 1000)  # 确保价格不会太低
        prices.append(new_price)
    
    # 创建OHLCV数据
    data = []
    for i, (timestamp, close) in enumerate(zip(timestamps, prices)):
        volatility = abs(np.random.normal(0, 0.002))
        high = close * (1 + volatility)
        low = close * (1 - volatility)
        open_price = prices[i-1] if i > 0 else close
        volume = abs(np.random.normal(1000, 200))
        
        data.append({
            'timestamp': timestamp,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
            'symbol': 'BTC-USD'
        })
    
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)
    logger.info(f"Created sample data with {len(df)} records at {filepath}")
    return df