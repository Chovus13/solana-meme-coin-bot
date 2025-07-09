"""
Logging utility module for structured logging throughout the trading bot
"""

import logging
import logging.handlers
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        """Format log record as JSON"""
        log_entry = {
            'timestamp': datetime.utcfromtimestamp(record.created).isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry)

class TradingBotFilter(logging.Filter):
    """Filter to add trading bot context to log records"""
    
    def __init__(self, bot_instance_id: str = None):
        super().__init__()
        self.bot_instance_id = bot_instance_id or f"bot_{int(datetime.now().timestamp())}"
    
    def filter(self, record):
        """Add bot context to record"""
        record.bot_instance_id = self.bot_instance_id
        return True

class ColoredConsoleFormatter(logging.Formatter):
    """Colored console formatter for better readability"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        """Format with colors"""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Format the message
        formatted = super().format(record)
        
        # Add color
        return f"{color}{formatted}{reset}"

def setup_logger(name: str, level: str = 'INFO', log_dir: str = 'logs') -> logging.Logger:
    """Setup structured logging for the trading bot"""
    
    # Create logger
    logger = logging.getLogger(name)
    #logger.setLevel(getattr(logging, level.upper()))
    actual_log_level_enum = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(actual_log_level_enum)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Bot instance ID for this session
    bot_instance_id = f"bot_{int(datetime.now().timestamp())}"
    
    # Add bot filter
    bot_filter = TradingBotFilter(bot_instance_id)
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    # ENSURE THE CONSOLE HANDLER'S LEVEL MATCHES THE LOGGER'S LEVEL:
    console_handler.setLevel(actual_log_level_enum)  # <--- MODIFIED THIS LINE
    console_formatter = ColoredConsoleFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(bot_filter)
    logger.addHandler(console_handler)
    
    # File handler for all logs (rotating)
    file_handler = logging.handlers.RotatingFileHandler(
        log_path / 'trading_bot.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(bot_filter)
    logger.addHandler(file_handler)
    
    # JSON handler for structured logs
    json_handler = logging.handlers.RotatingFileHandler(
        log_path / 'trading_bot.json',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    json_handler.setLevel(logging.DEBUG)
    json_formatter = JsonFormatter()
    json_handler.setFormatter(json_formatter)
    json_handler.addFilter(bot_filter)
    logger.addHandler(json_handler)
    
    # Error-only handler
    error_handler = logging.handlers.RotatingFileHandler(
        log_path / 'errors.log',
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d\n'
        'Message: %(message)s\n'
        '%(pathname)s:%(lineno)d\n'
        '----------------------------------------'
    )
    error_handler.setFormatter(error_formatter)
    error_handler.addFilter(bot_filter)
    logger.addHandler(error_handler)
    
    # Performance log handler
    perf_handler = logging.FileHandler(log_path / 'performance.log')
    perf_handler.setLevel(logging.INFO)
    perf_formatter = JsonFormatter()
    perf_handler.setFormatter(perf_formatter)
    perf_handler.addFilter(lambda record: getattr(record, 'log_type', None) == 'performance')
    logger.addHandler(perf_handler)
    
    # Trading activity log handler
    trading_handler = logging.FileHandler(log_path / 'trading.log')
    trading_handler.setLevel(logging.INFO)
    trading_formatter = JsonFormatter()
    trading_handler.setFormatter(trading_formatter)
    trading_handler.addFilter(lambda record: getattr(record, 'log_type', None) == 'trading')
    logger.addHandler(trading_handler)
    
    #logger.info(f"Logger '{name}' initialized with instance ID: {bot_instance_id}")
    
    # ... (other handlers like file_handler, json_handler should already be DEBUG or appropriate) ...
    # Add a test print and a debug log at the end of setup_logger:
    print(f"[DEBUG] Logger '{{name}}' configured by setup_logger with actual effective level: {{logging.getLevelName(logger.getEffectiveLevel())}}")
    logger.info(f"Logger '{{name}}' initialized (instance: {{bot_instance_id}}) at effective level {{logging.getLevelName(logger.getEffectiveLevel())}}.")
    logger.debug(f"This is a test DEBUG message from logger '{{name}}' to confirm DEBUG output.")
    
    return logger

def log_performance(logger: logging.Logger, operation: str, duration: float, 
                   metadata: Optional[Dict[str, Any]] = None):
    """Log performance metrics"""
    extra_fields = {
        'log_type': 'performance',
        'operation': operation,
        'duration_ms': duration * 1000,
        'metadata': metadata or {}
    }
    
    # Create a custom log record
    record = logger.makeRecord(
        logger.name, logging.INFO, '', 0,
        f"Performance: {operation} took {duration:.3f}s",
        (), None
    )
    record.extra_fields = extra_fields
    logger.handle(record)

def log_trading_activity(logger: logging.Logger, activity_type: str, 
                        data: Dict[str, Any]):
    """Log trading activities"""
    extra_fields = {
        'log_type': 'trading',
        'activity_type': activity_type,
        'data': data,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    record = logger.makeRecord(
        logger.name, logging.INFO, '', 0,
        f"Trading: {activity_type}",
        (), None
    )
    record.extra_fields = extra_fields
    logger.handle(record)

def log_token_discovery(logger: logging.Logger, symbol: str, source: str, 
                       confidence: float, metadata: Optional[Dict[str, Any]] = None):
    """Log token discoveries"""
    data = {
        'symbol': symbol,
        'source': source,
        'confidence': confidence,
        'metadata': metadata or {}
    }
    log_trading_activity(logger, 'token_discovery', data)

def log_token_analysis(logger: logging.Logger, symbol: str, safety_score: int,
                      recommendation: str, metadata: Optional[Dict[str, Any]] = None):
    """Log token analyses"""
    data = {
        'symbol': symbol,
        'safety_score': safety_score,
        'recommendation': recommendation,
        'metadata': metadata or {}
    }
    log_trading_activity(logger, 'token_analysis', data)

def log_trade_execution(logger: logging.Logger, trade_type: str, symbol: str,
                       amount: float, price: float, success: bool,
                       metadata: Optional[Dict[str, Any]] = None):
    """Log trade executions"""
    data = {
        'trade_type': trade_type,
        'symbol': symbol,
        'amount': amount,
        'price': price,
        'success': success,
        'metadata': metadata or {}
    }
    log_trading_activity(logger, 'trade_execution', data)

def log_position_update(logger: logging.Logger, symbol: str, action: str,
                       pnl: Optional[float] = None, metadata: Optional[Dict[str, Any]] = None):
    """Log position updates"""
    data = {
        'symbol': symbol,
        'action': action,
        'pnl': pnl,
        'metadata': metadata or {}
    }
    log_trading_activity(logger, 'position_update', data)

def log_error_with_context(logger: logging.Logger, error: Exception, 
                          context: Dict[str, Any]):
    """Log errors with additional context"""
    extra_fields = {
        'log_type': 'error',
        'error_type': type(error).__name__,
        'error_message': str(error),
        'context': context
    }
    
    record = logger.makeRecord(
        logger.name, logging.ERROR, '', 0,
        f"Error: {type(error).__name__}: {str(error)}",
        (), (type(error), error, error.__traceback__)
    )
    record.extra_fields = extra_fields
    logger.handle(record)

class PerformanceTimer:
    """Context manager for timing operations"""
    
    def __init__(self, logger: logging.Logger, operation: str, 
                 metadata: Optional[Dict[str, Any]] = None):
        self.logger = logger
        self.operation = operation
        self.metadata = metadata or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now().timestamp()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = datetime.now().timestamp() - self.start_time
            log_performance(self.logger, self.operation, duration, self.metadata)

class LoggingMixin:
    """Mixin class to add logging capabilities to other classes"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def log_performance(self, operation: str, duration: float, 
                       metadata: Optional[Dict[str, Any]] = None):
        """Log performance metrics"""
        log_performance(self.logger, operation, duration, metadata)
    
    def log_trading_activity(self, activity_type: str, data: Dict[str, Any]):
        """Log trading activities"""
        log_trading_activity(self.logger, activity_type, data)
    
    def log_error_with_context(self, error: Exception, context: Dict[str, Any]):
        """Log errors with context"""
        log_error_with_context(self.logger, error, context)
    
    def performance_timer(self, operation: str, 
                         metadata: Optional[Dict[str, Any]] = None):
        """Get performance timer context manager"""
        return PerformanceTimer(self.logger, operation, metadata)

def configure_third_party_loggers():
    """Configure third-party library loggers to reduce noise"""
    
    # Reduce noise from common libraries
    noisy_loggers = [
        'urllib3.connectionpool',
        'aiohttp.access',
        'asyncio',
        'websockets.server',
        'websockets.protocol'
    ]
    
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    # Set specific levels for crypto libraries
    logging.getLogger('solana').setLevel(logging.INFO)
    logging.getLogger('spl').setLevel(logging.INFO)

def setup_application_logging(app_name: str = 'SolanaMemecoinBot', 
                            log_level: str = 'INFO',
                            log_dir: str = 'logs') -> logging.Logger:
    """Setup complete application logging"""
    
    # Configure third-party loggers first
    configure_third_party_loggers()
    
    # Setup main application logger
    main_logger = setup_logger(app_name, log_level, log_dir)
    
    # Log application startup
    # --- Make PRAW loggers verbose for debugging ---
    import logging # Ensure logging is imported in this file if not already
    logging.getLogger("praw").setLevel(logging.DEBUG)
    logging.getLogger("prawcore").setLevel(logging.DEBUG)
    # Use the logger instance from your function if available, otherwise print:
    # logger.info("PRAW and PRAWCORE loggers set to DEBUG level.") 
    print("[DEBUG] utils.logger: PRAW and PRAWCORE loggers set to DEBUG level.")
    # --- End PRAW logger verbosity ---
    main_logger.info(f"Application logging initialized")
    main_logger.info(f"Log level: {log_level}")
    main_logger.info(f"Log directory: {log_dir}")
    
    return main_logger

def get_log_stats(log_dir: str = 'logs') -> Dict[str, Any]:
    """Get logging statistics"""
    try:
        log_path = Path(log_dir)
        
        if not log_path.exists():
            return {'error': 'Log directory does not exist'}
        
        stats = {}
        
        # Get file sizes
        for log_file in log_path.glob('*.log'):
            stats[log_file.name] = {
                'size_bytes': log_file.stat().st_size,
                'modified': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
            }
        
        # Get total log directory size
        total_size = sum(f.stat().st_size for f in log_path.glob('*') if f.is_file())
        stats['total_size_bytes'] = total_size
        
        return stats
    
    except Exception as e:
        return {'error': str(e)}

def cleanup_old_logs(log_dir: str = 'logs', days_to_keep: int = 30):
    """Clean up old log files"""
    try:
        log_path = Path(log_dir)
        
        if not log_path.exists():
            return
        
        cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
        
        for log_file in log_path.glob('*.log*'):
            if log_file.stat().st_mtime < cutoff_time:
                log_file.unlink()
                print(f"Deleted old log file: {log_file}")
    
    except Exception as e:
        print(f"Error cleaning up logs: {e}")

def setup_logging(app_name: str = 'SolanaMemecoinBot', 
                  log_level: str = 'INFO', 
                  log_dir: str = 'logs'):
    """Passes arguments to the main setup_application_logging function."""
    return setup_application_logging(app_name=app_name, log_level=log_level, log_dir=log_dir)