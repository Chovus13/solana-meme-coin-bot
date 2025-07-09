#!/usr/bin/env python3
"""
Solana Memecoin Trading Bot - Main Entry Point
Author: MiniMax Agent
"""

import asyncio
import logging
import signal
import sys
import threading
import time
from pathlib import Path

# Add the code directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "code"))

from code.config import Config
from code.solana_memecoin_bot import SolanaMemecoinBot
from code.web_interface.app import create_app
from code.utils.logger import setup_logging


class BotManager:
    """Main bot manager that coordinates all components"""
    
    def __init__(self):
        self.config = Config()
        self.bot = None
        self.web_app = None
        self.web_thread = None
        self.running = False
        
        # Setup logging
        setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def start(self):
        """Start the bot and web interface"""
        try:
            self.logger.info("🚀 Starting Solana Memecoin Trading Bot...")
            
            # Validate configuration
            if not self.config.validate():
                self.logger.error("❌ Configuration validation failed. Please check your settings.")
                return False
            
            # Initialize bot
            self.logger.info("📊 Initializing trading bot...")
            self.bot = SolanaMemecoinBot(self.config)
            
            # Initialize web interface
            self.logger.info("🌐 Starting web interface...")
            self.web_app = create_app(self.bot)
            
            # Start web server in separate thread
            self.web_thread = threading.Thread(
                target=self._run_web_server,
                daemon=True
            )
            self.web_thread.start()
            
            # Start bot
            self.logger.info("🤖 Starting bot operations...")
            self.running = True
            
            # Run bot in main thread
            asyncio.run(self.bot.start())
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start bot: {e}")
            return False
    
    def _run_web_server(self):
        """Run the web server"""
        try:
            host = self.config.web_host
            port = self.config.web_port
            
            self.logger.info(f"🌐 Web interface starting on http://{host}:{port}")
            
            # Import socketio for running the app
            from code.web_interface.app import socketio
            
            socketio.run(
                self.web_app,
                host=host,
                port=port,
                debug=False,
                allow_unsafe_werkzeug=True
            )
            
        except Exception as e:
            self.logger.error(f"❌ Web server error: {e}")
    
    def stop(self):
        """Stop the bot and web interface"""
        self.logger.info("🛑 Stopping bot...")
        self.running = False
        
        if self.bot:
            asyncio.create_task(self.bot.stop())
        
        # Web server will stop when main thread exits
        self.logger.info("✅ Bot stopped successfully")
    
    def status(self):
        """Get bot status"""
        if not self.bot:
            return {"status": "stopped", "message": "Bot not initialized"}
        
        return self.bot.get_status()


def print_banner():
    """Print startup banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║               🚀 SOLANA MEMECOIN TRADING BOT 🚀              ║
    ║                                                               ║
    ║  • Social Media Monitoring                                    ║
    ║  • AI-Powered Token Analysis                                  ║
    ║  • Automated Trading on Solana                               ║
    ║  • Risk Management & Safety Checks                           ║
    ║  • Real-time Web Dashboard                                   ║
    ║                                                               ║
    ║                    Author: MiniMax Agent                     ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def main():
    """Main entry point"""
    print_banner()
    
    # Create bot manager
    manager = BotManager()
    
    try:
        # Start the bot
        success = manager.start()
        
        if success:
            print("\n✅ Bot started successfully!")
            print(f"🌐 Web interface: http://{manager.config.web_host}:{manager.config.web_port}")
            print("📊 Dashboard: http://localhost:8080")
            print("\n🔧 Control commands:")
            print("  • Ctrl+C to stop")
            print("  • Check web interface for detailed controls")
            
            # Keep main thread alive
            try:
                while manager.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        else:
            print("\n❌ Failed to start bot. Check logs for details.")
            return 1
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1
    finally:
        manager.stop()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())