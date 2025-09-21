#!/usr/bin/env python3
"""
Hyperliquid数据获取脚本
用于从Hyperliquid链上获取历史数据并处理为训练格式
"""
import asyncio
import argparse
import logging
import sys
from pathlib import Path
import yaml
import pandas as pd

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from hyperliquid_data_provider import HyperliquidDataManager
from data_formatter import DataFormatter
from data_validator import DataQualityValidator, DataHealthMonitor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "INFO"):
    """设置日志"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


async def fetch_historical_data(
    days_back: int = 30,
    symbol: str = "BTC-USD",
    interval: str = "1m",
    output_dir: str = "data/hyperliquid"
):
    """获取历史数据"""
    logger.info(f"Fetching {days_back} days of {symbol} data...")
    
    # 创建输出目录
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 加载配置
    config_path = Path("configs/config.yaml")
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    else:
        config = {
            'realtime': {'symbol': symbol},
            'data': {'interval': interval}
        }
    
    # 创建数据管理器
    manager = HyperliquidDataManager(str(config_path))
    
    try:
        # 获取并处理数据
        processed_df = await manager.fetch_and_process_data(
            days_back=days_back,
            save_path=f"{output_dir}/raw_data_{symbol}_{days_back}d.csv"
        )
        
        if processed_df.empty:
            logger.error("No data retrieved")
            return None
        
        logger.info(f"Retrieved {len(processed_df)} records")
        
        # 验证数据质量
        validator = DataQualityValidator(config)
        health_monitor = DataHealthMonitor(config)
        
        validation_result = validator.validate_dataframe(processed_df)
        health_report = health_monitor.monitor_data_quality(processed_df)
        
        # 保存验证报告
        with open(f"{output_dir}/validation_report.json", 'w') as f:
            import json
            json.dump({
                'validation': validation_result,
                'health': health_report
            }, f, indent=2, default=str)
        
        # 清理数据
        cleaned_df = validator.clean_data(processed_df)
        
        # 保存清理后的数据
        cleaned_df.to_csv(f"{output_dir}/cleaned_data_{symbol}_{days_back}d.csv", index=False)
        
        # 格式化数据用于训练
        formatter = DataFormatter(config)
        X_train, X_val, X_test, y_train, y_val, y_test = formatter.prepare_training_dataset(
            cleaned_df, test_size=0.2, val_size=0.1
        )
        
        if X_train.size > 0:
            # 保存训练数据
            np.savez(
                f"{output_dir}/training_data_{symbol}_{days_back}d.npz",
                X_train=X_train, X_val=X_val, X_test=X_test,
                y_train=y_train, y_val=y_val, y_test=y_test
            )
            
            logger.info("Training data prepared and saved")
            logger.info(f"Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")
        
        return cleaned_df
        
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return None
    
    finally:
        await manager.provider.close()


async def fetch_multiple_symbols(
    symbols: List[str],
    days_back: int = 30,
    output_dir: str = "data/hyperliquid"
):
    """获取多个交易对的数据"""
    results = {}
    
    for symbol in symbols:
        logger.info(f"Processing symbol: {symbol}")
        try:
            df = await fetch_historical_data(
                days_back=days_back,
                symbol=symbol,
                output_dir=f"{output_dir}/{symbol}"
            )
            if df is not None:
                results[symbol] = df
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
    
    return results


def generate_summary_report(results: Dict[str, pd.DataFrame], output_dir: str):
    """生成汇总报告"""
    report = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'symbols': list(results.keys()),
        'data_summary': {}
    }
    
    for symbol, df in results.items():
        if df is not None and not df.empty:
            report['data_summary'][symbol] = {
                'total_records': len(df),
                'date_range': {
                    'start': df['timestamp'].min().isoformat(),
                    'end': df['timestamp'].max().isoformat()
                },
                'price_range': {
                    'min': float(df['close'].min()),
                    'max': float(df['close'].max()),
                    'mean': float(df['close'].mean())
                },
                'volume_stats': {
                    'total': float(df['volume'].sum()),
                    'mean': float(df['volume'].mean())
                }
            }
    
    # 保存报告
    with open(f"{output_dir}/summary_report.json", 'w') as f:
        import json
        json.dump(report, f, indent=2, default=str)
    
    return report


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Fetch Hyperliquid data')
    parser.add_argument('--days', type=int, default=30, help='Days of data to fetch')
    parser.add_argument('--symbol', type=str, default='BTC-USD', help='Trading symbol')
    parser.add_argument('--symbols', type=str, nargs='+', help='Multiple symbols')
    parser.add_argument('--output', type=str, default='data/hyperliquid', help='Output directory')
    parser.add_argument('--log-level', type=str, default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    
    if args.symbols:
        # 获取多个交易对
        results = await fetch_multiple_symbols(
            args.symbols,
            days_back=args.days,
            output_dir=args.output
        )
        
        if results:
            report = generate_summary_report(results, args.output)
            logger.info("Summary report generated")
            logger.info(f"Processed {len(results)} symbols")
    
    else:
        # 获取单个交易对
        df = await fetch_historical_data(
            days_back=args.days,
            symbol=args.symbol,
            output_dir=args.output
        )
        
        if df is not None:
            logger.info("Data fetch completed successfully")
        else:
            logger.error("Data fetch failed")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())