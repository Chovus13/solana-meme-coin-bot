import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import praw
from praw.exceptions import RedditAPIException, InvalidImplicitAuth, PRAWException 
import json

# This is for the __main__ test block, not essential for fixing the UnboundLocalError
try:
    from config import APIKeys 
except ImportError:
    APIKeys = None

class RedditMonitor:
    """Monitor Reddit for memecoin-related content"""
    
    def __init__(self, api_keys):
        """Initialize Reddit monitor with API keys"""
        # These first three print statements are for initial confirmation that keys arrive.
        # They can be commented out or removed once Reddit init is stable.
        print(f"[DEBUG] RedditMonitor.__init__ received api_keys.reddit_client_id: {getattr(api_keys, 'reddit_client_id', 'NOT_FOUND')}")
        print(f"[DEBUG] RedditMonitor.__init__ received api_keys.reddit_client_secret: {'********' if getattr(api_keys, 'reddit_client_secret', None) else 'NOT_FOUND'}")
        print(f"[DEBUG] RedditMonitor.__init__ received api_keys.reddit_username: {getattr(api_keys, 'reddit_username', 'NOT_FOUND')}")

        self.logger = logging.getLogger(__name__)
        self.api_keys = api_keys # Assign received api_keys to the instance attribute
        self.reddit = None

        # Temporary direct console handler for this logger
        # This ensures messages from this specific logger instance are visible on the console
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(funcName)s:%(lineno)d]')
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.DEBUG)  # Capture all levels from this logger for this handler
            self.logger.addHandler(console_handler)
            self.logger.propagate = False # Don't send to root logger if we have our own direct handler
            self.logger.info("Added temporary direct console handler to RedditMonitor logger (DEBUG level).")

        self.logger.info("Attempting to initialize RedditMonitor...")
        
        # Check if essential API keys for PRAW are present in the passed api_keys object
        if self.api_keys.reddit_client_id and self.api_keys.reddit_client_secret:
            self.logger.info("Client ID and Secret are present. Attempting PRAW client setup...")
            try:
                self.logger.info("Calling praw.Reddit(...) to create client.")
                self.reddit = praw.Reddit(
                    client_id=self.api_keys.reddit_client_id,
                    client_secret=self.api_keys.reddit_client_secret,
                    username=self.api_keys.reddit_username,
                    password=self.api_keys.reddit_password,
                    user_agent=self.api_keys.reddit_user_agent,
                    check_for_async=False
                )
                self.logger.info("praw.Reddit(...) call completed. PRAW client object created.")
                
                self.logger.info("Attempting self.reddit.user.me() for authentication check...")
                user = self.reddit.user.me()
                self.logger.debug(f"self.reddit.user.me() call completed. User object from PRAW: {user}")

                if user and hasattr(user, 'name') and user.name:
                    self.logger.info(f"Reddit API connection established successfully. Logged in as: {user.name}")
                else:
                    user_details_for_error = f"User object: {user}, Name attribute available: {hasattr(user, 'name') if user else 'N/A'}, User name: {getattr(user, 'name', 'N/A' if user else 'N/A')}"
                    self.logger.error(f"PRAW authentication failed: self.reddit.user.me() did not return a valid user with a name. Details: {user_details_for_error}")
                    raise Exception(f"PRAW authentication failed: self.reddit.user.me() did not return a valid user with a name. Details: {user_details_for_error}")
            
            except InvalidImplicitAuth as e: 
                self.logger.error(f"PRAW Initialization Error (InvalidImplicitAuth): {e}. This often means an issue with app type (e.g., script app needed for password flow) or credentials provided (username/password for the Reddit account). 2FA could also be a factor.", exc_info=True)
                self.reddit = None 
                raise  
            except PRAWException as e: 
                self.logger.error(f"PRAW Initialization Error (PRAWException): {e}. This can be due to various PRAW internal issues, incorrect credentials, network problems, or Reddit API errors.", exc_info=True)
                self.reddit = None 
                raise 
            except Exception as e: 
                self.logger.error(f"An UNEXPECTED error occurred during PRAW initialization: {e}", exc_info=True)
                self.reddit = None
                raise
        else:
            self.logger.warning("Reddit client_id or client_secret is missing in api_keys. Reddit monitoring will be disabled.")
            self.reddit = None # self.reddit is already None, but being explicit

        # Initialize regex patterns (should be outside the PRAW try/except)
        self.contract_pattern = re.compile(r'[A-HJ-NP-Z1-9]{32,44}')
        self.ticker_pattern = re.compile(r'\$([A-Z]{2,10})\b')
        self.ca_pattern = re.compile(r'CA:?\s*([A-HJ-NP-Z1-9]{32,44})')
        self.processed_posts = set()
        self.processed_comments = set()

    async def get_hot_posts(self, subreddit_name: str, keywords: List[str], limit: int = 25) -> List[Dict[str, Any]]:
        """Get hot posts from a subreddit"""
        if not self.reddit:
            self.logger.warning(f"Reddit client not initialized. Cannot get hot posts from r/{subreddit_name}.")
            return []
        
        try:
            self.logger.debug(f"Getting hot posts from r/{subreddit_name} with keywords: {keywords}")
            subreddit = self.reddit.subreddit(subreddit_name)
            hot_posts = []
            
            for submission in subreddit.hot(limit=limit):
                if self._contains_keywords(submission.title + " " + submission.selftext, keywords):
                    processed_post = await self._process_submission(submission, subreddit_name)
                    if processed_post:
                        hot_posts.append(processed_post)
            
            self.logger.info(f"Found {len(hot_posts)} relevant hot posts in r/{subreddit_name}")
            return hot_posts
            
        except Exception as e:
            self.logger.error(f"Error getting hot posts from r/{subreddit_name}: {e}", exc_info=True)
            return []
    
    async def get_new_posts(self, subreddit_name: str, keywords: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """Get new posts from a subreddit"""
        if not self.reddit:
            self.logger.warning(f"Reddit client not initialized. Cannot get new posts from r/{subreddit_name}.")
            return []
        
        try:
            self.logger.debug(f"Getting new posts from r/{subreddit_name} with keywords: {keywords}")
            subreddit = self.reddit.subreddit(subreddit_name)
            new_posts = []
            
            for submission in subreddit.new(limit=limit):
                post_time = datetime.fromtimestamp(submission.created_utc)
                if (datetime.now() - post_time).total_seconds() > 86400:  # 24 hours
                    continue
                
                if self._contains_keywords(submission.title + " " + submission.selftext, keywords):
                    processed_post = await self._process_submission(submission, subreddit_name)
                    if processed_post:
                        new_posts.append(processed_post)
            
            self.logger.info(f"Found {len(new_posts)} relevant new posts in r/{subreddit_name}")
            return new_posts
            
        except Exception as e:
            self.logger.error(f"Error getting new posts from r/{subreddit_name}: {e}", exc_info=True)
            return []
    
    async def search_posts(self, query: str, subreddit_names: List[str], limit: int = 25) -> List[Dict[str, Any]]:
        """Search for posts across multiple subreddits"""
        if not self.reddit:
            self.logger.warning("Reddit client not initialized. Cannot search posts.")
            return []
        
        search_results = []
        self.logger.debug(f"Searching for query '{query}' in subreddits: {subreddit_names}")
        for subreddit_name in subreddit_names:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                for submission in subreddit.search(query, sort='new', time_filter='day', limit=limit):
                    processed_post = await self._process_submission(submission, subreddit_name)
                    if processed_post:
                        search_results.append(processed_post)
            except Exception as e:
                self.logger.error(f"Error searching in r/{subreddit_name}: {e}", exc_info=True)
                continue
        
        self.logger.info(f"Found {len(search_results)} posts from search for query '{query}'")
        return search_results
    
    async def get_post_comments(self, post_id: str, keywords: List[str], limit: int = 100) -> List[Dict[str, Any]]:
        """Get comments from a specific post"""
        if not self.reddit:
            self.logger.warning(f"Reddit client not initialized. Cannot get comments for post {post_id}.")
            return []
        
        try:
            self.logger.debug(f"Getting comments for post {post_id} with keywords: {keywords}")
            submission = self.reddit.submission(id=post_id)
            submission.comments.replace_more(limit=0) 
            
            relevant_comments = []
            for comment in submission.comments.list():
                if hasattr(comment, 'body') and self._contains_keywords(comment.body, keywords):
                    processed_comment = await self._process_comment(comment, submission.subreddit.display_name)
                    if processed_comment:
                        relevant_comments.append(processed_comment)
            
            self.logger.info(f"Found {len(relevant_comments)} relevant comments for post {post_id}")
            return relevant_comments[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting comments for post {post_id}: {e}", exc_info=True)
            return []
    
    async def monitor_user(self, username: str, keywords: List[str], limit: int = 25) -> List[Dict[str, Any]]:
        """Monitor a specific user's posts and comments"""
        if not self.reddit:
            self.logger.warning(f"Reddit client not initialized. Cannot monitor user u/{username}.")
            return []
        
        try:
            self.logger.debug(f"Monitoring user u/{username} for keywords: {keywords}")
            user = self.reddit.redditor(username)
            user_content = []
            
            for submission in user.submissions.new(limit=limit):
                if self._contains_keywords(submission.title + " " + submission.selftext, keywords):
                    processed_post = await self._process_submission(submission, submission.subreddit.display_name)
                    if processed_post:
                        user_content.append(processed_post)
            
            for comment in user.comments.new(limit=limit):
                if hasattr(comment, 'body') and self._contains_keywords(comment.body, keywords):
                    processed_comment = await self._process_comment(comment, comment.subreddit.display_name)
                    if processed_comment:
                        user_content.append(processed_comment)
            
            self.logger.info(f"Found {len(user_content)} relevant items from user u/{username}")
            return user_content
            
        except Exception as e:
            self.logger.error(f"Error monitoring user u/{username}: {e}", exc_info=True)
            return []
    
    def _contains_keywords(self, text: str, keywords: List[str]) -> bool:
        if not text: return False
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)
    
    async def _process_submission(self, submission, subreddit_name: str) -> Optional[Dict[str, Any]]:
        try:
            post_id = submission.id
            if post_id in self.processed_posts: return None
            self.processed_posts.add(post_id)
            
            full_text = submission.title + " " + submission.selftext
            contract_addresses = self.contract_pattern.findall(full_text)
            ticker_symbols = self.ticker_pattern.findall(full_text.upper()) # Ensure .upper() for ticker
            ca_addresses = self.ca_pattern.findall(full_text)
            all_contracts = list(set(contract_addresses + ca_addresses))
            
            engagement_score = self._calculate_post_engagement(submission)
            is_memecoin_related = self._is_memecoin_related(full_text)
            
            post_time = datetime.fromtimestamp(submission.created_utc)
            age_hours = (datetime.now() - post_time).total_seconds() / 3600
            
            return {
                'id': post_id, 'title': submission.title, 'content': submission.selftext,
                'text': full_text, 'author': str(submission.author) if submission.author else '[deleted]',
                'subreddit': subreddit_name, 'created_at': post_time.isoformat(),
                'url': f"https://reddit.com{submission.permalink}", 'score': submission.score,
                'upvote_ratio': submission.upvote_ratio, 'num_comments': submission.num_comments,
                'contract_addresses': all_contracts, 'ticker_symbols': ticker_symbols,
                'engagement_score': engagement_score, 'is_memecoin_related': is_memecoin_related,
                'age_hours': age_hours, 'flair': submission.link_flair_text,
                'is_self': submission.is_self, 'type': 'post'
            }
        except Exception as e:
            self.logger.error(f"Error processing submission {submission.id if hasattr(submission, 'id') else 'UNKNOWN'}: {e}", exc_info=True)
            return None
    
    async def _process_comment(self, comment, subreddit_name: str) -> Optional[Dict[str, Any]]:
        try:
            comment_id = comment.id
            if comment_id in self.processed_comments: return None
            self.processed_comments.add(comment_id)
            
            if not hasattr(comment, 'body') or comment.body in ['[deleted]', '[removed]']: return None
            
            contract_addresses = self.contract_pattern.findall(comment.body)
            ticker_symbols = self.ticker_pattern.findall(comment.body.upper()) # Ensure .upper() for ticker
            ca_addresses = self.ca_pattern.findall(comment.body)
            all_contracts = list(set(contract_addresses + ca_addresses))
            
            engagement_score = self._calculate_comment_engagement(comment)
            is_memecoin_related = self._is_memecoin_related(comment.body)
            
            comment_time = datetime.fromtimestamp(comment.created_utc)
            age_hours = (datetime.now() - comment_time).total_seconds() / 3600
            
            return {
                'id': comment_id, 'text': comment.body, 'content': comment.body,
                'author': str(comment.author) if comment.author else '[deleted]',
                'subreddit': subreddit_name, 'created_at': comment_time.isoformat(),
                'url': f"https://reddit.com{comment.permalink}", 'score': comment.score,
                'contract_addresses': all_contracts, 'ticker_symbols': ticker_symbols,
                'engagement_score': engagement_score, 'is_memecoin_related': is_memecoin_related,
                'age_hours': age_hours, 'parent_id': comment.parent_id, 'type': 'comment'
            }
        except Exception as e:
            self.logger.error(f"Error processing comment {comment.id if hasattr(comment, 'id') else 'UNKNOWN'}: {e}", exc_info=True)
            return None
            
    def _calculate_post_engagement(self, submission) -> float:
        try:
            # Add checks for attribute existence if necessary
            score = getattr(submission, 'score', 0)
            num_comments = getattr(submission, 'num_comments', 0)
            upvote_ratio = getattr(submission, 'upvote_ratio', 0.0)
            engagement = (score * upvote_ratio) + (num_comments * 2)
            import math
            normalized = math.log(max(engagement + 1, 1)) / 15
            return min(normalized, 1.0)
        except Exception as e:
            self.logger.error(f"Error calculating post engagement: {e}", exc_info=True)
            return 0.0

    def _calculate_comment_engagement(self, comment) -> float:
        try:
            score = getattr(comment, 'score', 0)
            import math
            normalized = math.log(max(score + 1, 1)) / 10
            return min(normalized, 1.0)
        except Exception as e:
            self.logger.error(f"Error calculating comment engagement: {e}", exc_info=True)
            return 0.0

    def _is_memecoin_related(self, text: str) -> bool:
        if not text: return False
        text_lower = text.lower()
        positive_keywords = [
            'pump', 'moon', 'gem', 'new token', 'just launched', 'fair launch',
            'presale', 'memecoin', 'meme coin', 'altcoin', 'defi', 'dex',
            'raydium', 'jupiter', 'pumpfun', 'pump.fun', 'solana', 'sol',
            'contract', 'ca:', 'ticker', 'symbol', 'address', 'stealth launch',
            'dev doxxed', 'liquidity locked', 'renounced', 'safu'
        ]
        negative_keywords = [
            'scam', 'rug', 'rugpull', 'avoid', 'warning', 'caution', 'fake',
            'honeypot', 'suspicious', 'fraud', 'dump', 'exit scam'
        ]
        positive_count = sum(1 for keyword in positive_keywords if keyword in text_lower)
        negative_count = sum(1 for keyword in negative_keywords if keyword in text_lower)
        
        has_contract = bool(self.contract_pattern.search(text) or self.ca_pattern.search(text))
        has_ticker = bool(self.ticker_pattern.search(text.upper())) # Ensure .upper() for ticker search
        
        if negative_count > positive_count and not (has_contract or has_ticker) : return False # More lenient if contract/ticker present
        if has_contract or has_ticker : return True
        return positive_count >= 2

    async def get_subreddit_info(self, subreddit_name: str) -> Dict[str, Any]:
        if not self.reddit:
            self.logger.warning(f"Reddit client not initialized. Cannot get info for r/{subreddit_name}.")
            return {}
        try:
            self.logger.debug(f"Getting info for subreddit r/{subreddit_name}")
            subreddit = self.reddit.subreddit(subreddit_name)
            return {
                'name': subreddit.display_name, 'title': subreddit.title,
                'description': subreddit.description, 'subscribers': subreddit.subscribers,
                'active_users': subreddit.accounts_active, 'created_utc': subreddit.created_utc,
                'over18': subreddit.over18, 'public_description': subreddit.public_description
            }
        except Exception as e:
            self.logger.error(f"Error getting subreddit info for r/{subreddit_name}: {e}", exc_info=True)
            return {}

    async def get_trending_posts(self, subreddit_names: List[str], hours_back: int = 24) -> List[Dict[str, Any]]:
        if not self.reddit:
            self.logger.warning("Reddit client not initialized. Cannot get trending posts.")
            return []
        
        trending_posts = []
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        self.logger.debug(f"Getting trending posts from {subreddit_names} within last {hours_back} hours.")
        
        for subreddit_name in subreddit_names:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                for submission in subreddit.hot(limit=10): # Check more posts to find trending ones
                    post_time = datetime.fromtimestamp(submission.created_utc)
                    if post_time > cutoff_time:
                        age_hours = max((datetime.now() - post_time).total_seconds() / 3600, 0.1) # Avoid division by zero, ensure minimum age
                        trending_score = getattr(submission, 'score', 0) / age_hours
                        if trending_score > 10: 
                            processed_post = await self._process_submission(submission, subreddit_name)
                            if processed_post:
                                processed_post['trending_score'] = trending_score
                                trending_posts.append(processed_post)
            except Exception as e:
                self.logger.error(f"Error getting trending posts from r/{subreddit_name}: {e}", exc_info=True)
                continue
        
        trending_posts.sort(key=lambda x: x.get('trending_score', 0), reverse=True)
        self.logger.info(f"Found {len(trending_posts)} trending posts.")
        return trending_posts
    
    async def monitor_real_time(self, subreddit_names: List[str], keywords: List[str], callback):
        if not self.reddit:
            self.logger.warning("No Reddit client available for real-time monitoring.")
            return
        
        subreddit_string = '+'.join(subreddit_names)
        self.logger.info(f"Starting real-time monitoring for subreddits: {subreddit_string}, keywords: {keywords}")
        
        try:
            subreddit = self.reddit.subreddit(subreddit_string)
            for submission in subreddit.stream.submissions(skip_existing=True, pause_after=-1): # pause_after=-1 for continuous stream
                if submission is None:
                    await asyncio.sleep(0.1) # Small sleep if pause_after=0 yields None frequently
                    continue
                
                try:
                    # self.logger.debug(f"Streamed new submission: {submission.id} from r/{submission.subreddit.display_name}")
                    full_text = submission.title + " " + submission.selftext
                    if self._contains_keywords(full_text, keywords):
                        self.logger.info(f"Keyword match in new submission {submission.id} from r/{submission.subreddit.display_name}")
                        processed_post = await self._process_submission(submission, submission.subreddit.display_name)
                        if processed_post:
                            await callback(processed_post, 'reddit')
                except praw.exceptions.PRAWException as praw_exc: # More specific PRAW exception
                    self.logger.error(f"PRAW error processing streamed submission {getattr(submission, 'id', 'UNKNOWN')}: {praw_exc}", exc_info=True)
                    # Decide if to continue or break/reconnect based on error type
                    if "Connection broken" in str(praw_exc) or "Connection reset" in str(praw_exc): # Example conditions
                        self.logger.warning("Stream connection issue, attempting to restart stream...")
                        break # Break to allow outer loop to re-establish stream
                    await asyncio.sleep(5) # Wait a bit before processing next item from stream on other errors
                except Exception as e:
                    self.logger.error(f"Error processing streamed submission {getattr(submission, 'id', 'UNKNOWN')}: {e}", exc_info=True)
                    await asyncio.sleep(5) # Wait before processing next item
                
        except praw.exceptions.PRAWException as praw_exc_stream: # Catch PRAW exceptions on the stream itself
             self.logger.error(f"PRAW error in Reddit real-time monitoring stream for {subreddit_string}: {praw_exc_stream}", exc_info=True)
             # Consider a limited number of retries or a longer backoff
        except Exception as e:
            self.logger.error(f"Fatal error in Reddit real-time monitoring for {subreddit_string}: {e}", exc_info=True)
            # Fallback or re-raise might be needed here depending on desired resilience
            # For now, just log and exit this monitoring attempt. Outer logic might retry.

    # Removed fallback_monitoring as real-time stream should be prioritized and managed with retries if needed.
    # If real-time fails consistently, periodic polling (get_new_posts) is the fallback handled by the main bot loop.

    def is_connected(self) -> bool:
        """Check if the PRAW client is initialized."""
        return self.reddit is not None

    @staticmethod
    def test_praw_connection(client_id: str, client_secret: str, username: str, password: str, user_agent: str):
        logger = logging.getLogger("RedditMonitorTest")
        if not logger.handlers:
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        logger.info("Attempting to test PRAW connection...")
        if not client_id or not client_secret:
            logger.error("Client ID or Client Secret is missing. Cannot test connection.")
            return False
        try:
            reddit = praw.Reddit(
                client_id=client_id, client_secret=client_secret, username=username,
                password=password, user_agent=user_agent, check_for_async=False
            )
            logger.info("PRAW client initialized. Testing authentication...")
            user = reddit.user.me()
            if user and user.name: # Added check for user.name
                logger.info(f"Successfully authenticated as Reddit user: {user.name}")
                logger.info("Attempting to fetch 1 hot post from r/test...")
                try:
                    subreddit = reddit.subreddit("test")
                    for submission in subreddit.hot(limit=1):
                        logger.info(f"Successfully fetched post: {submission.title}")
                    logger.info("PRAW connection test successful!")
                    return True
                except Exception as e_fetch:
                    logger.error(f"Error fetching posts from r/test: {e_fetch}", exc_info=True)
                    return False
            else:
                logger.error(f"Authentication failed: reddit.user.me() returned user: {user} (name: {getattr(user, 'name', 'N/A') if user else 'User is None'}).")
                return False
        except InvalidImplicitAuth as e_auth:
            logger.error(f"PRAW connection test failed (InvalidImplicitAuth): {e_auth}. Ensure script-type app credentials with username/password.", exc_info=True)
            return False
        except PRAWException as e_praw: # Changed from PrawcoreException
            logger.error(f"PRAW connection test failed (PRAWException): {e_praw}. Check credentials, user agent, network.", exc_info=True)
            return False
        except Exception as e_general:
            logger.error(f"An unexpected error occurred during PRAW connection test: {e_general}", exc_info=True)
            return False

# if __name__ == '__main__': # Keep this commented out unless specifically running this file for test
#     print("Running RedditMonitor PRAW connection test script...")
#     # ... (rest of the __main__ block for testing) ...
#     # This requires careful path setup for config and .env if run directly
#     # For now, primary testing is via the main bot application
