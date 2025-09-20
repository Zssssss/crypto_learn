import pandas as pd
import numpy as np
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def load_csv(path: str, **kwargs) -> pd.DataFrame:
    """
    加载CSV数据文件
    
    Args:
        path: CSV文件路径
        **kwargs: pandas.read_csv的其他参数
    
    Returns:
        DataFrame包含OHLCV数据
    
    Raises:
        ValueError: 如果缺少必要的列
    """
    try:
        df = pd.read_csv(path, **kwargs)
        
        # 标准化列名
        column_mapping = {
            'Timestamp': 'timestamp',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }
        
        # 重命名列
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # 检查必要列
        required_columns = ["timestamp", "open", "high", "low", "close", "volume"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # 确保数据类型正确
        numeric_columns = ["open", "high", "low", "close", "volume"]
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 处理时间戳
        if df['timestamp'].dtype == 'object':
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 按时间排序
        df = df.sort_values("timestamp").reset_index(drop=True)
        
        # 检查数据完整性
        if df.isnull().any().any():
            logger.warning("Data contains NaN values, filling forward...")
            df = df.fillna(method='ffill')
        
        logger.info(f"Loaded {len(df)} rows of data from {path}")
        return df
        
    except Exception as e:
        logger.error(f"Error loading CSV: {str(e)}")
        raise


def prepare_data(df: pd.DataFrame, window_size: int = 50) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    准备训练数据
    
    Args:
        df: 原始数据DataFrame
        window_size: 窗口大小
    
    Returns:
        处理后的DataFrame和特征数组
    """
    # 计算技术指标
    from utils import add_technical_indicators
    
    df = add_technical_indicators(df)
    
    # 创建特征
    features = []
    for i in range(window_size, len(df)):
        window = df.iloc[i-window_size:i]
        feature = create_features(window)
        features.append(feature)
    
    features = np.array(features)
    
    # 移除前window_size行
    df = df.iloc[window_size:].reset_index(drop=True)
    
    return df, features


def create_features(window: pd.DataFrame) -> np.ndarray:
    """
    从窗口数据创建特征
    
    Args:
        window: 时间窗口数据
    
    Returns:
        特征数组
    """
    features = []
    
    # 价格特征
    close_prices = window['close'].values
    returns = np.diff(close_prices) / close_prices[:-1]
    
    # 基础统计特征
    features.extend([
        close_prices[-1],  # 最新价格
        np.mean(close_prices),  # 平均价格
        np.std(close_prices),   # 价格波动
        np.max(close_prices),   # 最高价
        np.min(close_prices),   # 最低价
    ])
    
    # 技术指标特征
    if 'rsi' in window.columns:
        features.append(window['rsi'].iloc[-1])
    if 'ma10' in window.columns:
        features.append(window['ma10'].iloc[-1])
    if 'ma50' in window.columns:
        features.append(window['ma50'].iloc[-1])
    if 'atr' in window.columns:
        features.append(window['atr'].iloc[-1])
    
    # 成交量特征
    volumes = window['volume'].values
    features.extend([
        volumes[-1],  # 最新成交量
        np.mean(volumes),  # 平均成交量
        np.std(volumes),   # 成交量波动
    ])
    
    # 价格动量
    if len(returns) > 0:
        features.extend([
            returns[-1],  # 最新收益率
            np.mean(returns),  # 平均收益率
            np.std(returns),   # 收益率波动
        ])
    
    return np.array(features)


def split_data(df: pd.DataFrame, train_ratio: float = 0.7, val_ratio: float = 0.15) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    分割数据集
    
    Args:
        df: 完整数据集
        train_ratio: 训练集比例
        val_ratio: 验证集比例
    
    Returns:
        训练集、验证集、测试集
    """
    n = len(df)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    
    train_df = df[:train_end].copy()
    val_df = df[train_end:val_end].copy()
    test_df = df[val_end:].copy()
    
    logger.info(f"Data split - Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
    
    return train_df, val_df, test_df


def validate_data(df: pd.DataFrame) -> bool:
    """
    验证数据质量
    
    Args:
        df: 待验证的DataFrame
    
    Returns:
        数据是否有效
    """
    if df is None or df.empty:
        logger.error("DataFrame is empty")
        return False
    
    # 检查价格数据
    price_columns = ['open', 'high', 'low', 'close']
    for col in price_columns:
        if (df[col] <= 0).any():
            logger.error(f"Invalid {col} values (<= 0)")
            return False
    
    # 检查高低价关系
    if not (df['high'] >= df['low']).all():
        logger.error("High price must be >= low price")
        return False
    
    # 检查时间戳
    if not df['timestamp'].is_monotonic_increasing:
        logger.error("Timestamps must be monotonically increasing")
        return False
    
    logger.info("Data validation passed")
    return True


if __name__ == "__main__":
    # 测试数据加载
    import os
    
    config_path = "configs/config.yaml"
    if os.path.exists(config_path):
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        csv_path = config['data']['csv_path']
        if os.path.exists(csv_path):
            df = load_csv(csv_path)
            print(f"Loaded {len(df)} rows")
            print(df.head())
            validate_data(df)
        else:
            print(f"CSV file not found: {csv_path}")
    else:
        print("Config file not found")