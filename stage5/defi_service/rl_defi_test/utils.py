"""
工具函数模块
包含技术指标计算、数据预处理、性能评估等功能
"""
import numpy as np
import pandas as pd
import talib
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    添加技术指标到DataFrame
    
    Args:
        df: 包含OHLCV数据的DataFrame
    
    Returns:
        添加技术指标后的DataFrame
    """
    df = df.copy()
    
    # 价格数据
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    volume = df['volume'].values
    
    # 移动平均线
    df['ma5'] = talib.SMA(close, timeperiod=5)
    df['ma10'] = talib.SMA(close, timeperiod=10)
    df['ma20'] = talib.SMA(close, timeperiod=20)
    df['ma50'] = talib.SMA(close, timeperiod=50)
    
    # 指数移动平均线
    df['ema12'] = talib.EMA(close, timeperiod=12)
    df['ema26'] = talib.EMA(close, timeperiod=26)
    
    # 相对强弱指标
    df['rsi'] = talib.RSI(close, timeperiod=14)
    
    # 移动平均收敛散度
    df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(
        close, fastperiod=12, slowperiod=26, signalperiod=9
    )
    
    # 布林带
    df['bb_upper'], df['bb_middle'], df['bb_lower'] = talib.BBANDS(
        close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
    )
    
    # 平均真实波幅
    df['atr'] = talib.ATR(high, low, close, timeperiod=14)
    
    # 随机指标
    df['stoch_k'], df['stoch_d'] = talib.STOCH(
        high, low, close, fastk_period=14, slowk_period=3, slowd_period=3
    )
    
    # 威廉指标
    df['willr'] = talib.WILLR(high, low, close, timeperiod=14)
    
    # 成交量指标
    df['volume_ma'] = talib.SMA(volume, timeperiod=20)
    df['volume_ratio'] = volume / df['volume_ma']
    
    # 价格动量
    df['price_change'] = df['close'].pct_change()
    df['price_momentum'] = df['price_change'].rolling(window=10).mean()
    
    # 波动率
    df['volatility'] = df['price_change'].rolling(window=20).std()
    
    # 处理NaN值
    df = df.fillna(method='ffill').fillna(0)
    
    return df


def normalize_data(df: pd.DataFrame, method: str = 'minmax') -> pd.DataFrame:
    """
    标准化数据
    
    Args:
        df: 待标准化的DataFrame
        method: 标准化方法 ('minmax', 'zscore', 'robust')
    
    Returns:
        标准化后的DataFrame
    """
    df_norm = df.copy()
    
    # 选择数值列
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    if method == 'minmax':
        # Min-Max标准化
        for col in numeric_cols:
            min_val = df[col].min()
            max_val = df[col].max()
            if max_val > min_val:
                df_norm[col] = (df[col] - min_val) / (max_val - min_val)
            else:
                df_norm[col] = 0
    
    elif method == 'zscore':
        # Z-score标准化
        for col in numeric_cols:
            mean = df[col].mean()
            std = df[col].std()
            if std > 0:
                df_norm[col] = (df[col] - mean) / std
            else:
                df_norm[col] = 0
    
    elif method == 'robust':
        # Robust标准化
        for col in numeric_cols:
            median = df[col].median()
            mad = np.median(np.abs(df[col] - median))
            if mad > 0:
                df_norm[col] = (df[col] - median) / mad
            else:
                df_norm[col] = 0
    
    return df_norm


def calculate_performance_metrics(trades: List[Dict], initial_balance: float) -> Dict[str, float]:
    """
    计算性能指标
    
    Args:
        trades: 交易记录列表
        initial_balance: 初始资金
    
    Returns:
        性能指标字典
    """
    if not trades:
        return {
            'total_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'total_trades': 0
        }
    
    # 提取盈亏数据
    pnl_list = [trade['pnl'] for trade in trades]
    cumulative_pnl = np.cumsum(pnl_list)
    cumulative_returns = cumulative_pnl / initial_balance
    
    # 总收益
    total_return = cumulative_pnl[-1] / initial_balance
    
    # 夏普比率
    if len(pnl_list) > 1:
        returns = np.array(pnl_list) / initial_balance
        excess_returns = returns - 0.02 / 252  # 假设无风险利率2%
        sharpe_ratio = np.sqrt(252) * np.mean(excess_returns) / np.std(excess_returns) if np.std(excess_returns) > 0 else 0
    else:
        sharpe_ratio = 0
    
    # 最大回撤
    running_max = np.maximum.accumulate(cumulative_returns)
    drawdowns = cumulative_returns - running_max
    max_drawdown = np.min(drawdowns)
    
    # 胜率
   
    winning_trades = [pnl for pnl in pnl_list if pnl > 0]
    win_rate = len(winning_trades) / len(pnl_list) if pnl_list else 0
    
    # 盈利因子
    gross_profit = sum([pnl for pnl in pnl_list if pnl > 0])
    gross_loss = abs(sum([pnl for pnl in pnl_list if pnl < 0]))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    return {
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': abs(max_drawdown),
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_trades': len(trades),
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'net_profit': sum(pnl_list)
    }


def plot_trading_results(trades: List[Dict], df: pd.DataFrame, save_path: Optional[str] = None):
    """
    绘制交易结果图表
    
    Args:
        trades: 交易记录
        df: 价格数据
        save_path: 保存路径
    """
    fig, axes = plt.subplots(3, 1, figsize=(15, 12))
    
    # 价格图表
    axes[0].plot(df.index, df['close'], label='Close Price', color='black')
    
    # 标记买卖点
    long_entries = [t for t in trades if t['side'] == 1]
    short_entries = [t for t in trades if t['side'] == -1]
    exits = [t for t in trades if 'exit_price' in t]
    
    if long_entries:
        axes[0].scatter([t['entry_idx'] for t in long_entries], 
                       [t['entry_price'] for t in long_entries], 
                       color='green', marker='^', s=100, label='Long Entry')
    
    if short_entries:
        axes[0].scatter([t['entry_idx'] for t in short_entries], 
                       [t['entry_price'] for t in short_entries], 
                       color='red', marker='v', s=100, label='Short Entry')
    
    axes[0].set_title('Trading Signals')
    axes[0].legend()
    axes[0].grid(True)
    
    # 累计收益
    if trades:
        pnl_list = [t['pnl'] for t in trades]
        cumulative_pnl = np.cumsum(pnl_list)
        axes[1].plot(cumulative_pnl, color='blue')
        axes[1].set_title('Cumulative PnL')
        axes[1].grid(True)
    
    # 回撤
    if trades:
        pnl_list = [t['pnl'] for t in trades]
        cumulative_pnl = np.cumsum(pnl_list)
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = cumulative_pnl - running_max
        axes[2].fill_between(range(len(drawdown)), drawdown, 0, color='red', alpha=0.3)
        axes[2].set_title('Drawdown')
        axes[2].grid(True)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()


def create_features(df: pd.DataFrame, window_size: int = 20) -> np.ndarray:
    """
    创建特征向量
    
    Args:
        df: 数据DataFrame
        window_size: 窗口大小
    
    Returns:
        特征数组
    """
    features = []
    
    # 价格特征
    close_prices = df['close'].values[-window_size:]
    high_prices = df['high'].values[-window_size:]
    low_prices = df['low'].values[-window_size:]
    volumes = df['volume'].values[-window_size:]
    
    if len(close_prices) < window_size:
        # 填充数据
        padding = window_size - len(close_prices)
        close_prices = np.pad(close_prices, (padding, 0), mode='edge')
        high_prices = np.pad(high_prices, (padding, 0), mode='edge')
        low_prices = np.pad(low_prices, (padding, 0), mode='edge')
        volumes = np.pad(volumes, (padding, 0), mode='edge')
    
    # 标准化价格
    latest_price = close_prices[-1]
    if latest_price > 0:
        price_features = close_prices / latest_price - 1.0
    else:
        price_features = np.zeros(window_size)
    
    features.extend(price_features)
    
    # 技术指标特征
    technical_features = []
    
    # 移动平均线特征
    if 'ma10' in df.columns and 'ma50' in df.columns:
        ma10 = df['ma10'].iloc[-1] if not pd.isna(df['ma10'].iloc[-1]) else latest_price
        ma50 = df['ma50'].iloc[-1] if not pd.isna(df['ma50'].iloc[-1]) else latest_price
        technical_features.extend([
            (ma10 - latest_price) / latest_price,
            (ma50 - latest_price) / latest_price,
            (ma10 - ma50) / latest_price
        ])
    
    # RSI特征
    if 'rsi' in df.columns:
        rsi = df['rsi'].iloc[-1] if not pd.isna(df['rsi'].iloc[-1]) else 50
        technical_features.append(rsi / 100.0)
    
    # MACD特征
    if 'macd' in df.columns:
        macd = df['macd'].iloc[-1] if not pd.isna(df['macd'].iloc[-1]) else 0
        technical_features.append(macd / latest_price)
    
    # 波动率特征
    if len(close_prices) > 1:
        returns = np.diff(close_prices) / close_prices[:-1]
        volatility = np.std(returns)
        technical_features.append(volatility)
    
    # 成交量特征
    if len(volumes) > 0:
        volume_features = [
            volumes[-1] / np.mean(volumes) if np.mean(volumes) > 0 else 1.0,
            np.std(volumes) / np.mean(volumes) if np.mean(volumes) > 0 else 0.0
        ]
        technical_features.extend(volume_features)
    
    features.extend(technical_features)
    
    return np.array(features, dtype=np.float32)


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """
    设置日志配置
    
    Args:
        log_level: 日志级别
        log_file: 日志文件路径
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    if log_file:
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    else:
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format=log_format
        )


def save_model_info(model_path: str, config: Dict, metrics: Dict):
    """
    保存模型信息
    
    Args:
        model_path: 模型路径
        config: 配置字典
        metrics: 性能指标
    """
    info = {
        "model_path": model_path,
        "config": config,
        "metrics": metrics,
        "timestamp": datetime.now().isoformat()
    }
    
    info_path = f"{model_path}_info.json"
    import json
    with open(info_path, 'w') as f:
        json.dump(info, f, indent=2, default=str)
    
    logger.info(f"Model info saved to {info_path}")


if __name__ == "__main__":
    # 测试工具函数
    import os
    
    # 设置日志
    setup_logging()
    
    # 测试数据加载和特征创建
    if os.path.exists("data/sample_data.csv"):
        from data_loader import load_csv
        df = load_csv("data/sample_data.csv")
        df = add_technical_indicators(df)
        
        print(f"Data shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        
        # 测试标准化
        df_norm = normalize_data(df[['close', 'volume', 'rsi']])
        print(f"Normalized data shape: {df_norm.shape}")
        
        # 测试特征创建
        features = create_features(df.tail(50))
        print(f"Feature vector shape: {features.shape}")
    else:
        print("Sample data file not found")