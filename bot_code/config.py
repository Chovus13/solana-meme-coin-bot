# bot_code/config.py

import os
from dataclasses import dataclass, field # Import field
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
    notification_webhook: Optional[str] = os.getenv('NOTIFICATION_WEBHOOK')


@dataclass
class TradingConfig:
    """Trading configuration parameters"""
    # Buy settings
    buy_amount_sol: float = float(os.getenv('BUY_AMOUNT_SOL', '0.5'))
    max_buy_amount_sol: float = 0.7 # Add from .env if needed
    min_buy_amount_sol: float = 0.3 # Add from .env if needed

    # Slippage settings
    buy_slippage: float = float(os.getenv('BUY_SLIPPAGE', '0.20'))  # 20%
    sell_slippage: float = float(os.getenv('SELL_SLIPPAGE', '0.25'))  # 25%

    # Profit/Loss settings
    take_profit_multiplier: float = float(os.getenv('TAKE_PROFIT_MULTIPLIER', '10.0'))  # 10x profit target
    moonbag_percentage: float = float(os.getenv('MOONBAG_PERCENTAGE', '0.15'))  # Keep 15% as moonbag
    stop_loss_percentage: float = float(os.getenv('STOP_LOSS_PERCENTAGE', '0.50'))  # 50% stop loss

    # Priority fees
    priority_fee_lamports: int = int(os.getenv('PRIORITY_FEE_LAMPORTS', '10000'))  # 0.00001 SOL

    # Position sizing
    max_positions: int = int(os.getenv('MAX_POSITIONS', '3'))
    position_size_percentage: float = float(os.getenv('POSITION_SIZE_PERCENTAGE', '0.2'))  # 20% of available balance per position

    # Risk management
    max_position_age_hours: int = int(os.getenv('MAX_POSITION_AGE_HOURS', '24'))
    max_daily_loss_percentage: float = float(os.getenv('MAX_DAILY_LOSS_PERCENTAGE', '0.10'))  # 10%
    emergency_stop_loss_percentage: float = float(os.getenv('EMERGENCY_STOP_LOSS_PERCENTAGE', '0.80'))  # 80%


@dataclass
class MonitoringConfig:
    """Social media monitoring configuration"""
    # Keywords to monitor
    memecoin_keywords: List[str] = field(default_factory=lambda: [
        '$', 'token', 'coin', 'pump', 'moon', 'gem', 'memecoin',
        'solana', 'sol', 'CA:', 'contract', 'address', 'pumpfun',
        'raydium', 'jupiter', 'dex', 'launched', 'presale', 'fair launch'
    ])
    exclude_keywords: List[str] = field(default_factory=lambda: [
        'scam', 'rug', 'fake', 'honeypot', 'warning', 'caution',
        'avoid', 'dangerous', 'suspicious', 'fraud'
    ])

    # Social media accounts to monitor
    twitter_usernames: Optional[List[str]] = None # Kept for backward compatibility if needed
    twitter_accounts: List[str] = field(default_factory=lambda: [ # Use this for UI
        '@SolanaFloor', '@SolanaMobile', '@solana', '@SolanaSpaces',
        '@RaydiumProtocol', '@JupiterExchange', '@pumpdotfun'
    ])
    reddit_subreddits: List[str] = field(default_factory=lambda: [
        'solana', 'SolanaMemeCoins', 'cryptomoonshots',
        'CryptoGemDiscovery', 'memecoin'
    ])
    # Discord channels are typically IDs, convert to string for .env / UI
    discord_channels: List[int] = field(default_factory=lambda: [
        int(cid) for cid in os.getenv('DISCORD_CHANNELS', '').split(',') if cid
    ])
    telegram_channels: List[str] = field(default_factory=lambda: [
        ch.strip() for ch in os.getenv('TELEGRAM_CHANNELS', '').split(',') if ch.strip()
    ])


    # Monitoring intervals (in seconds)
    twitter_check_interval: int = int(os.getenv('TWITTER_CHECK_INTERVAL', '36000')) # Make sure this matches .env.template
    reddit_check_interval: int = int(os.getenv('REDDIT_CHECK_INTERVAL', '60'))
    discord_check_interval: int = int(os.getenv('DISCORD_CHECK_INTERVAL', '45'))
    telegram_check_interval: int = int(os.getenv('TELEGRAM_CHECK_INTERVAL', '60'))
    tiktok_check_interval: int = int(os.getenv('TIKTOK_CHECK_INTERVAL', '300'))


@dataclass
class FilterConfig:
    """Token filtering configuration"""
    # Solsniffer score requirements
    min_safety_score: int = int(os.getenv('MIN_SAFETY_SCORE', '80'))

    # Market cap requirements
    min_market_cap: float = float(os.getenv('MIN_MARKET_CAP', '10000'))  # $10K
    max_market_cap: float = float(os.getenv('MAX_MARKET_CAP', '1000000'))  # $1M

    # Liquidity requirements
    min_liquidity: float = float(os.getenv('MIN_LIQUIDITY', '5000'))  # $5K
    require_locked_liquidity: bool = os.getenv('REQUIRE_LOCKED_LIQUIDITY', 'true').lower() == 'true'

    # Contract requirements
    require_verified_contract: bool = os.getenv('REQUIRE_VERIFIED_CONTRACT', 'false').lower() == 'true'
    require_disabled_mint: bool = os.getenv('REQUIRE_DISABLED_MINT', 'true').lower() == 'true'

    # Social sentiment requirements
    min_social_score: float = float(os.getenv('MIN_SOCIAL_SCORE', '0.6'))  # 60% positive sentiment
    min_mentions_count: int = int(os.getenv('MIN_MENTIONS_COUNT', '5'))

    # Technical analysis requirements
    min_volume_24h: float = float(os.getenv('MIN_VOLUME_24H', '1000'))  # $1K daily volume

    # Age limits
    max_age_hours: int = int(os.getenv('MAX_AGE_HOURS', '24'))  # Only trade tokens younger than 24 hours
    min_age_minutes: int = int(os.getenv('MIN_AGE_MINUTES', '5'))  # Avoid extremely new tokens


class Config:
    """Main configuration class"""

    def __init__(self):
        self.api_keys = APIKeys()
        self.trading = TradingConfig()
        self.filters = FilterConfig()
        self.monitoring = MonitoringConfig()

        # Database
        self.database_path = os.getenv('DATABASE_PATH', 'data/bot_database.db')

        # Web interface
        self.web_host = os.getenv('WEB_HOST', '0.0.0.0')
        self.web_port = int(os.getenv('WEB_PORT', '8080'))

        # Debug settings
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'
        self.testnet_enabled = os.getenv('ENABLE_TESTNET', 'false').lower() == 'true'
        self.emergency_stop_enabled = os.getenv('EMERGENCY_STOP_ENABLED', 'false').lower() == 'true'


        # Logging
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_directory = os.getenv('LOG_DIRECTORY', 'logs')

    def validate(self) -> bool:
        """Validate the configuration"""
        errors = []

        # Check required API keys for basic functionality
        if not self.api_keys.solana_private_key:
            errors.append("SOLANA_PRIVATE_KEY is required")

        # Validate trading parameters
        if self.trading.buy_amount_sol <= 0:
            errors.append("BUY_AMOUNT_SOL must be positive")

        if self.trading.max_positions <= 0:
            errors.append("MAX_POSITIONS must be positive")

        # Validate filter parameters
        if not (0 <= self.filters.min_safety_score <= 100):
            errors.append("MIN_SAFETY_SCORE must be between 0 and 100")
        if not (0.0 <= self.filters.min_social_score <= 1.0):
            errors.append("MIN_SOCIAL_SCORE must be between 0.0 and 1.0")


        if errors:
            print("❌ Configuration validation errors:")
            for error in errors:
                print(f"  • {error}")
            return False

        # Warnings for missing optional keys
        warnings = []
        if not self.api_keys.twitter_bearer_token:
            warnings.append("TWITTER_BEARER_TOKEN not set - Twitter monitoring disabled")

        if not self.api_keys.reddit_client_id:
            warnings.append("REDDIT_CLIENT_ID not set - Reddit monitoring disabled")

        if not self.api_keys.discord_token:
            warnings.append("DISCORD_TOKEN not set - Discord monitoring disabled")

        if not self.api_keys.telegram_api_id:
            warnings.append("TELEGRAM_API_ID / TELEGRAM_API_HASH not set - Telegram monitoring disabled")

        if warnings:
            print("⚠️  Configuration warnings:")
            for warning in warnings:
                print(f"  • {warning}")

        return True


# Create default configuration instances for easy importing
_default_config = Config()

# Export configuration components as module-level variables
api_keys = _default_config.api_keys
trading_config = _default_config.trading
monitoring_config = _default_config.monitoring
filter_config = _default_config.filters
web_config = {
    'host': _default_config.web_host,
    'port': _default_config.web_port,
    'debug': _default_config.debug,
    'secret_key': os.getenv('WEB_SECRET_KEY', 'dev-secret-key-change-in-production')
}
database_config = {
    'path': _default_config.database_path
}

# Export validation function
def validate_config():
    """Validate the default configuration"""
    return _default_config.validate()