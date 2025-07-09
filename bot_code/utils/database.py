"""
Database management module for storing bot data
"""

import sqlite3
import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import asdict
import threading

class DatabaseManager:
    """SQLite database manager for the trading bot"""
    
    def __init__(self, db_path: str):
        """Initialize database manager"""
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path
        self.lock = threading.Lock()
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # # # Initialize database
        # # asyncio.create_task(self.initialize())
        # # # Don't auto-initialize in __init__ - let caller handle it
    
    
    # async def initialize(self):
        # """Initialize database with required tables"""
    def initialize_database(self):
        """Initialize database with required tables (synchronous)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create tables
                # await self._create_tables(cursor)
                self._create_tables(cursor)
                
                # Create indexes
                # await self._create_indexes(cursor)
                self._create_indexes(cursor)
                
                conn.commit()
                self.logger.info("Database initialized successfully")
        
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise
    
    async def initialize(self):
        """Initialize database with required tables (async version)"""
        self.initialize_database()     
    
    # async def _create_tables(self, cursor):
    def _create_tables(self, cursor):
        """Create all required tables"""
        
        # Token discoveries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS token_discoveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                contract_address TEXT NOT NULL,
                source TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                original_message TEXT,
                author TEXT,
                platform_url TEXT,
                confidence_score REAL,
                social_metrics TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Token analyses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS token_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT NOT NULL,
                symbol TEXT,
                safety_score INTEGER,
                market_data TEXT,
                ai_prediction TEXT,
                filter_passed BOOLEAN,
                analysis_timestamp TEXT,
                recommendation TEXT,
                overall_risk_score REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Trading positions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT NOT NULL,
                symbol TEXT,
                entry_price REAL,
                current_price REAL,
                amount_sol REAL,
                tokens_held REAL,
                entry_timestamp TEXT,
                exit_timestamp TEXT,
                status TEXT,
                pnl_percent REAL,
                pnl_sol REAL,
                stop_loss_price REAL,
                take_profit_price REAL,
                exit_reason TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE,
                position_id INTEGER,
                type TEXT NOT NULL,
                token_address TEXT NOT NULL,
                amount_in REAL,
                amount_out REAL,
                price REAL,
                gas_fee REAL,
                timestamp TEXT,
                dex TEXT,
                status TEXT,
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (position_id) REFERENCES positions (id)
            )
        ''')
        
        # Bot statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                tokens_discovered INTEGER,
                tokens_analyzed INTEGER,
                positions_opened INTEGER,
                positions_closed INTEGER,
                total_pnl REAL,
                win_rate REAL,
                total_volume REAL,
                active_positions INTEGER,
                balance_sol REAL,
                portfolio_value REAL,
                uptime_hours REAL,
                success_rate REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Social media mentions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_mentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT,
                symbol TEXT,
                platform TEXT NOT NULL,
                message_id TEXT,
                content TEXT,
                author TEXT,
                url TEXT,
                engagement_score REAL,
                sentiment_score REAL,
                timestamp TEXT,
                processed BOOLEAN DEFAULT FALSE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Price history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT NOT NULL,
                price REAL NOT NULL,
                volume_24h REAL,
                market_cap REAL,
                timestamp TEXT NOT NULL,
                source TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Model predictions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT NOT NULL,
                prediction_data TEXT,
                actual_outcome TEXT,
                performance_data TEXT,
                prediction_timestamp TEXT,
                outcome_timestamp TEXT,
                model_version TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Configuration settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    # async def _create_indexes(self, cursor):
        """Create indexes for better performance"""
    def _create_indexes(self, cursor):
        
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_discoveries_address ON token_discoveries(contract_address)',
            'CREATE INDEX IF NOT EXISTS idx_discoveries_timestamp ON token_discoveries(timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_analyses_address ON token_analyses(token_address)',
            'CREATE INDEX IF NOT EXISTS idx_positions_address ON positions(token_address)',
            'CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)',
            'CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)',
            'CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_mentions_platform ON social_mentions(platform)',
            'CREATE INDEX IF NOT EXISTS idx_mentions_timestamp ON social_mentions(timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_price_history_address ON price_history(token_address)',
            'CREATE INDEX IF NOT EXISTS idx_price_history_timestamp ON price_history(timestamp)'
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
    
    async def save_discovery(self, discovery) -> int:
        """Save a token discovery"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO token_discoveries 
                    (symbol, contract_address, source, timestamp, original_message, 
                     author, platform_url, confidence_score, social_metrics)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    discovery.symbol,
                    discovery.contract_address,
                    discovery.source,
                    discovery.timestamp.isoformat(),
                    discovery.original_message,
                    discovery.author,
                    discovery.platform_url,
                    discovery.confidence_score,
                    json.dumps(discovery.social_metrics) if discovery.social_metrics else None
                ))
                
                discovery_id = cursor.lastrowid
                conn.commit()
                
                return discovery_id
        
        except Exception as e:
            self.logger.error(f"Error saving discovery: {e}")
            return 0
    
    async def save_analysis(self, analysis) -> int:
        """Save a token analysis"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO token_analyses 
                    (token_address, symbol, safety_score, market_data, ai_prediction,
                     filter_passed, analysis_timestamp, recommendation, overall_risk_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    analysis.token_discovery.contract_address,
                    analysis.token_discovery.symbol,
                    analysis.safety_score,
                    json.dumps(analysis.market_data),
                    json.dumps(analysis.ai_prediction),
                    analysis.filter_passed,
                    analysis.analysis_timestamp.isoformat(),
                    analysis.recommendation,
                    analysis.ai_prediction.get('overall_risk_score', 0.5) if analysis.ai_prediction else 0.5
                ))
                
                analysis_id = cursor.lastrowid
                conn.commit()
                
                return analysis_id
        
        except Exception as e:
            self.logger.error(f"Error saving analysis: {e}")
            return 0
    
    async def save_position(self, position) -> int:
        """Save a trading position"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO positions 
                    (token_address, symbol, entry_price, current_price, amount_sol,
                     tokens_held, entry_timestamp, status, pnl_percent, stop_loss_price,
                     take_profit_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    position.token_address,
                    position.symbol,
                    position.entry_price,
                    position.current_price,
                    position.amount_sol,
                    position.tokens_held,
                    position.entry_timestamp.isoformat(),
                    position.status,
                    position.pnl_percent,
                    position.stop_loss_price,
                    position.take_profit_price
                ))
                
                position_id = cursor.lastrowid
                conn.commit()
                
                return position_id
        
        except Exception as e:
            self.logger.error(f"Error saving position: {e}")
            return 0
    
    async def update_position(self, position) -> bool:
        """Update an existing position"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE positions SET
                        current_price = ?,
                        pnl_percent = ?,
                        status = ?,
                        exit_timestamp = ?,
                        exit_reason = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE token_address = ? AND status IN ('OPEN', 'PARTIAL_CLOSE')
                ''', (
                    position.current_price,
                    position.pnl_percent,
                    position.status,
                    datetime.now().isoformat() if position.status == 'CLOSED' else None,
                    getattr(position, 'exit_reason', None),
                    position.token_address
                ))
                
                conn.commit()
                return cursor.rowcount > 0
        
        except Exception as e:
            self.logger.error(f"Error updating position: {e}")
            return False
    
    async def save_transaction(self, transaction_data: Dict[str, Any]) -> int:
        """Save a transaction"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO transactions 
                    (transaction_id, position_id, type, token_address, amount_in,
                     amount_out, price, gas_fee, timestamp, dex, status, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    transaction_data.get('transaction_id'),
                    transaction_data.get('position_id'),
                    transaction_data.get('type'),
                    transaction_data.get('token_address'),
                    transaction_data.get('amount_in'),
                    transaction_data.get('amount_out'),
                    transaction_data.get('price'),
                    transaction_data.get('gas_fee'),
                    transaction_data.get('timestamp'),
                    transaction_data.get('dex'),
                    transaction_data.get('status'),
                    transaction_data.get('error_message')
                ))
                
                transaction_id = cursor.lastrowid
                conn.commit()
                
                return transaction_id
        
        except Exception as e:
            self.logger.error(f"Error saving transaction: {e}")
            return 0
    
    async def save_statistics(self, stats: Dict[str, Any]) -> bool:
        """Save bot statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO bot_statistics 
                    (timestamp, tokens_discovered, tokens_analyzed, positions_opened,
                     positions_closed, total_pnl, win_rate, total_volume, active_positions,
                     balance_sol, portfolio_value, uptime_hours, success_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    stats.get('tokens_discovered', 0),
                    stats.get('tokens_analyzed', 0),
                    stats.get('positions_opened', 0),
                    stats.get('positions_closed', 0),
                    stats.get('total_pnl', 0.0),
                    stats.get('win_rate', 0.0),
                    stats.get('total_volume', 0.0),
                    stats.get('active_positions', 0),
                    stats.get('balance_sol', 0.0),
                    stats.get('portfolio_value', 0.0),
                    stats.get('uptime_hours', 0.0),
                    stats.get('success_rate', 0.0)
                ))
                
                conn.commit()
                return True
        
        except Exception as e:
            self.logger.error(f"Error saving statistics: {e}")
            return False
    
    async def get_open_positions(self) -> List[Any]:
        """Get all open positions"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM positions 
                    WHERE status IN ('OPEN', 'PARTIAL_CLOSE')
                    ORDER BY entry_timestamp DESC
                ''')
                
                rows = cursor.fetchall()
                
                # Convert to position objects
                positions = []
                for row in rows:
                    # This would need to be converted back to Position dataclass
                    # For now, return as dict
                    position_dict = {
                        'id': row[0],
                        'token_address': row[1],
                        'symbol': row[2],
                        'entry_price': row[3],
                        'current_price': row[4],
                        'amount_sol': row[5],
                        'tokens_held': row[6],
                        'entry_timestamp': row[7],
                        'status': row[9],
                        'pnl_percent': row[10]
                    }
                    positions.append(position_dict)
                
                return positions
        
        except Exception as e:
            self.logger.error(f"Error getting open positions: {e}")
            return []
    
    async def get_closed_positions(self, days_back: int = 30) -> List[Any]:
        """Get closed positions"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
                
                cursor.execute('''
                    SELECT * FROM positions 
                    WHERE status = 'CLOSED' AND entry_timestamp > ?
                    ORDER BY exit_timestamp DESC
                ''', (cutoff_date,))
                
                rows = cursor.fetchall()
                
                positions = []
                for row in rows:
                    position_dict = {
                        'id': row[0],
                        'token_address': row[1],
                        'symbol': row[2],
                        'entry_price': row[3],
                        'current_price': row[4],
                        'amount_sol': row[5],
                        'pnl_percent': row[10],
                        'exit_timestamp': row[8]
                    }
                    positions.append(position_dict)
                
                return positions
        
        except Exception as e:
            self.logger.error(f"Error getting closed positions: {e}")
            return []
    
    async def get_recent_discoveries(self, hours_back: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent token discoveries"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_time = (datetime.now() - timedelta(hours=hours_back)).isoformat()
                
                cursor.execute('''
                    SELECT * FROM token_discoveries 
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (cutoff_time, limit))
                
                rows = cursor.fetchall()
                
                discoveries = []
                for row in rows:
                    discovery = {
                        'id': row[0],
                        'symbol': row[1],
                        'contract_address': row[2],
                        'source': row[3],
                        'timestamp': row[4],
                        'original_message': row[5],
                        'author': row[6],
                        'confidence_score': row[8]
                    }
                    discoveries.append(discovery)
                
                return discoveries
        
        except Exception as e:
            self.logger.error(f"Error getting recent discoveries: {e}")
            return []
    
    async def get_token_analysis(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Get the latest analysis for a token"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM token_analyses 
                    WHERE token_address = ?
                    ORDER BY analysis_timestamp DESC
                    LIMIT 1
                ''', (token_address,))
                
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row[0],
                        'token_address': row[1],
                        'symbol': row[2],
                        'safety_score': row[3],
                        'market_data': json.loads(row[4]) if row[4] else {},
                        'ai_prediction': json.loads(row[5]) if row[5] else {},
                        'filter_passed': row[6],
                        'recommendation': row[8],
                        'analysis_timestamp': row[7]
                    }
                
                return None
        
        except Exception as e:
            self.logger.error(f"Error getting token analysis: {e}")
            return None
    
    async def get_statistics_history(self, days_back: int = 7) -> List[Dict[str, Any]]:
        """Get statistics history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
                
                cursor.execute('''
                    SELECT * FROM bot_statistics 
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                ''', (cutoff_date,))
                
                rows = cursor.fetchall()
                
                stats = []
                for row in rows:
                    stat = {
                        'timestamp': row[1],
                        'tokens_discovered': row[2],
                        'tokens_analyzed': row[3],
                        'positions_opened': row[4],
                        'positions_closed': row[5],
                        'total_pnl': row[6],
                        'win_rate': row[7],
                        'portfolio_value': row[10]
                    }
                    stats.append(stat)
                
                return stats
        
        except Exception as e:
            self.logger.error(f"Error getting statistics history: {e}")
            return []
    
    async def save_price_data(self, token_address: str, price: float, volume_24h: float = None, 
                            market_cap: float = None, source: str = 'api') -> bool:
        """Save price data for a token"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO price_history 
                    (token_address, price, volume_24h, market_cap, timestamp, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    token_address,
                    price,
                    volume_24h,
                    market_cap,
                    datetime.now().isoformat(),
                    source
                ))
                
                conn.commit()
                return True
        
        except Exception as e:
            self.logger.error(f"Error saving price data: {e}")
            return False
    
    async def get_price_history(self, token_address: str, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get price history for a token"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_time = (datetime.now() - timedelta(hours=hours_back)).isoformat()
                
                cursor.execute('''
                    SELECT * FROM price_history 
                    WHERE token_address = ? AND timestamp > ?
                    ORDER BY timestamp ASC
                ''', (token_address, cutoff_time))
                
                rows = cursor.fetchall()
                
                prices = []
                for row in rows:
                    price_data = {
                        'timestamp': row[5],
                        'price': row[2],
                        'volume_24h': row[3],
                        'market_cap': row[4]
                    }
                    prices.append(price_data)
                
                return prices
        
        except Exception as e:
            self.logger.error(f"Error getting price history: {e}")
            return []
    
    async def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data to keep database size manageable"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
                
                # Clean up old discoveries
                cursor.execute('DELETE FROM token_discoveries WHERE timestamp < ?', (cutoff_date,))
                
                # Clean up old price history
                cursor.execute('DELETE FROM price_history WHERE timestamp < ?', (cutoff_date,))
                
                # Clean up old statistics
                cursor.execute('DELETE FROM bot_statistics WHERE timestamp < ?', (cutoff_date,))
                
                # Clean up old social mentions
                cursor.execute('DELETE FROM social_mentions WHERE timestamp < ?', (cutoff_date,))
                
                conn.commit()
                
                # Vacuum database to reclaim space
                cursor.execute('VACUUM')
                
                self.logger.info(f"Cleaned up data older than {days_to_keep} days")
        
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Count records in each table
                tables = [
                    'token_discoveries', 'token_analyses', 'positions', 
                    'transactions', 'bot_statistics', 'social_mentions', 'price_history'
                ]
                
                for table in tables:
                    cursor.execute(f'SELECT COUNT(*) FROM {table}')
                    stats[f'{table}_count'] = cursor.fetchone()[0]
                
                # Get database size
                cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                stats['database_size_bytes'] = cursor.fetchone()[0]
                
                return stats
        
        except Exception as e:
            self.logger.error(f"Error getting database stats: {e}")
            return {}
