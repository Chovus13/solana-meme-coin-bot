# 🚀 Solana Memecoin Trading Bot

An advanced automated trading bot for Solana memecoins featuring social media monitoring, AI-powered analysis, and comprehensive risk management.

## ✨ Features

### 🕵️ Social Media Monitoring
- **Multi-platform scanning**: Twitter, Reddit, Discord, Telegram, TikTok
- **Real-time discovery**: Automatically detects memecoin mentions and ticker symbols
- **Smart filtering**: AI-powered confidence scoring for discovered tokens
- **Influencer tracking**: Monitor specific accounts and channels

### 🤖 AI-Powered Analysis
- **Machine learning predictions**: Success probability analysis using historical data
- **Technical indicators**: Market cap, liquidity, volume analysis
- **Social sentiment**: Aggregate social media sentiment scoring
- **Risk assessment**: Multi-factor risk evaluation

### 🛡️ Safety & Security
- **Contract verification**: Integration with Solsniffer.com for safety scoring
- **Liquidity checks**: Verify locked liquidity and disabled mint functions
- **Risk limits**: Configurable daily loss limits and emergency stop-loss
- **Blacklist management**: Automatic filtering of known scam tokens

### 💰 Automated Trading
- **Jupiter/Raydium integration**: Trade through Solana's top DEXs
- **Smart position sizing**: Configurable position sizes and risk management
- **Take profit automation**: 10x target with 15% moonbag retention
- **Priority fees**: Configurable transaction priority for faster execution

### 📊 Web Dashboard
- **Real-time monitoring**: Live dashboard with trading statistics
- **Position management**: Track all open positions and P&L
- **Discovery feed**: View all discovered tokens with analysis
- **Settings panel**: Configure all bot parameters through web interface

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- Node.js 16+ (for web interface)
- Git
- 1-2 SOL for trading (testnet recommended for initial setup)

### Quick Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd solana-memecoin-bot
```

2. **Run the automated setup**
```bash
python setup.py
```

3. **Configure your environment**
```bash
# Edit the .env file with your API keys
nano .env
```

4. **Start the bot**
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Run the bot
python main.py
```

5. **Access the web interface**
```
http://localhost:8080
```

### Manual Setup

If the automated setup fails, follow these manual steps:

1. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

2. **Install dependencies**
```bash
pip install -r code/requirements.txt
```

3. **Create directories**
```bash
mkdir -p data logs
```

4. **Configure environment**
```bash
cp .env.template .env
# Edit .env with your actual values
```

## 🔧 Configuration

### Required API Keys

#### Solana Configuration
- **RPC URL**: Solana RPC endpoint (mainnet/testnet)
- **Private Key**: Base58-encoded private key for your trading wallet

#### Social Media APIs
- **Twitter**: Bearer token and API credentials
- **Reddit**: Client ID, secret, and user agent
- **Discord**: Bot token for monitoring servers
- **Telegram**: Bot token for channel monitoring

#### Data Sources
- **GMGN**: API key for memecoin data
- **Birdeye**: API key for additional market data

### Environment Variables (.env)

```bash
# Solana Configuration
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_PRIVATE_KEY=your_base58_private_key

# Enable testnet for safe testing
ENABLE_TESTNET=true

# Trading Parameters
BUY_AMOUNT_SOL=1.5
MAX_POSITIONS=5
TAKE_PROFIT_MULTIPLIER=10
STOP_LOSS_PERCENTAGE=50
MOONBAG_PERCENTAGE=15

# Safety Settings
MIN_SAFETY_SCORE=80
REQUIRE_LOCKED_LIQUIDITY=true
REQUIRE_DISABLED_MINT=true
```

### Web Interface Configuration

The bot includes a comprehensive web interface accessible at `http://localhost:8080`:

- **Dashboard**: Overview of bot performance and statistics
- **Positions**: Manage active trading positions
- **Discoveries**: View and analyze discovered tokens
- **Settings**: Configure all bot parameters
- **Analytics**: Detailed performance analytics

## 🚀 Usage

### Starting the Bot

```bash
# Basic startup
python main.py

# With custom configuration
ENABLE_TESTNET=true python main.py
```

### Web Interface

Navigate to `http://localhost:8080` to access:

1. **Dashboard**: Real-time bot statistics and performance
2. **Positions**: Monitor active trades and P&L
3. **Discoveries**: Review discovered tokens and analysis
4. **Settings**: Configure trading parameters and filters
5. **Analytics**: Detailed performance analysis

### Manual Controls

Through the web interface, you can:
- Start/stop the bot
- Force analysis of specific tokens
- Execute manual buy/sell orders
- Adjust risk parameters in real-time
- View detailed token analysis

## 📊 Trading Strategy

### Discovery Process
1. **Social Media Monitoring**: Scan platforms for memecoin mentions
2. **Confidence Scoring**: AI evaluation of discovery reliability
3. **Contract Analysis**: Safety checks via Solsniffer
4. **Market Validation**: Liquidity, volume, and market cap verification

### Entry Criteria
- Safety score > 80/100
- Locked liquidity required
- Disabled mint function
- Minimum market cap: $10,000
- Minimum liquidity: $5,000
- Social confidence > 60%

### Exit Strategy
- **Take Profit**: 10x multiplier (1000% gain)
- **Stop Loss**: 50% of position value
- **Moonbag**: Retain 15% of position after take profit
- **Time Limit**: Force exit after 24 hours

### Risk Management
- Maximum 5 concurrent positions
- Position size: 20% of available balance
- Daily loss limit: 10%
- Emergency stop-loss at 80% total loss

## 🔐 Security Features

### Wallet Security
- Private keys stored in environment variables
- Optional testnet mode for safe testing
- Emergency kill switch for immediate stop
- Daily loss limits and monitoring

### Contract Safety
- Solsniffer.com integration for safety scoring
- Automatic verification of liquidity locks
- Detection of disabled mint functions
- Blacklist management for known scam tokens

### Risk Controls
- Maximum position size limits
- Diversification across multiple tokens
- Stop-loss automation
- Real-time monitoring and alerts

## 📈 Performance Monitoring

### Metrics Tracked
- Total P&L and ROI
- Win/loss ratio
- Average hold time
- Discovery accuracy
- Risk-adjusted returns

### Notifications
- Trade executions
- Token discoveries
- Risk alerts
- Daily summaries
- Error notifications

### Logging
- Detailed trade logs
- Discovery logs with confidence scores
- Error and warning logs
- Performance metrics

## 🛠️ API Integrations

### Supported Platforms

#### Social Media
- **Twitter API v2**: Real-time tweet monitoring
- **Reddit API**: Subreddit and post scanning
- **Discord API**: Server and channel monitoring
- **Telegram API**: Channel and group scanning
- **TikTok**: Unofficial API for viral content

#### Trading & Data
- **Jupiter**: Primary DEX for token swaps
- **Raydium**: Secondary DEX integration
- **GMGN**: Memecoin analytics and data
- **Birdeye**: Additional market data
- **Solsniffer**: Contract safety scoring

## 🔧 Troubleshooting

### Common Issues

#### Bot Won't Start
- Check Python version (3.8+ required)
- Verify all dependencies installed
- Check .env file configuration
- Ensure database permissions

#### No Discoveries
- Verify social media API keys
- Check network connectivity
- Review monitoring intervals
- Confirm keyword configuration

#### Trading Errors
- Verify Solana RPC connection
- Check wallet balance (SOL for fees)
- Confirm private key format
- Review slippage settings

#### Web Interface Issues
- Check port 8080 availability
- Verify Flask dependencies
- Review browser console for errors
- Clear browser cache

### Debug Mode

Enable debug logging:
```bash
DEBUG=true python main.py
```

### Log Files
- `logs/bot.log`: General bot operations
- `logs/trading.log`: Trading-specific logs
- `logs/discovery.log`: Token discovery logs
- `logs/error.log`: Error and warning logs

## 🚨 Important Warnings

### Financial Risk
- **High Risk**: Memecoin trading is extremely risky
- **Potential Total Loss**: You may lose all invested funds
- **Not Financial Advice**: This bot is for educational purposes
- **Test First**: Always test on Solana testnet first

### Technical Risk
- **API Limitations**: Social media APIs have rate limits
- **Network Issues**: Solana network can be congested
- **Smart Contract Risk**: DeFi protocols may have vulnerabilities
- **Bot Bugs**: Software may contain errors

### Legal Considerations
- **Compliance**: Ensure compliance with local regulations
- **Tax Implications**: Trading may have tax consequences
- **Terms of Service**: Respect social media platform ToS
- **Professional Advice**: Consult professionals for large amounts

## 📚 Advanced Configuration

### Custom Strategies

Edit `code/config.py` to customize:
- Trading parameters
- Risk management rules
- Discovery filters
- Analysis weights

### Adding Platforms

To add new social media platforms:
1. Create monitor class in `code/social_media/`
2. Implement required methods
3. Add to main bot configuration
4. Update web interface

### Custom Indicators

Add custom analysis indicators:
1. Extend `TokenAnalyzer` class
2. Implement indicator calculation
3. Update AI predictor features
4. Configure weights in settings

## 🤝 Contributing

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd solana-memecoin-bot

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Code formatting
black code/
isort code/
```

### Project Structure
```
solana-memecoin-bot/
├── main.py                     # Main entry point
├── setup.py                    # Setup script
├── code/
│   ├── config.py              # Configuration management
│   ├── solana_memecoin_bot.py # Main bot logic
│   ├── social_media/          # Social media monitors
│   ├── token_analysis/        # Analysis modules
│   ├── trading/              # Trading logic
│   ├── utils/                # Utilities
│   └── web_interface/        # Web dashboard
├── data/                     # Database and data files
├── logs/                     # Log files
└── docs/                     # Documentation
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This software is provided "as is" without warranty of any kind. Trading cryptocurrencies involves substantial risk of loss and is not suitable for all investors. The developers are not responsible for any financial losses incurred while using this software. Always trade responsibly and only invest what you can afford to lose.

---

**Author**: MiniMax Agent  
**Version**: 1.0.0  
**Last Updated**: 2025-06-26