#!/usr/bin/env python3
"""
套利数据可视化工具
用于分析和展示套利机会数据
"""

import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np
from collections import defaultdict

# 设置绘图风格
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

class ArbitrageVisualizer:
    """套利数据可视化器"""
    
    def __init__(self, data_dir: str = "./data"):
        """
        初始化可视化器
        
        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = data_dir
        self.opportunities_file = os.path.join(data_dir, "opportunities.json")
        self.statistics_file = os.path.join(data_dir, "statistics.json")
        self.output_dir = os.path.join(data_dir, "charts")
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 加载数据
        self.opportunities_df = None
        self.statistics_df = None
        self.load_data()
    
    def load_data(self):
        """加载数据文件"""
        # 加载套利机会数据
        if os.path.exists(self.opportunities_file):
            with open(self.opportunities_file, 'r') as f:
                opportunities = json.load(f)
            
            if opportunities:
                self.opportunities_df = pd.DataFrame(opportunities)
                self.opportunities_df['timestamp'] = pd.to_datetime(self.opportunities_df['timestamp'])
                self.opportunities_df['net_profit_usdt'] = self.opportunities_df['net_profit'] / 1e6
                self.opportunities_df['gas_cost_usdt'] = self.opportunities_df['gas_cost'] / 1e6
                self.opportunities_df['amount_in_usdt'] = self.opportunities_df['amount_in'] / 1e6
                print(f"✅ 加载了 {len(self.opportunities_df)} 条套利机会记录")
            else:
                print("⚠️ 套利机会数据为空")
        else:
            print(f"⚠️ 未找到套利机会数据文件: {self.opportunities_file}")
        
        # 加载统计数据
        if os.path.exists(self.statistics_file):
            with open(self.statistics_file, 'r') as f:
                statistics = json.load(f)
            
            if statistics:
                self.statistics_df = pd.DataFrame(statistics)
                self.statistics_df['timestamp'] = pd.to_datetime(self.statistics_df['timestamp'])
                print(f"✅ 加载了 {len(self.statistics_df)} 条统计记录")
            else:
                print("⚠️ 统计数据为空")
        else:
            print(f"⚠️ 未找到统计数据文件: {self.statistics_file}")
    
    def plot_profit_distribution(self):
        """绘制利润分布图"""
        if self.opportunities_df is None or self.opportunities_df.empty:
            print("❌ 无数据可绘制利润分布图")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. 净利润直方图
        ax1 = axes[0, 0]
        ax1.hist(self.opportunities_df['net_profit_usdt'], bins=50, edgecolor='black', alpha=0.7)
        ax1.set_xlabel('净利润 (USDT)')
        ax1.set_ylabel('频次')
        ax1.set_title('净利润分布')
        ax1.axvline(self.opportunities_df['net_profit_usdt'].mean(), color='red', 
                   linestyle='--', label=f'平均值: {self.opportunities_df["net_profit_usdt"].mean():.2f}')
        ax1.legend()
        
        # 2. 利润率分布
        ax2 = axes[0, 1]
        ax2.hist(self.opportunities_df['profit_percentage'], bins=50, edgecolor='black', alpha=0.7)
        ax2.set_xlabel('利润率 (%)')
        ax2.set_ylabel('频次')
        ax2.set_title('利润率分布')
        ax2.axvline(self.opportunities_df['profit_percentage'].mean(), color='red', 
                   linestyle='--', label=f'平均值: {self.opportunities_df["profit_percentage"].mean():.2f}%')
        ax2.legend()
        
        # 3. Gas成本 vs 净利润
        ax3 = axes[1, 0]
        ax3.scatter(self.opportunities_df['gas_cost_usdt'], 
                   self.opportunities_df['net_profit_usdt'], alpha=0.5)
        ax3.set_xlabel('Gas 成本 (USDT)')
        ax3.set_ylabel('净利润 (USDT)')
        ax3.set_title('Gas 成本 vs 净利润')
        
        # 4. 累计利润曲线
        ax4 = axes[1, 1]
        cumulative_profit = self.opportunities_df.sort_values('timestamp')['net_profit_usdt'].cumsum()
        ax4.plot(range(len(cumulative_profit)), cumulative_profit, linewidth=2)
        ax4.set_xlabel('机会数量')
        ax4.set_ylabel('累计利润 (USDT)')
        ax4.set_title(f'累计利润曲线 (总计: {cumulative_profit.iloc[-1]:.2f} USDT)')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = os.path.join(self.output_dir, 'profit_distribution.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"📊 利润分布图已保存至: {output_path}")
        plt.show()
    
    def plot_dex_analysis(self):
        """分析 DEX 表现"""
        if self.opportunities_df is None or self.opportunities_df.empty:
            print("❌ 无数据可分析 DEX 表现")
            return
        
        # 提取 DEX 对信息
        dex_pairs = []
        for _, row in self.opportunities_df.iterrows():
            if len(row['dex_path']) >= 2:
                dex_pair = f"{row['dex_path'][0]} -> {row['dex_path'][1]}"
            else:
                dex_pair = row['dex_path'][0] if row['dex_path'] else "Unknown"
            dex_pairs.append(dex_pair)
        
        self.opportunities_df['dex_pair'] = dex_pairs
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. DEX 对机会数量
        ax1 = axes[0, 0]
        dex_counts = self.opportunities_df['dex_pair'].value_counts().head(10)
        dex_counts.plot(kind='bar', ax=ax1)
        ax1.set_xlabel('DEX 对')
        ax1.set_ylabel('机会数量')
        ax1.set_title('Top 10 DEX 对 - 机会数量')
        ax1.tick_params(axis='x', rotation=45)
        
        # 2. DEX 对平均利润
        ax2 = axes[0, 1]
        dex_avg_profit = self.opportunities_df.groupby('dex_pair')['net_profit_usdt'].mean().sort_values(ascending=False).head(10)
        dex_avg_profit.plot(kind='bar', ax=ax2)
        ax2.set_xlabel('DEX 对')
        ax2.set_ylabel('平均净利润 (USDT)')
        ax2.set_title('Top 10 DEX 对 - 平均利润')
        ax2.tick_params(axis='x', rotation=45)
        
        # 3. DEX 对总利润
        ax3 = axes[1, 0]
        dex_total_profit = self.opportunities_df.groupby('dex_pair')['net_profit_usdt'].sum().sort_values(ascending=False).head(10)
        dex_total_profit.plot(kind='bar', ax=ax3)
        ax3.set_xlabel('DEX 对')
        ax3.set_ylabel('总净利润 (USDT)')
        ax3.set_title('Top 10 DEX 对 - 总利润')
        ax3.tick_params(axis='x', rotation=45)
        
        # 4. DEX 对利润率箱线图
        ax4 = axes[1, 1]
        top_dex_pairs = self.opportunities_df['dex_pair'].value_counts().head(5).index
        data_for_box = [self.opportunities_df[self.opportunities_df['dex_pair'] == dex]['profit_percentage'].values 
                       for dex in top_dex_pairs]
        ax4.boxplot(data_for_box, labels=top_dex_pairs)
        ax4.set_xlabel('DEX 对')
        ax4.set_ylabel('利润率 (%)')
        ax4.set_title('Top 5 DEX 对 - 利润率分布')
        ax4.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        output_path = os.path.join(self.output_dir, 'dex_analysis.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"📊 DEX 分析图已保存至: {output_path}")
        plt.show()
    
    def plot_time_analysis(self):
        """时间序列分析"""
        if self.opportunities_df is None or self.opportunities_df.empty:
            print("❌ 无数据可进行时间序列分析")
            return
        
        # 按小时聚合数据
        self.opportunities_df['hour'] = self.opportunities_df['timestamp'].dt.floor('H')
        hourly_stats = self.opportunities_df.groupby('hour').agg({
            'net_profit_usdt': ['count', 'sum', 'mean'],
            'profit_percentage': 'mean',
            'gas_cost_usdt': 'mean'
        })
        
        fig, axes = plt.subplots(3, 1, figsize=(15, 12))
        
        # 1. 每小时机会数量
        ax1 = axes[0]
        ax1.plot(hourly_stats.index, hourly_stats[('net_profit_usdt', 'count')], 
                marker='o', linewidth=2, markersize=4)
        ax1.set_xlabel('时间')
        ax1.set_ylabel('机会数量')
        ax1.set_title('每小时套利机会数量')
        ax1.grid(True, alpha=0.3)
        
        # 2. 每小时总利润和平均利润
        ax2 = axes[1]
        ax2_twin = ax2.twinx()
        
        line1 = ax2.plot(hourly_stats.index, hourly_stats[('net_profit_usdt', 'sum')], 
                        color='blue', label='总利润', linewidth=2)
        line2 = ax2_twin.plot(hourly_stats.index, hourly_stats[('net_profit_usdt', 'mean')], 
                             color='red', label='平均利润', linewidth=2)
        
        ax2.set_xlabel('时间')
        ax2.set_ylabel('总利润 (USDT)', color='blue')
        ax2_twin.set_ylabel('平均利润 (USDT)', color='red')
        ax2.set_title('每小时利润统计')
        ax2.tick_params(axis='y', labelcolor='blue')
        ax2_twin.tick_params(axis='y', labelcolor='red')
        
        # 合并图例
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax2.legend(lines, labels, loc='upper left')
        ax2.grid(True, alpha=0.3)
        
        # 3. Gas 成本趋势
        ax3 = axes[2]
        ax3.plot(hourly_stats.index, hourly_stats[('gas_cost_usdt', 'mean')], 
                color='green', marker='o', linewidth=2, markersize=4)
        ax3.set_xlabel('时间')
        ax3.set_ylabel('平均 Gas 成本 (USDT)')
        ax3.set_title('Gas 成本趋势')
        ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = os.path.join(self.output_dir, 'time_analysis.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"📊 时间序列分析图已保存至: {output_path}")
        plt.show()
    
    def plot_token_analysis(self):
        """代币对分析"""
        if self.opportunities_df is None or self.opportunities_df.empty:
            print("❌ 无数据可分析代币对")
            return
        
        # 提取代币对信息
        token_pairs = []
        for _, row in self.opportunities_df.iterrows():
            if len(row['token_path']) >= 2:
                # 简化代币地址显示
                token_in = row['token_path'][0][-6:] if row['token_path'][0] else "?"
                token_out = row['token_path'][-1][-6:] if row['token_path'][-1] else "?"
                token_pair = f"{token_in} -> {token_out}"
            else:
                token_pair = "Unknown"
            token_pairs.append(token_pair)
        
        self.opportunities_df['token_pair'] = token_pairs
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. 代币对机会数量
        ax1 = axes[0, 0]
        token_counts = self.opportunities_df['token_pair'].value_counts().head(10)
        token_counts.plot(kind='bar', ax=ax1, color='skyblue')
        ax1.set_xlabel('代币对')
        ax1.set_ylabel('机会数量')
        ax1.set_title('Top 10 代币对 - 机会数量')
        ax1.tick_params(axis='x', rotation=45)
        
        # 2. 代币对平均利润
        ax2 = axes[0, 1]
        token_avg_profit = self.opportunities_df.groupby('token_pair')['net_profit_usdt'].mean().sort_values(ascending=False).head(10)
        token_avg_profit.plot(kind='bar', ax=ax2, color='lightgreen')
        ax2.set_xlabel('代币对')
        ax2.set_ylabel('平均净利润 (USDT)')
        ax2.set_title('Top 10 代币对 - 平均利润')
        ax2.tick_params(axis='x', rotation=45)
        
        # 3. 价格影响分析
        ax3 = axes[1, 0]
        ax3.scatter(self.opportunities_df['price_impact'], 
                   self.opportunities_df['net_profit_usdt'], alpha=0.5)
        ax3.set_xlabel('价格影响 (%)')
        ax3.set_ylabel('净利润 (USDT)')
        ax3.set_title('价格影响 vs 净利润')
        
        # 4. 投入金额 vs 利润率
        ax4 = axes[1, 1]
        ax4.scatter(self.opportunities_df['amount_in_usdt'], 
                   self.opportunities_df['profit_percentage'], alpha=0.5)
        ax4.set_xlabel('投入金额 (USDT)')
        ax4.set_ylabel('利润率 (%)')
        ax4.set_title('投入金额 vs 利润率')
        
        plt.tight_layout()
        output_path = os.path.join(self.output_dir, 'token_analysis.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"📊 代币对分析图已保存至: {output_path}")
        plt.show()
    
    def generate_report(self):
        """生成综合报告"""
        if self.opportunities_df is None or self.opportunities_df.empty:
            print("❌ 无数据可生成报告")
            return
        
        report = []
        report.append("=" * 60)
        report.append("套利机会分析报告")
        report.append("=" * 60)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 基本统计
        report.append("📊 基本统计")
        report.append("-" * 40)
        report.append(f"总机会数: {len(self.opportunities_df)}")
        report.append(f"时间范围: {self.opportunities_df['timestamp'].min()} 至 {self.opportunities_df['timestamp'].max()}")
        report.append(f"总潜在利润: {self.opportunities_df['net_profit_usdt'].sum():.2f} USDT")
        report.append(f"平均净利润: {self.opportunities_df['net_profit_usdt'].mean():.2f} USDT")
        report.append(f"最大净利润: {self.opportunities_df['net_profit_usdt'].max():.2f} USDT")
        report.append(f"最小净利润: {self.opportunities_df['net_profit_usdt'].min():.2f} USDT")
        report.append(f"平均利润率: {self.opportunities_df['profit_percentage'].mean():.2f}%")
        report.append(f"平均 Gas 成本: {self.opportunities_df['gas_cost_usdt'].mean():.2f} USDT")
        report.append("")
        
        # DEX 分析
        report.append("🏛️ DEX 分析")
        report.append("-" * 40)
        dex_stats = self.opportunities_df.groupby('dex_pair' if 'dex_pair' in self.opportunities_df else 'dex_path').agg({
            'net_profit_usdt': ['count', 'sum', 'mean']
        }).sort_values(('net_profit_usdt', 'sum'), ascending=False).head(5)
        
        for dex, stats in dex_stats.iterrows():
            report.append(f"{dex}:")
            report.append(f"  机会数: {stats[('net_profit_usdt', 'count')]:.0f}")
            report.append(f"  总利润: {stats[('net_profit_usdt', 'sum')]:.2f} USDT")
            report.append(f"  平均利润: {stats[('net_profit_usdt', 'mean')]:.2f} USDT")
        report.append("")
        
        # 时间分析
        report.append("⏰ 时间分析")
        report.append("-" * 40)
        self.opportunities_df['hour_of_day'] = self.opportunities_df['timestamp'].dt.hour
        hourly_avg = self.opportunities_df.groupby('hour_of_day')['net_profit_usdt'].mean()
        best_hour = hourly_avg.idxmax()
        worst_hour = hourly_avg.idxmin()
        report.append(f"最佳时段: {best_hour}:00 (平均利润 {hourly_avg[best_hour]:.2f} USDT)")
        report.append(f"最差时段: {worst_hour}:00 (平均利润 {hourly_avg[worst_hour]:.2f} USDT)")
        report.append("")
        
        # 保存报告
        report_text = "\n".join(report)
        report_path = os.path.join(self.output_dir, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        print(report_text)
        print(f"\n📄 报告已保存至: {report_path}")
        
        return report_text
    
    def run_all_analysis(self):
        """运行所有分析"""
        print("🚀 开始运行套利数据分析...")
        print("=" * 60)
        
        if self.opportunities_df is None or self.opportunities_df.empty:
            print("❌ 没有可用的数据进行分析")
            print("请确保机器人已运行并生成了数据文件")
            return
        
        print(f"📊 分析 {len(self.opportunities_df)} 条套利机会记录")
        print("=" * 60)
        
        # 生成所有图表
        print("\n1. 生成利润分布图...")
        self.plot_profit_distribution()
        
        print("\n2. 生成 DEX 分析图...")
        self.plot_dex_analysis()
        
        print("\n3. 生成时间序列分析图...")
        self.plot_time_analysis()
        
        print("\n4. 生成代币对分析图...")
        self.plot_token_analysis()
        
        print("\n5. 生成综合报告...")
        self.generate_report()
        
        print("\n✅ 所有分析完成！")
        print(f"📁 结果保存在: {self.output_dir}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='套利数据可视化工具')
    parser.add_argument('--data-dir', type=str, default='./data', 
                       help='数据目录路径')
    parser.add_argument('--chart', type=str, choices=['profit', 'dex', 'time', 'token', 'all'],
                       default='all', help='要生成的图表类型')
    
    args = parser.parse_args()
    
    # 创建可视化器
    visualizer = ArbitrageVisualizer(args.data_dir)
    
    # 根据参数生成图表
    if args.chart == 'all':
        visualizer.run_all_analysis()
    elif args.chart == 'profit':
        visualizer.plot_profit_distribution()
    elif args.chart == 'dex':
        visualizer.plot_dex_analysis()
    elif args.chart == 'time':
        visualizer.plot_time_analysis()
    elif args.chart == 'token':
        visualizer.plot_token_analysis()

if __name__ == "__main__":
    main()