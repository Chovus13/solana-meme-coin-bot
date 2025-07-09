#!/usr/bin/env python3
"""
Setup script for Solana Memecoin Trading Bot
Author: MiniMax Agent
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import List


def run_command(command, description):
    """Run a command and handle errors"""
    print(f"📦 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return True


def install_system_dependencies():
    """Install system-level dependencies"""
    system = platform.system().lower()
    
    if system == "linux":
        commands = [
            ("sudo apt update", "Updating package list"),
            ("sudo apt install -y python3-pip python3-venv build-essential", "Installing Python dependencies"),
            ("sudo apt install -y curl wget git", "Installing basic tools")
        ]
    elif system == "darwin":  # macOS
        commands = [
            ("xcode-select --install", "Installing Xcode command line tools"),
            ("brew install python git", "Installing Python and Git via Homebrew")
        ]
    else:  # Windows
        print("⚠️  Please ensure Python 3.8+, pip, and git are installed on Windows")
        return True
    
    for command, description in commands:
        if not run_command(command, description):
            print(f"⚠️  Failed to install system dependencies. Please install manually.")
            return False
    
    return True


def create_virtual_environment():
    """Create and setup virtual environment"""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("📦 Virtual environment already exists")
        return True
    
    if not run_command("python3 -m venv venv", "Creating virtual environment"):
        return False
    
    # Activate virtual environment commands
    if platform.system().lower() == "windows":
        activate_cmd = "venv\\Scripts\\activate"
        pip_cmd = "venv\\Scripts\\pip"
    else:
        activate_cmd = "source venv/bin/activate"
        pip_cmd = "venv/bin/pip"
    
    # Upgrade pip
    if not run_command(f"{pip_cmd} install --upgrade pip", "Upgrading pip"):
        return False
    
    return True


def install_python_dependencies():
    """Install Python package dependencies"""
    # Determine pip command
    if platform.system().lower() == "windows":
        pip_cmd = "venv\\Scripts\\pip"
    else:
        pip_cmd = "venv/bin/pip"
    
    # Install from requirements.txt
    if not run_command(f"{pip_cmd} install -r bot_code/requirements.txt", "Installing Python packages"):
        return False
    
    return True


def create_env_file():
    """Create .env file from template"""
    env_file = Path(".env")
    env_template = Path(".env.template")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    if not env_template.exists():
        # Create template
        with open(env_template, 'w') as f:
            f.write("""# Solana Memecoin Trading Bot Configuration
# Copy this file to .env and fill in your actual values

# Solana Configuration
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_PRIVATE_KEY=your_base58_encoded_private_key_here

# Social Media API Keys
TWITTER_BEARER_TOKEN=your_twitter_bearer_token_here
TWITTER_API_KEY=your_twitter_api_key_here
TWITTER_API_SECRET=your_twitter_api_secret_here
TWITTER_ACCESS_TOKEN=your_twitter_access_token_here
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret_here

REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
REDDIT_USER_AGENT=your_reddit_user_agent_here

DISCORD_BOT_TOKEN=your_discord_bot_token_here

TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Data Source API Keys
GMGN_API_KEY=your_gmgn_api_key_here
BIRDEYE_API_KEY=your_birdeye_api_key_here

# Notification Webhooks (Optional)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_here
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your_webhook_here

# Database Configuration
DATABASE_PATH=data/bot_database.db

# Web Interface Configuration
WEB_HOST=0.0.0.0
WEB_PORT=8080

# Security Settings
ENABLE_TESTNET=true
MAX_DAILY_LOSS_PERCENTAGE=10
EMERGENCY_STOP_ENABLED=true
""")
    
    # Copy template to .env
    if run_command("cp .env.template .env", "Creating .env file from template"):
        print("📝 Please edit .env file with your actual API keys and configuration")
        return True
    
    return False


def create_data_directories():
    """Create necessary data directories"""
    directories = [
        "data",
        "logs",
        "bot_code/data",
        "web_interface/static/uploads"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    return True


def setup_database():
    """Initialize the database"""
    try:
        # Import and initialize database
        sys.path.insert(0, str(Path(__file__).parent / "bot_code"))
        from utils.database import DatabaseManager
        
        db = DatabaseManager("data/bot_database.db")
        db.initialize_database()
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False


def run_tests():
    """Run basic system tests"""
    print("🧪 Running system tests...")
    
    try:
        # Test imports
        sys.path.insert(0, str(Path(__file__).parent / "bot_code"))
        
        from config import Config
        from utils.database import DatabaseManager
        from utils.logger import setup_logging
        
        # Test configuration
        config = Config()
        if not config.validate():
            print("⚠️  Configuration validation failed - please check your .env file")
            return False
        
        print("✅ All tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ System test failed: {e}")
        return False


def main():
    """Main setup function"""
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║              🛠️  SOLANA MEMECOIN BOT SETUP  🛠️               ║
    ║                                                               ║
    ║  This script will set up your trading bot environment         ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    setup_steps = [
        ("Checking Python version", check_python_version),
        ("Installing system dependencies", install_system_dependencies),
        ("Creating virtual environment", create_virtual_environment),
        ("Installing Python dependencies", install_python_dependencies),
        ("Creating configuration files", create_env_file),
        ("Creating data directories", create_data_directories),
        ("Setting up database", setup_database),
        ("Running system tests", run_tests)
    ]
    
    failed_steps = []
    
    for step_name, step_function in setup_steps:
        print(f"\n🔄 {step_name}...")
        if not step_function():
            failed_steps.append(step_name)
            print(f"❌ {step_name} failed")
        else:
            print(f"✅ {step_name} completed")
    
    print("\n" + "="*60)
    
    if failed_steps:
        print("❌ Setup completed with errors:")
        for step in failed_steps:
            print(f"   • {step}")
        print("\nPlease resolve the errors above before running the bot.")
        return 1
    else:
        print("🎉 Setup completed successfully!")
        print("\n📋 Next steps:")
        print("   1. Edit .env file with your API keys")
        print("   2. Review bot_code/config.py for trading parameters")
        print("   3. Run the bot: python main.py")
        print("   4. Access web interface: http://localhost:8080")
        
        if platform.system().lower() != "windows":
            print("\n🚀 Quick start commands:")
            print("   source venv/bin/activate  # Activate virtual environment")
            print("   python main.py            # Start the bot")
        else:
            print("\n🚀 Quick start commands:")
            print("   venv\\Scripts\\activate     # Activate virtual environment")
            print("   python main.py            # Start the bot")
        
        return 0


if __name__ == "__main__":
    sys.exit(main())
