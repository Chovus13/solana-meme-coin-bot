"""
Configuration settings for the Solana Memecoin Trading Bot
"""
import os
from dataclasses import dataclass
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

@dataclass
class APIKeys:
    """API keys configuration"""
    # Twitter API
    twitter_bearer_token: Optional[str] = os.getenv('TWITTER_BEARER_TOKEN')
    twitter_api_key: Optional[str] = os.getenv('TWITTER_API_KEY')
    twitter_api_secret: Optional[str] = os.getenv('TWITTER_API_SECRET')
    twitter_access_token: Optional[str] = os.getenv('TWITTER_ACCESS_TOKEN')
    twitter_access_secret: Optional[str] = os.getenv('TWITTER_ACCESS_SECRET')
    
    # Reddit API
    reddit_client_id: Optional[str] = os.getenv('REDDIT_CLIENT_ID')
    reddit_client_secret: Optional[str] = os.getenv('REDDIT_CLIENT_SECRET')
    reddit_username: Optional[str] = os.getenv('REDDIT_USERNAME')
    reddit_password: Optional[str] = os.getenv('REDDIT_PASSWORD')
    reddit_user_agent: str = "SolanaMemecoinBot/1.0"
    
    # Discord API
    discord_token: Optional[str] = os.getenv('DISCORD_TOKEN')
    
    # Telegram API
    telegram_api_id: Optional[str] = os.getenv('TELEGRAM_API_ID')
    telegram_api_hash: Optional[str] = os.getenv('TELEGRAM_API_HASH')
    telegram_phone: Optional[str] = os.getenv('TELEGRAM_PHONE')
    
    # TikTok (unofficial)
    tiktok_session_id: Optional[str] = os.getenv('TIKTOK_SESSION_ID')
    
    # Solana
    solana_rpc_url: str = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
    solana_private_key: Optional[str] = os.getenv('SOLANA_PRIVATE_KEY')
    
    # GMGN API
    gmgn_api_key: Optional[str] = os.getenv('GMGN_API_KEY')
    
    # Notification services
    notification_webhook: Optional[str] = os.getenv('NOTIFICATION_WEBHOOK')

@dataclass
class TradingConfig:
    """Trading configuration parameters"""
    # Buy settings
    buy_amount_sol: float = 1.5  # Amount in SOL to buy
    max_buy_amount_sol: float = 2.0
    min_buy_amount_sol: float = 1.0
    
    # Slippage settings
    buy_slippage: float = 0.20  # 20%
    sell_slippage: float = 0.25  # 25%
    
    # Profit/Loss settings
    take_profit_multiplier: float = 10.0  # 10x profit target
    moonbag_percentage: float = 0.15  # Keep 15% as moonbag
    stop_loss_percentage: float = 0.50  # 50% stop loss
    
    # Priority fees
    priority_fee_lamports: int = 10000  # 0.00001 SOL
    
    # Position sizing
    max_positions: int = 5
    position_size_percentage: float = 0.2  # 20% of available balance per position

@dataclass
class MonitoringConfig:
    """Social media monitoring configuration"""
    # Keywords to monitor
    memecoin_keywords: List[str] = None
    exclude_keywords: List[str] = None
    
    # Social media accounts to monitor
    twitter_accounts: List[str] = None
    reddit_subreddits: List[str] = None
    discord_channels: List[str] = None
    telegram_channels: List[str] = None
    
    # Monitoring intervals
    twitter_check_interval: int = 30  # seconds
    reddit_check_interval: int = 60  # seconds
    discord_check_interval: int = 45  # seconds
    telegram_check_interval: int = 60  # seconds
    tiktok_check_interval: int = 300  # seconds
    
    def __post_init__(self):
        if self.memecoin_keywords is None:
            self.memecoin_keywords = [
                '$', 'token', 'coin', 'pump', 'moon', 'gem', 'memecoin', 
                'solana', 'sol', 'CA:', 'contract', 'address', 'pumpfun',
                'raydium', 'jupiter', 'dex', 'launched', 'presale', 'fair launch'
            ]
        
        if self.exclude_keywords is None:
            self.exclude_keywords = [
                'scam', 'rug', 'fake', 'honeypot', 'warning', 'caution',
                'avoid', 'dangerous', 'suspicious', 'fraud'
            ]
        
        if self.twitter_accounts is None:
            self.twitter_accounts = [
                '@SolanaFloor', '@SolanaMobile', '@solana', '@SolanaSpaces',
                '@RaydiumProtocol', '@JupiterExchange', '@pumpdotfun'
            ]
        
        if self.reddit_subreddits is None:
            self.reddit_subreddits = [
                'solana', 'SolanaMemeCoins', 'cryptomoonshots', 
                'CryptoGemDiscovery', 'memecoin'
            ]

@dataclass
class FilterConfig:
    """Token filtering configuration"""
    # Solsniffer score requirements
    min_safety_score: int = 80
    
    # Market cap requirements
    min_market_cap: float = 10000  # $10K
    max_market_cap: float = 1000000  # $1M
    
    # Liquidity requirements
    min_liquidity: float = 5000  # $5K
    require_locked_liquidity: bool = True
    
    # Contract requirements
    require_verified_contract: bool = True
    require_disabled_mint: bool = True
    
    # Social sentiment requirements
    min_social_score: float = 0.6  # 60% positive sentiment
    min_mentions_count: int = 5
    
    # Technical analysis requirements
    min_volume_24h: float = 1000  # $1K daily volume
    max_age_hours: int = 24  # Only tokens less than 24 hours old

@dataclass
class WebConfig:
    """Web interface configuration"""
    host: str = '0.0.0.0'
    port: int = 8080
    debug: bool = False
    secret_key: str = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

@dataclass
class DatabaseConfig:
    """Database configuration"""
    database_path: str = 'data/trading_bot.db'
    backup_interval_hours: int = 6

# Global configuration instances
api_keys = APIKeys()
trading_config = TradingConfig()
monitoring_config = MonitoringConfig()
filter_config = FilterConfig()
web_config = WebConfig()
database_config = DatabaseConfig()

# Validation function
def validate_config() -> bool:
    """Validate essential configuration settings"""
    errors = []
    
    # Check essential API keys
    if not api_keys.solana_private_key:
        errors.append("SOLANA_PRIVATE_KEY is required")
    
    if not api_keys.twitter_bearer_token:
        errors.append("TWITTER_BEARER_TOKEN is recommended for Twitter monitoring")
    
    # Check trading config
    if trading_config.buy_amount_sol <= 0:
        errors.append("buy_amount_sol must be positive")
    
    if trading_config.take_profit_multiplier <= 1:
        errors.append("take_profit_multiplier must be greater than 1")
    
    # Check filter config
    if filter_config.min_safety_score < 0 or filter_config.min_safety_score > 100:
        errors.append("min_safety_score must be between 0 and 100")
    
    if errors:
        print("Configuration errors found:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True
