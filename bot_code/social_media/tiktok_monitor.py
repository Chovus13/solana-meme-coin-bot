"""
TikTok monitoring module for discovering memecoin mentions in videos and comments
Note: Uses unofficial TikTok API - use with caution and respect rate limits
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import time

try:
    from TikTokApi import TikTokApi
except ImportError:
    TikTokApi = None

class TikTokMonitor:
    """Monitor TikTok for memecoin-related content"""
    
    def __init__(self, api_keys):
        """Initialize TikTok monitor"""
        self.logger = logging.getLogger(__name__)
        self.api_keys = api_keys
        
        # Initialize TikTok API client
        if TikTokApi and api_keys.tiktok_session_id:
            try:
                self.api = TikTokApi()
                self.logger.info("TikTok API initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize TikTok API: {e}")
                self.api = None
        else:
            self.api = None
            self.logger.warning("TikTok API not available or no session ID provided")
        
        # Compiled regex patterns
        self.contract_pattern = re.compile(r'[A-HJ-NP-Z1-9]{32,44}')
        self.ticker_pattern = re.compile(r'\\$([A-Z]{2,10})\\b')
        self.ca_pattern = re.compile(r'CA:?\\s*([A-HJ-NP-Z1-9]{32,44})')
        
        # Track processed videos
        self.processed_videos = set()
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 5.0  # Minimum seconds between requests (be conservative)
    
    async def search_hashtags(self, hashtags: List[str], limit: int = 20) -> List[Dict[str, Any]]:
        """Search for videos by hashtags"""
        if not self.api:
            return []
        
        videos = []
        
        for hashtag in hashtags:
            try:
                await self._rate_limit()
                
                # Search for hashtag
                hashtag_videos = []
                async for video in self.api.hashtag(name=hashtag).videos(count=limit):
                    processed_video = await self._process_tiktok_video(video, hashtag)
                    if processed_video:
                        hashtag_videos.append(processed_video)
                
                videos.extend(hashtag_videos)
                self.logger.info(f"Found {len(hashtag_videos)} videos for #{hashtag}")
                
            except Exception as e:
                self.logger.error(f"Error searching hashtag #{hashtag}: {e}")
                continue
        
        return videos
    
    async def search_keywords(self, keywords: List[str], limit: int = 20) -> List[Dict[str, Any]]:
        """Search for videos by keywords"""
        if not self.api:
            return []
        
        videos = []
        
        for keyword in keywords:
            try:
                await self._rate_limit()
                
                # Search for keyword
                search_videos = []
                async for video in self.api.search.videos(keyword, count=limit):
                    processed_video = await self._process_tiktok_video(video, f"search:{keyword}")
                    if processed_video:
                        search_videos.append(processed_video)
                
                videos.extend(search_videos)
                self.logger.info(f"Found {len(search_videos)} videos for keyword '{keyword}'")
                
            except Exception as e:
                self.logger.error(f"Error searching keyword '{keyword}': {e}")
                continue
        
        return videos
    
    async def get_user_videos(self, username: str, keywords: List[str], limit: int = 30) -> List[Dict[str, Any]]:
        """Get videos from a specific user"""
        if not self.api:
            return []
        
        try:
            await self._rate_limit()
            
            user = self.api.user(username=username)
            user_videos = []
            
            async for video in user.videos(count=limit):
                # Check if video description contains keywords
                description = getattr(video, 'desc', '')
                if self._contains_keywords(description, keywords):
                    processed_video = await self._process_tiktok_video(video, f"user:{username}")
                    if processed_video:
                        user_videos.append(processed_video)
            
            self.logger.info(f"Found {len(user_videos)} relevant videos from @{username}")
            return user_videos
            
        except Exception as e:
            self.logger.error(f"Error getting videos from user @{username}: {e}")
            return []
    
    async def get_trending_videos(self, keywords: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """Get trending videos that match keywords"""
        if not self.api:
            return []
        
        try:
            await self._rate_limit()
            
            trending_videos = []
            
            async for video in self.api.trending.videos(count=limit):
                description = getattr(video, 'desc', '')
                if self._contains_keywords(description, keywords):
                    processed_video = await self._process_tiktok_video(video, "trending")
                    if processed_video:
                        trending_videos.append(processed_video)
            
            self.logger.info(f"Found {len(trending_videos)} relevant trending videos")
            return trending_videos
            
        except Exception as e:
            self.logger.error(f"Error getting trending videos: {e}")
            return []
    
    async def get_video_comments(self, video_id: str, keywords: List[str], limit: int = 100) -> List[Dict[str, Any]]:
        """Get comments from a specific video"""
        if not self.api:
            return []
        
        try:
            await self._rate_limit()
            
            video = self.api.video(id=video_id)
            relevant_comments = []
            
            async for comment in video.comments(count=limit):
                comment_text = getattr(comment, 'text', '')
                if self._contains_keywords(comment_text, keywords):
                    processed_comment = await self._process_tiktok_comment(comment, video_id)
                    if processed_comment:
                        relevant_comments.append(processed_comment)
            
            return relevant_comments
            
        except Exception as e:
            self.logger.error(f"Error getting comments for video {video_id}: {e}")
            return []
    
    def _contains_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the specified keywords"""
        if not text:
            return False
        
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)
    
    async def _process_tiktok_video(self, video, source: str) -> Optional[Dict[str, Any]]:
        """Process a TikTok video and extract relevant information"""
        try:
            video_id = getattr(video, 'id', str(hash(str(video))))
            
            # Skip if already processed
            if video_id in self.processed_videos:
                return None
            
            self.processed_videos.add(video_id)
            
            # Get video details
            description = getattr(video, 'desc', '')
            author = getattr(video, 'author', {})
            stats = getattr(video, 'stats', {})
            
            # Extract token information from description
            contract_addresses = self.contract_pattern.findall(description)
            ticker_symbols = self.ticker_pattern.findall(description.upper())
            ca_addresses = self.ca_pattern.findall(description)
            
            # Combine contract addresses
            all_contracts = list(set(contract_addresses + ca_addresses))
            
            # Calculate engagement score
            engagement_score = self._calculate_video_engagement(stats)
            
            # Determine if this is memecoin-related
            is_memecoin_related = self._is_memecoin_related(description)
            
            # Get video creation time
            create_time = getattr(video, 'createTime', 0)
            created_at = datetime.fromtimestamp(create_time) if create_time else datetime.utcnow()
            age_hours = (datetime.utcnow() - created_at).total_seconds() / 3600
            
            # Get author info
            author_info = {}
            if author:
                author_info = {
                    'id': getattr(author, 'id', ''),
                    'username': getattr(author, 'uniqueId', ''),
                    'nickname': getattr(author, 'nickname', ''),
                    'verified': getattr(author, 'verified', False),
                    'follower_count': getattr(author, 'followerCount', 0),
                    'following_count': getattr(author, 'followingCount', 0)
                }
            
            processed_video = {
                'id': video_id,
                'description': description,
                'text': description,  # Alias for compatibility
                'author': author_info.get('username', 'unknown'),
                'author_info': author_info,
                'created_at': created_at.isoformat(),
                'url': f"https://www.tiktok.com/@{author_info.get('username', 'user')}/video/{video_id}",
                'source': source,
                'contract_addresses': all_contracts,
                'ticker_symbols': ticker_symbols,
                'engagement_score': engagement_score,
                'is_memecoin_related': is_memecoin_related,
                'age_hours': age_hours,
                'stats': {
                    'like_count': stats.get('likeCount', 0),
                    'comment_count': stats.get('commentCount', 0),
                    'share_count': stats.get('shareCount', 0),
                    'play_count': stats.get('playCount', 0)
                },
                'hashtags': self._extract_hashtags(description),
                'type': 'tiktok_video'
            }
            
            return processed_video
            
        except Exception as e:
            self.logger.error(f"Error processing TikTok video: {e}")
            return None
    
    async def _process_tiktok_comment(self, comment, video_id: str) -> Optional[Dict[str, Any]]:
        """Process a TikTok comment"""
        try:
            comment_id = getattr(comment, 'id', str(hash(str(comment))))
            text = getattr(comment, 'text', '')
            user = getattr(comment, 'user', {})
            
            # Extract token information
            contract_addresses = self.contract_pattern.findall(text)
            ticker_symbols = self.ticker_pattern.findall(text.upper())
            ca_addresses = self.ca_pattern.findall(text)
            
            # Combine contract addresses
            all_contracts = list(set(contract_addresses + ca_addresses))
            
            # Get comment stats
            like_count = getattr(comment, 'likeCount', 0)
            
            processed_comment = {
                'id': comment_id,
                'text': text,
                'video_id': video_id,
                'author': user.get('uniqueId', 'unknown') if user else 'unknown',
                'user_info': user,
                'like_count': like_count,
                'contract_addresses': all_contracts,
                'ticker_symbols': ticker_symbols,
                'is_memecoin_related': self._is_memecoin_related(text),
                'type': 'tiktok_comment'
            }
            
            return processed_comment
            
        except Exception as e:
            self.logger.error(f"Error processing TikTok comment: {e}")
            return None
    
    def _calculate_video_engagement(self, stats: Dict[str, Any]) -> float:
        """Calculate engagement score for a TikTok video"""
        try:
            likes = stats.get('likeCount', 0)
            comments = stats.get('commentCount', 0)
            shares = stats.get('shareCount', 0)
            plays = stats.get('playCount', 0)
            
            # Calculate engagement rate
            if plays > 0:
                engagement_rate = (likes + comments * 2 + shares * 3) / plays
            else:
                engagement_rate = 0
            
            # Normalize to 0-1 scale
            import math
            normalized = math.log(max(engagement_rate * 1000 + 1, 1)) / 10
            
            return min(normalized, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating video engagement: {e}")
            return 0.0
    
    def _is_memecoin_related(self, text: str) -> bool:
        """Determine if TikTok content is memecoin-related"""
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Positive indicators
        positive_keywords = [
            'crypto', 'pump', 'moon', 'gem', 'token', 'coin', 'memecoin',
            'solana', 'sol', 'bitcoin', 'ethereum', 'defi', 'nft', 'web3',
            'blockchain', 'dex', 'investment', 'trading', 'hodl', 'diamond hands',
            'to the moon', 'lambo', 'ape in', 'buy the dip', 'altcoin',
            'cryptocurrency', 'digital currency', 'passive income'
        ]
        
        # TikTok specific positive indicators
        tiktok_crypto_terms = [
            'cryptotok', 'cryptotiktok', 'fintok', 'moneytok', 'investtok',
            'tradinglife', 'cryptotrading', 'cryptonews', 'cryptotips'
        ]
        
        positive_keywords.extend(tiktok_crypto_terms)
        
        # Negative indicators
        negative_keywords = [
            'scam', 'fake', 'warning', 'avoid', 'fraud', 'ponzi', 'pyramid'
        ]
        
        positive_count = sum(1 for keyword in positive_keywords if keyword in text_lower)
        negative_count = sum(1 for keyword in negative_keywords if keyword in text_lower)
        
        # Check for contract addresses or tickers
        has_contract = bool(self.contract_pattern.search(text) or self.ca_pattern.search(text))
        has_ticker = bool(self.ticker_pattern.search(text))
        
        # Check for crypto hashtags
        crypto_hashtags = [
            '#crypto', '#bitcoin', '#ethereum', '#solana', '#memecoin',
            '#defi', '#nft', '#blockchain', '#trading', '#investment',
            '#cryptotok', '#fintok', '#moneytok'
        ]
        has_crypto_hashtags = any(hashtag in text_lower for hashtag in crypto_hashtags)
        
        # Scoring logic
        if negative_count > 0:
            return False
        
        if has_contract or has_ticker:
            return True
        
        if has_crypto_hashtags:
            return True
        
        return positive_count >= 2
    
    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text"""
        if not text:
            return []
        
        hashtag_pattern = re.compile(r'#\\w+')
        hashtags = hashtag_pattern.findall(text)
        return [tag.lower() for tag in hashtags]
    
    async def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def get_hashtag_info(self, hashtag: str) -> Dict[str, Any]:
        """Get information about a hashtag"""
        if not self.api:
            return {}
        
        try:
            await self._rate_limit()
            
            hashtag_obj = self.api.hashtag(name=hashtag)
            
            return {
                'name': hashtag,
                'title': getattr(hashtag_obj, 'title', ''),
                'desc': getattr(hashtag_obj, 'desc', ''),
                'video_count': getattr(hashtag_obj, 'videoCount', 0),
                'view_count': getattr(hashtag_obj, 'viewCount', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting hashtag info for #{hashtag}: {e}")
            return {}
    
    async def search_users(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for TikTok users"""
        if not self.api:
            return []
        
        try:
            await self._rate_limit()
            
            users = []
            async for user in self.api.search.users(query, count=limit):
                user_info = {
                    'id': getattr(user, 'id', ''),
                    'username': getattr(user, 'uniqueId', ''),
                    'nickname': getattr(user, 'nickname', ''),
                    'verified': getattr(user, 'verified', False),
                    'follower_count': getattr(user, 'followerCount', 0),
                    'following_count': getattr(user, 'followingCount', 0),
                    'heart_count': getattr(user, 'heartCount', 0),
                    'video_count': getattr(user, 'videoCount', 0)
                }
                users.append(user_info)
            
            return users
            
        except Exception as e:
            self.logger.error(f"Error searching users for '{query}': {e}")
            return []
    
    async def monitor_hashtags_realtime(self, hashtags: List[str], keywords: List[str], callback):
        """Monitor hashtags in real-time (simplified polling approach)"""
        if not self.api:
            self.logger.warning("No TikTok API available for monitoring")
            return
        
        while True:
            try:
                for hashtag in hashtags:
                    videos = await self.search_hashtags([hashtag], limit=5)
                    
                    for video in videos:
                        if self._contains_keywords(video.get('description', ''), keywords):
                            await callback(video, 'tiktok')
                
                # Wait longer between checks due to rate limits
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in TikTok real-time monitoring: {e}")
                await asyncio.sleep(600)  # Wait 10 minutes on error
    
    def is_available(self) -> bool:
        """Check if TikTok API is available"""
        return self.api is not None
    
    async def get_video_details(self, video_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific video"""
        if not self.api:
            return {}
        
        try:
            await self._rate_limit()
            
            video = self.api.video(id=video_id)
            
            return {
                'id': video_id,
                'description': getattr(video, 'desc', ''),
                'author': getattr(video, 'author', {}),
                'stats': getattr(video, 'stats', {}),
                'music': getattr(video, 'music', {}),
                'challenges': getattr(video, 'challenges', []),
                'duetInfo': getattr(video, 'duetInfo', {}),
                'createTime': getattr(video, 'createTime', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting video details for {video_id}: {e}")
            return {}
