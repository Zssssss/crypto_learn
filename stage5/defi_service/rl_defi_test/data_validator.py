"""
数据验证和质量检查模块
用于验证Hyperliquid数据的质量和完整性
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class DataQualityValidator:
    """数据质量验证器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.validation_rules = self._load_validation_rules()
    
    def _load_validation_rules(self) -> Dict[str, Any]:
        """加载验证规则"""
        return {
            'price_range': {
                'min_price': 0.01,
                'max_price': 1000000,
                'max_price_change': 0.5  # 50% max change
            },
            'volume_range': {
                'min_volume': 0,
                'max_volume': 1e12
            },
            'time_range': {
                'max_gap_minutes': 5,
                'max_future_data': 1
            },
            'data_completeness': {
                'min_required_columns': ['timestamp', 'open', 'high', 'low', 'close', 'volume'],
                'max_missing_ratio': 0.05
            }
        }
    
    def validate_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """验证DataFrame"""
        if df.empty:
            return {
                'valid': False,
                'errors': ['Empty DataFrame'],
                'warnings': [],
                'stats': {}
            }
        
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'stats': {}
        }
        
        # 检查必需列
        missing_columns = self._check_required_columns(df)
        if missing_columns:
            validation_result['errors'].extend([
                f"Missing columns: {', '.join(missing_columns)}"
            ])
            validation_result['valid'] = False
        
        # 检查数据类型
        type_errors = self._check_data_types(df)
        if type_errors:
            validation_result['errors'].extend(type_errors)
            validation_result['valid'] = False
        
        # 检查价格数据
        price_errors = self._check_price_data(df)
        if price_errors:
            validation_result['errors'].extend(price_errors)
            validation_result['valid'] = False
        
        # 检查成交量数据
        volume_errors = self._check_volume_data(df)
        if volume_errors:
            validation_result['errors'].extend(volume_errors)
            validation_result['valid'] = False
        
        # 检查时间序列
        time_errors = self._check_time_series(df)
        if time_errors:
            validation_result['warnings'].extend(time_errors)
        
        # 检查异常值
        outlier_warnings = self._check_outliers(df)
        if outlier_warnings:
            validation_result['warnings'].extend(outlier_warnings)
        
        # 计算统计信息
        validation_result['stats'] = self._calculate_stats(df)
        
        return validation_result
    
    def _check_required_columns(self, df: pd.DataFrame) -> List[str]:
        """检查必需列"""
        required_columns = self.validation_rules['data_completeness']['min_required_columns']
        missing_columns = [col for col in required_columns if col not in df.columns]
        return missing_columns
    
    def _check_data_types(self, df: pd.DataFrame) -> List[str]:
        """检查数据类型"""
        errors = []
        
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    errors.append(f"Column {col} must be numeric")
        
        if 'timestamp' in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                try:
                    pd.to_datetime(df['timestamp'])
                except:
                    errors.append("Timestamp column must be convertible to datetime")
        
        return errors
    
    def _check_price_data(self, df: pd.DataFrame) -> List[str]:
        """检查价格数据"""
        errors = []
        
        price_rules = self.validation_rules['price_range']
        
        # 检查价格范围
        for col in ['open', 'high', 'low', 'close']:
            if col in df.columns:
                if (df[col] <= 0).any():
                    errors.append(f"{col} must be positive")
                if (df[col] > price_rules['max_price']).any():
                    errors.append(f"{col} exceeds maximum price")
        
        # 检查高低价关系
        if all(col in df.columns for col in ['high', 'low']):
            invalid_rows = df[df['high'] < df['low']]
            if not invalid_rows.empty:
                errors.append("High price must be >= low price")
        
        # 检查价格变化
        if 'close' in df.columns:
            price_changes = df['close'].pct_change().abs()
            extreme_changes = price_changes > price_rules['max_price_change']
            if extreme_changes.any():
                count = extreme_changes.sum()
                errors.append(f"Found {count} extreme price changes (>50%)")
        
        return errors
    
    def _check_volume_data(self, df: pd.DataFrame) -> List[str]:
        """检查成交量数据"""
        errors = []
        
        if 'volume' not in df.columns:
            return errors
        
        volume_rules = self.validation_rules['volume_range']
        
        # 检查成交量范围
        if (df['volume'] < volume_rules['min_volume']).any():
            errors.append("Volume contains negative values")
        
        if (df['volume'] > volume_rules['max_volume']).any():
            errors.append("Volume exceeds maximum")
        
        return errors
    
    def _check_time_series(self, df: pd.DataFrame) -> List[str]:
        """检查时间序列"""
        warnings = []
        
        if 'timestamp' not in df.columns:
            return warnings
        
        # 检查时间顺序
        if not df['timestamp'].is_monotonic_increasing:
            warnings.append("Timestamps are not monotonically increasing")
        
        # 检查时间间隔
        time_diff = df['timestamp'].diff()
        median_diff = time_diff.median()
        
        if pd.isna(median_diff):
            return warnings
        
        # 检查时间间隔一致性
        max_gap = timedelta(minutes=self.validation_rules['time_range']['max_gap_minutes'])
        large_gaps = time_diff > max_gap
        
        if large_gaps.any():
            count = large_gaps.sum()
            warnings.append(f"Found {count} large time gaps")
        
        # 检查未来数据
        now = datetime.now()
        future_data = df['timestamp'] > now
        
        if future_data.any():
            count = future_data.sum()
            warnings.append(f"Found {count} future timestamps")
        
        return warnings
    
    def _check_outliers(self, df: pd.DataFrame) -> List[str]:
        """检查异常值"""
        warnings = []
        
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        
        for col in numeric_columns:
            if col not in df.columns:
                continue
            
            # 使用IQR方法检测异常值
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 3 * IQR
            upper_bound = Q3 + 3 * IQR
            
            outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
            
            if not outliers.empty:
                outlier_ratio = len(outliers) / len(df)
                if outlier_ratio > 0.01:  # 超过1%的异常值
                    warnings.append(f"{col} has {outlier_ratio:.2%} outliers")
        
        return warnings
    
    def _calculate_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算统计信息"""
        stats = {
            'total_rows': len(df),
            'date_range': None,
            'missing_values': {},
            'price_stats': {},
            'volume_stats': {}
        }
        
        if df.empty:
            return stats
        
        # 日期范围
        if 'timestamp' in df.columns:
            stats['date_range'] = {
                'start': df['timestamp'].min().isoformat(),
                'end': df['timestamp'].max().isoformat()
            }
        
        # 缺失值统计
        for col in df.columns:
            missing_count = df[col].isnull().sum()
            if missing_count > 0:
                stats['missing_values'][col] = {
                    'count': int(missing_count),
                    'ratio': float(missing_count / len(df))
                }
        
        # 价格统计
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in df.columns:
                stats['price_stats'][col] = {
                    'min': float(df[col].min()),
                    'max': float(df[col].max()),
                    'mean': float(df[col].mean()),
                    'std': float(df[col].std())
                }
        
        # 成交量统计
        if 'volume' in df.columns:
            stats['volume_stats'] = {
                'min': float(df['volume'].min()),
                'max': float(df['volume'].max()),
                'mean': float(df['volume'].mean()),
                'std': float(df['volume'].std()),
                'total': float(df['volume'].sum())
            }
        
        return stats
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理数据"""
        if df.empty:
            return df
        
        cleaned_df = df.copy()
        
        # 移除重复行
        cleaned_df = cleaned_df.drop_duplicates(subset=['timestamp'], keep='first')
        
        # 排序
        cleaned_df = cleaned_df.sort_values('timestamp').reset_index(drop=True)
        
        # 处理缺失值
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in cleaned_df.columns:
                # 前向填充
                cleaned_df[col] = cleaned_df[col].fillna(method='ffill')
                # 后向填充
                cleaned_df[col] = cleaned_df[col].fillna(method='bfill')
                # 如果还有缺失值，用中位数填充
                cleaned_df[col] = cleaned_df[col].fillna(cleaned_df[col].median())
        
        # 处理异常值
        cleaned_df = self._handle_outliers(cleaned_df)
        
        # 确保价格关系正确
        cleaned_df = self._fix_price_relationships(cleaned_df)
        
        return cleaned_df
    
    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理异常值"""
        df_clean = df.copy()
        
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        
        for col in numeric_columns:
            if col not in df_clean.columns:
                continue
            
            # 使用IQR方法处理异常值
            Q1 = df_clean[col].quantile(0.25)
            Q3 = df_clean[col].quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 3 * IQR
            upper_bound = Q3 + 3 * IQR
            
            # 用边界值替换异常值
            mask = (df_clean[col] < lower_bound) | (df_clean[col] > upper_bound)
            df_clean.loc[mask, col] = df_clean[col].median()
        
        return df_clean
    
    def _fix_price_relationships(self, df: pd.DataFrame) -> pd.DataFrame:
        """修复价格关系"""
        df_fixed = df.copy()
        
        if all(col in df_fixed.columns for col in ['high', 'low', 'close']):
            # 确保high >= max(open, close, low)
            df_fixed['high'] = df_fixed[['high', 'open', 'close', 'low']].axis=1).max(axis=1)
            
            # 确保low <= min(open, close, high)
            df_fixed['low'] = df_fixed[['low', 'open', 'close', 'high']].min(axis=1)
        
        return df_fixed


class DataHealthMonitor:
    """数据健康监控器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.validator = DataQualityValidator(config)
        self.health_history = []
        self.thresholds = {
            'max_error_rate': 0.05,
            'max_missing_ratio': 0.1,
            'max_outlier_ratio': 0.05
        }
    
    def monitor_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """监控数据质量"""
        validation_result = self.validator.validate_dataframe(df)
        
        health_score = self._calculate_health_score(validation_result)
        
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'health_score': health_score,
            'validation_result': validation_result,
            'recommendations': self._generate_recommendations(validation_result)
        }
        
        self.health_history.append(health_report)
        
        # 保留最近100条记录
        if len(self.health_history) > 100:
            self.health_history.pop(0)
        
        return health_report
    
    def _calculate_health_score(self, validation_result: Dict[str, Any]) -> float:
        """计算健康分数"""
        if not validation_result['valid']:
            return 0.0
        
        score = 100.0
        
        # 根据警告扣分
        warnings = validation_result.get('warnings', [])
        for warning in warnings:
            if 'outlier' in warning.lower():
                score -= 10.0
            elif 'gap' in warning.lower():
                score -= 5.0
            elif 'future' in warning.lower():
                score -= 15.0
        
        # 根据缺失值比例扣分
        stats = validation_result.get('stats', {})
        missing_values = stats.get('missing_values', {})
        if missing_values:
            total_missing = sum(mv['count'] for mv in missing_values.values())
            total_cells = stats.get('total_rows', 1) * len(missing_values)
            missing_ratio = total_missing / total_cells
            
            if missing_ratio > self.thresholds['max_missing_ratio']:
                score -= (missing_ratio * 100)
        
        return max(0.0, score)
    
    def _generate_recommendations(self, validation_result: Dict[str, Any]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        errors = validation_result.get('errors', [])
        warnings = validation_result.get('warnings', [])
        
        if errors:
            recommendations.append("Address critical data issues before using for training")
        
        if any('outlier' in str(w).lower() for w in warnings):
            recommendations.append("Consider outlier detection and treatment")
        
        if any('gap' in str(w).lower() for w in warnings):
            recommendations.append("Consider data interpolation for time gaps")
        
        if any('missing' in str(e).lower() for e in errors):
            recommendations.append("Ensure all required columns are present")
        
        return recommendations
    
    def get_health_trend(self) -> Dict[str, Any]:
        """获取健康趋势"""
        if not self.health_history:
            return {'trend': 'no_data', 'average_score': 0.0}
        
        scores = [h['health_score'] for h in self.health_history]
        
        return {
            'trend': 'improving' if scores[-1] > scores[0] else 'declining',
            'average_score': np.mean(scores),
            'latest_score': scores[-1],
            'sample_size': len(scores)
        }


# 使用示例
def main():
    """主函数示例"""
    logging.basicConfig(level=logging.INFO)
    
    # 加载配置
    import yaml
    with open('configs/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # 创建验证器
    validator = DataQualityValidator(config)
    monitor = DataHealthMonitor(config)
    
    # 加载示例数据
    import pandas as pd
    try:
        df = pd.read_csv('data/sample_data.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 验证数据
        result = validator.validate_dataframe(df)
        print("Validation Result:")
        print(json.dumps(result, indent=2, default=str))
        
        # 清理数据
        cleaned_df = validator.clean_data(df)
        
        # 监控数据质量
        health_report = monitor.monitor_data_quality(cleaned_df)
        print("\nHealth Report:")
        print(json.dumps(health_report, indent=2, default=str))
        
    except FileNotFoundError:
        print("Sample data file not found")


if __name__ == "__main__":
    main()