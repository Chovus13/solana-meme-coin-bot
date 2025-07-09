from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

@dataclass
class TokenDiscovery:
    symbol: str
    contract_address: str
    source: str  # npr. twitter, reddit, telegram
    timestamp: datetime
    original_message: str
    author: str
    platform_url: str
    confidence_score: float = 0.0
    social_metrics: Dict[str, Any] = None

@dataclass
class TokenAnalysis:
    token_discovery: TokenDiscovery
    safety_score: int
    market_data: Dict[str, Any]
    ai_prediction: Dict[str, Any]
    filter_passed: bool
    analysis_timestamp: datetime
    recommendation: str  # BUY, PASS, MONITOR

@dataclass
class Position:
    token_address: str
    symbol: str
    entry_price: float
    current_price: float
    amount_sol: float
    tokens_held: float
    entry_timestamp: datetime
    status: str  # OPEN, CLOSED, PARTIAL_CLOSE
    pnl_percent: float = 0.0
    stop_loss_price: float = 0.0
    take_profit_price: float = 0.0