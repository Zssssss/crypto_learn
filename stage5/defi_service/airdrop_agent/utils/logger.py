"""日志工具模块"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from colorama import init, Fore, Style
from rich.console import Console
from rich.logging import RichHandler

init()

class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.MAGENTA,
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, '')
        reset = Style.RESET_ALL
        
        # 格式化时间
        record.asctime = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # 添加颜色
        record.levelname = f"{log_color}{record.levelname}{reset}"
        record.msg = f"{log_color}{record.msg}{reset}"
        
        return super().format(record)

def setup_logger(name: str, level: str = "INFO", log_file: str = None) -> logging.Logger:
    """设置日志器
    
    Args:
        name: 日志器名称
        level: 日志级别
        log_file: 日志文件路径，为None则不写入文件
        
    Returns:
        logging.Logger: 配置好的日志器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 清除现有处理器
    logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = ColoredFormatter(
        '[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

# 创建全局日志器
logger = setup_logger("airdrop_agent", log_file="logs/airdrop_agent.log")

# Rich控制台用于美观输出
console = Console()

def print_banner():
    """打印启动横幅"""
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                    🪂 Airdrop Hunter Agent                    ║
    ║              自动空投狩猎 & 交互执行系统                      ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")