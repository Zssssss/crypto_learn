#!/usr/bin/env python3
"""
套利监听机器人启动脚本
提供简单的命令行界面和配置检查
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def check_environment():
    """检查环境配置"""
    print("🔍 检查环境配置...")
    
    # 检查Python版本
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("❌ Python版本过低，需要 Python 3.8+")
        return False
    print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 检查必要的目录
    dirs_to_create = ['./logs', './data', './data/charts']
    for dir_path in dirs_to_create:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    print("✅ 目录结构已创建")
    
    # 检查.env文件
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            print("⚠️ 未找到 .env 文件，将从 .env.example 创建")
            import shutil
            shutil.copy('.env.example', '.env')
            print("📝 请编辑 .env 文件配置必要的参数")
            return False
        else:
            print("❌ 未找到 .env 或 .env.example 文件")
            return False
    print("✅ 配置文件存在")
    
    # 检查关键配置
    rpc_url = os.getenv("RPC_URL")
    if not rpc_url:
        print("❌ RPC_URL 未配置")
        return False
    print(f"✅ RPC URL: {rpc_url[:30]}...")
    
    return True

def install_dependencies():
    """安装依赖"""
    print("\n📦 安装依赖包...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError:
        print("❌ 依赖安装失败")
        return False

def run_bot(mode='monitor'):
    """运行机器人"""
    print("\n🚀 启动套利机器人...")
    print("=" * 60)
    
    # 选择运行的脚本
    if mode == 'advanced':
        script_name = "arbitrage_bot_advanced.py"
        version = "高级版"
    elif mode == 'optimized':
        script_name = "arbitrage_bot_optimized.py"
        version = "优化版"
    else:
        script_name = "arbitrage_bot.py"
        version = "基础版"
    
    if mode == 'monitor':
        # 监听模式
        print(f"📡 运行模式: 监听模式（{version}）")
        print("💡 提示: 按 Ctrl+C 停止运行")
        print("=" * 60)
        
        if mode == 'advanced':
            print("🔥 高级版功能:")
            print("  ✅ 6个DEX支持")
            print("  ✅ 16个代币")
            print("  ✅ 直接套利 + 三角套利")
            print("  ✅ 超低检测阈值 (0.01%)")
            print("  ✅ 更快扫描 (0.5秒)")
            print("  ✅ 更低门槛 (0.1 USDT)")
        elif mode == 'optimized':
            print("🔥 优化版功能:")
            print("  ✅ 4个DEX支持")
            print("  ✅ 10个代币对")
            print("  ✅ 异步并行扫描")
            print("  ✅ 更低检测阈值 (0.05%)")
            print("  ✅ 优化Gas估算")
        else:
            print("🔥 基础功能:")
            print("  ✅ Uniswap V2/V3支持")
            print("  ✅ 跨DEX套利")
            print("  ✅ 实时价格监控")
            print("  ✅ 机会记录和分析")
        print("=" * 60)
        
        try:
            subprocess.run([sys.executable, script_name])
        except KeyboardInterrupt:
            print("\n\n👋 机器人已停止")
    
    elif mode == 'visualize':
        # 可视化模式
        print("📊 运行数据可视化...")
        subprocess.run([sys.executable, "visualizer.py"])
    
    elif mode == 'test':
        # 测试模式
        print(f"🧪 运行测试模式（{version}）...")
        # 设置测试环境变量
        os.environ['SCAN_INTERVAL'] = '0.5'
        os.environ['MIN_PROFIT_USDT'] = '0.05'
        os.environ['MIN_PRICE_DIFF_PCT'] = '0.005'
        print(f"📝 使用测试参数: 扫描间隔=0.5秒, 最小利润=0.05 USDT, 最小价差=0.005%")
        
        try:
            subprocess.run([sys.executable, script_name])
        except KeyboardInterrupt:
            print("\n\n👋 测试完成")
    
    elif mode == 'backtest':
        # 回测模式
        print("📈 运行回测模式...")
        print("⚠️ 回测功能开发中...")

def show_status():
    """显示状态信息"""
    print("\n📊 系统状态")
    print("=" * 60)
    
    # 检查日志文件
    log_file = "./logs/arbitrage.log"
    if os.path.exists(log_file):
        size = os.path.getsize(log_file) / 1024  # KB
        print(f"📄 日志文件: {size:.2f} KB")
        
        # 显示最后几行日志
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                last_lines = lines[-5:] if len(lines) >= 5 else lines
                print("\n最近日志:")
                for line in last_lines:
                    print(f"  {line.strip()}")
        except:
            pass
    else:
        print("📄 日志文件: 未创建")
    
    # 检查数据文件
    data_file = "./data/opportunities.json"
    if os.path.exists(data_file):
        size = os.path.getsize(data_file) / 1024  # KB
        print(f"\n📊 数据文件: {size:.2f} KB")
        
        # 统计机会数量
        try:
            import json
            with open(data_file, 'r') as f:
                data = json.load(f)
                print(f"💰 记录的套利机会: {len(data)} 个")
                
                if data:
                    # 计算总利润
                    total_profit = sum(opp.get('net_profit', 0) for opp in data) / 1e6
                    print(f"💵 潜在总利润: {total_profit:.2f} USDT")
        except:
            pass
    else:
        print("\n📊 数据文件: 未创建")
    
    print("=" * 60)

def clean_data():
    """清理数据文件"""
    print("\n🧹 清理数据文件...")
    
    files_to_clean = [
        "./logs/arbitrage.log",
        "./data/opportunities.json",
        "./data/statistics.json"
    ]
    
    for file_path in files_to_clean:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"✅ 已删除: {file_path}")
            except Exception as e:
                print(f"❌ 删除失败: {file_path} - {e}")
        else:
            print(f"⏭️ 文件不存在: {file_path}")
    
    print("✅ 清理完成")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='套利机器人启动脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python start.py                    # 启动标准版监听机器人
  python start.py --test             # 测试模式运行
  python start.py --visualize        # 运行数据可视化
  python start.py --status           # 查看系统状态
  python start.py --clean            # 清理数据文件
  python start.py --install          # 安装依赖包
  python start.py --config           # 显示配置信息
        """
    )
    
    parser.add_argument('--test', action='store_true',
                       help='测试模式运行（使用测试参数）')
    parser.add_argument('--visualize', action='store_true',
                       help='运行数据可视化')
    parser.add_argument('--status', action='store_true',
                       help='显示系统状态')
    parser.add_argument('--clean', action='store_true',
                       help='清理数据文件')
    parser.add_argument('--install', action='store_true',
                       help='安装依赖包')
    parser.add_argument('--check', action='store_true',
                       help='仅检查环境配置')
    parser.add_argument('--config', action='store_true',
                       help='显示配置信息')
    parser.add_argument('--backtest', action='store_true',
                       help='运行回测模式')
    parser.add_argument('--enhanced', action='store_true',
                       help='运行增强版机器人（需要额外依赖）')
    
    args = parser.parse_args()
    
    # 显示标题
    print("=" * 60)
    print("🤖 套利机器人 基础版")
    print("📡 监听模式 - 专注于价格监控和机会分析")
    print("=" * 60)
    
    # 处理命令
    if args.install:
        install_dependencies()
        return
    
    if args.clean:
        clean_data()
        return
    
    if args.status:
        show_status()
        return
    
    if args.config:
        show_config()
        return
    
    # 检查环境
    if not check_environment():
        print("\n❌ 环境检查失败，请修复问题后重试")
        return
    
    if args.check:
        print("\n✅ 环境检查通过")
        return
    
    # 运行机器人
    if args.visualize:
        run_bot('visualize')
    elif args.test:
        run_bot('test')
    elif args.backtest:
        run_bot('backtest')
    else:
        run_bot('monitor')

def show_config():
    """显示配置信息"""
    print("\n⚙️ 配置信息")
    print("=" * 60)
    
    print("📋 基础版配置:")
    # 读取.env文件
    if os.path.exists('.env'):
        from dotenv import dotenv_values
        config = dotenv_values('.env')
        
        print(f"\n🌐 RPC URL: {config.get('RPC_URL', 'N/A')[:50]}...")
        print(f"💰 套利金额: ${config.get('AMOUNT_USDT', '100')} USDT")
        print(f"💵 最小利润: ${config.get('MIN_NET_PROFIT_USDT', '0.5')} USDT")
        print(f"⏱️ 扫描间隔: {config.get('SCAN_INTERVAL', '1')}秒")
        print(f"📝 详细日志: {config.get('VERBOSE_LOGGING', 'true')}")
    else:
        print("⚠️ 配置文件.env未找到")
    
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 程序已退出")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()