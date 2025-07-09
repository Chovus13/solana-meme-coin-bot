# 🚀 Solana Memecoin Trading Bot - Deployment Guide

This guide provides step-by-step instructions for deploying and running the Solana Memecoin Trading Bot.

## 📋 Prerequisites

### System Requirements
- **Operating System**: Linux (Ubuntu 20.04+), macOS (10.15+), or Windows 10+
- **Python**: 3.8 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: 10GB free space
- **Network**: Stable internet connection

### Required Accounts & API Keys

#### 1. Solana Wallet
- Create a Solana wallet using Phantom, Solflare, or generate programmatically
- Fund with 2-5 SOL for trading (start with testnet SOL)
- Export private key in base58 format

#### 2. Social Media API Access
- **Twitter Developer Account**: https://developer.twitter.com/
- **Reddit API Access**: https://www.reddit.com/prefs/apps
- **Discord Bot**: https://discord.com/developers/applications
- **Telegram Bot**: Create via @BotFather

#### 3. Data Provider APIs
- **GMGN**: Sign up at https://gmgn.ai for memecoin data
- **Birdeye**: Get API key from https://birdeye.so

## 🛠️ Installation Methods

### Method 1: Automated Setup (Recommended)

1. **Download and Extract**
```bash
# Download the project
git clone <repository-url>
cd solana-memecoin-bot

# Make setup script executable
chmod +x setup.py
```

2. **Run Automated Setup**
```bash
python setup.py
```

3. **Configure Environment**
```bash
# Edit the generated .env file
nano .env
# Fill in your API keys and configuration
```

4. **Start the Bot**
```bash
# Activate virtual environment
source venv/bin/activate

# Run the bot
python main.py
```

### Method 2: Manual Setup

1. **Create Virtual Environment**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows
```

2. **Install Dependencies**
```bash
pip install --upgrade pip
pip install -r bot_code/requirements.txt
```

3. **Create Directories**
```bash
mkdir -p data logs
mkdir -p bot_code/data
```

4. **Setup Configuration**
```bash
cp .env.template .env
# Edit .env with your actual values
```

5. **Initialize Database**
```bash
python -c "
import sys
sys.path.append('bot_code')
from utils.database import DatabaseManager
db = DatabaseManager('data/bot_database.db')
db.initialize_database()
print('Database initialized successfully')
"
```

## 🔧 Configuration

### Essential Configuration Steps

#### 1. Solana Configuration
```bash
# In .env file
SOLANA_RPC_URL=https://api.testnet.solana.com  # Start with testnet
SOLANA_PRIVATE_KEY=your_base58_private_key
ENABLE_TESTNET=true
```

**Getting Your Private Key:**
```bash
# If using Solana CLI
solana-keygen new --outfile ~/my-wallet.json
solana-keygen pubkey ~/my-wallet.json  # Get public key
# Use base58 encoding of the private key array
```

#### 2. Social Media APIs

**Twitter API Setup:**
1. Apply for Twitter Developer Account
2. Create a new app
3. Generate Bearer Token and API keys
4. Add to .env file

**Reddit API Setup:**
1. Go to https://www.reddit.com/prefs/apps
2. Create a new application (script type)
3. Copy client ID and secret

**Discord Bot Setup:**
1. Go to Discord Developer Portal
2. Create new application and bot
3. Copy bot token
4. Invite bot to servers you want to monitor

#### 3. Trading Parameters
```bash
# Conservative settings for beginners
BUY_AMOUNT_SOL=0.5
MAX_POSITIONS=3
TAKE_PROFIT_MULTIPLIER=5
STOP_LOSS_PERCENTAGE=0.3
MIN_SAFETY_SCORE=85
```

### Security Configuration

#### 1. Wallet Security
- Store private keys securely
- Use testnet for initial testing
- Enable emergency stop mechanisms

#### 2. Risk Management
```bash
MAX_DAILY_LOSS=0.05          # 5% max daily loss
EMERGENCY_STOP_LOSS=0.7      # 70% emergency stop
ENABLE_KILL_SWITCH=true
```

#### 3. API Rate Limiting
- Configure appropriate check intervals
- Respect platform rate limits
- Monitor API usage

## 🚀 Running the Bot

### Development Mode

```bash
# Activate environment
source venv/bin/activate

# Start with debug logging
DEBUG=true python main.py
```

### Production Mode

```bash
# Start the bot
python main.py

# Or run in background
nohup python main.py > logs/bot.log 2>&1 &
```

### Using systemd (Linux)

Create service file:
```bash
sudo nano /etc/systemd/system/memecoin-bot.service
```

```ini
[Unit]
Description=Solana Memecoin Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/path/to/solana-memecoin-bot
Environment=PATH=/path/to/solana-memecoin-bot/venv/bin
ExecStart=/path/to/solana-memecoin-bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable memecoin-bot
sudo systemctl start memecoin-bot
sudo systemctl status memecoin-bot
```

## 🌐 Web Interface

### Accessing the Dashboard

1. **Local Access**
```
http://localhost:8080
```

2. **Remote Access** (if deployed on server)
```
http://your-server-ip:8080
```

### Dashboard Features

- **Real-time Monitoring**: Live bot statistics
- **Position Management**: Track active trades
- **Discovery Feed**: View discovered tokens
- **Settings Panel**: Configure parameters
- **Analytics**: Performance metrics

### Security Considerations

For production deployment:
1. Enable authentication in web interface
2. Use HTTPS with SSL certificates
3. Configure firewall rules
4. Use reverse proxy (nginx/Apache)

## 🔍 Monitoring & Maintenance

### Log Files

Monitor these log files:
```bash
tail -f logs/bot.log           # General operations
tail -f logs/trading.log       # Trading activities
tail -f logs/discovery.log     # Token discoveries
tail -f logs/error.log         # Errors and warnings
```

### Performance Monitoring

Key metrics to monitor:
- Discovery rate (tokens per hour)
- Analysis success rate
- Trading execution time
- Memory and CPU usage
- API response times

### Health Checks

Create monitoring script:
```bash
#!/bin/bash
# health_check.sh

# Check if bot process is running
if pgrep -f "python main.py" > /dev/null; then
    echo "✅ Bot is running"
else
    echo "❌ Bot is not running"
    # Restart bot
    cd /path/to/solana-memecoin-bot
    source venv/bin/activate
    nohup python main.py > logs/bot.log 2>&1 &
fi

# Check web interface
if curl -s http://localhost:8080 > /dev/null; then
    echo "✅ Web interface is accessible"
else
    echo "❌ Web interface is not responding"
fi
```

### Backup Strategy

Daily backup script:
```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR="/path/to/backups"

# Backup database
cp data/bot_database.db "$BACKUP_DIR/database_$DATE.db"

# Backup configuration
cp .env "$BACKUP_DIR/config_$DATE.env"

# Backup logs
tar -czf "$BACKUP_DIR/logs_$DATE.tar.gz" logs/

# Clean old backups (keep 30 days)
find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.env" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete
```

## 🔧 Troubleshooting

### Common Issues

#### Bot Won't Start
```bash
# Check Python version
python --version

# Check dependencies
pip list

# Check configuration
python -c "
import sys
sys.path.append('code')
from config import Config
config = Config()
print('Config validation:', config.validate())
"
```

#### API Connection Issues
```bash
# Test Solana connection
curl -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"getHealth"}' \
  $SOLANA_RPC_URL

# Check API keys in logs
grep -i "api" logs/error.log
```

#### Database Issues
```bash
# Reset database
rm data/bot_database.db
python -c "
import sys
sys.path.append('code')
from utils.database import DatabaseManager
db = DatabaseManager('data/bot_database.db')
db.initialize_database()
"
```

#### Memory Issues
```bash
# Monitor memory usage
free -h
ps aux | grep python

# Restart bot if memory usage is high
pkill -f "python main.py"
python main.py
```

### Performance Optimization

#### 1. Reduce Discovery Frequency
```bash
# In .env file
TWITTER_CHECK_INTERVAL=60     # Increase from 30
REDDIT_CHECK_INTERVAL=120     # Increase from 60
```

#### 2. Limit Concurrent Positions
```bash
MAX_POSITIONS=3               # Reduce from 5
```

#### 3. Optimize Database
```bash
# Vacuum database weekly
sqlite3 data/bot_database.db "VACUUM;"
```

## 📊 Production Deployment

### VPS Deployment (Ubuntu 20.04)

1. **Server Setup**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip python3-venv git -y

# Clone repository
git clone <repository-url>
cd solana-memecoin-bot
```

2. **Security Setup**
```bash
# Create non-root user
sudo adduser botuser
sudo usermod -aG sudo botuser

# Setup firewall
sudo ufw allow 22
sudo ufw allow 8080
sudo ufw enable

# Setup fail2ban
sudo apt install fail2ban -y
```

3. **SSL/HTTPS Setup**
```bash
# Install nginx
sudo apt install nginx -y

# Configure reverse proxy
sudo nano /etc/nginx/sites-available/memecoin-bot
```

Nginx configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Docker Deployment

Create Dockerfile:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for better caching
COPY code/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p data logs

# Expose web interface port
EXPOSE 8080

# Run the bot
CMD ["python", "main.py"]
```

Build and run:
```bash
# Build image
docker build -t solana-memecoin-bot .

# Run container
docker run -d \
  --name memecoin-bot \
  --env-file .env \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  solana-memecoin-bot
```

## 🚨 Security Best Practices

### 1. Key Management
- Store private keys in environment variables only
- Use hardware wallets for large amounts
- Rotate API keys regularly
- Never commit secrets to version control

### 2. Network Security
- Use VPN for remote access
- Configure firewall rules
- Enable DDoS protection
- Use HTTPS for web interface

### 3. Monitoring
- Set up log monitoring alerts
- Monitor unusual trading activity
- Track API usage and rate limits
- Regular security audits

## 📞 Support

### Getting Help

1. **Check Logs**: Review error logs for specific issues
2. **Documentation**: Read the full README.md
3. **Common Issues**: Check troubleshooting section
4. **Performance**: Monitor system resources

### Maintenance Schedule

- **Daily**: Check logs and performance
- **Weekly**: Review trading performance
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Full system audit and optimization

---

**⚠️ Important Reminders:**
- Always test on Solana testnet first
- Start with small amounts
- Monitor the bot actively
- Keep backups of configuration and data
- This software is for educational purposes only

**Author**: MiniMax Agent  
**Last Updated**: 2025-06-26