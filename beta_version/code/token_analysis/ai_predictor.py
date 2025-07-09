"""
AI predictor module for predicting memecoin success using machine learning
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import pickle
import os
import json
import re

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.impute import SimpleImputer
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import tensorflow as tf
    from tensorflow import keras
    HAS_TENSORFLOW = True
except ImportError:
    HAS_TENSORFLOW = False

try:
    from transformers import pipeline, AutoTokenizer, AutoModel
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

class AIPredictor:
    """AI-powered predictor for memecoin success"""
    
    def __init__(self, model_dir: str = "data/models"):
        """Initialize AI predictor"""
        self.logger = logging.getLogger(__name__)
        self.model_dir = model_dir
        
        # Create model directory if it doesn't exist
        os.makedirs(model_dir, exist_ok=True)
        
        # Initialize models
        self.models = {}
        self.scalers = {}
        self.feature_columns = []
        
        # Sentiment analyzer
        self.sentiment_analyzer = None
        if HAS_TRANSFORMERS:
            try:
                self.sentiment_analyzer = pipeline(
                    "sentiment-analysis",
                    model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                    return_all_scores=True
                )
            except Exception as e:
                self.logger.warning(f"Could not load sentiment analyzer: {e}")
        
        # Historical data for training
        self.historical_data = []
        self.training_data_file = os.path.join(model_dir, "training_data.json")
        
        # Load existing models and data
        self._load_models()
        self._load_training_data()
        
        # Feature importance tracking
        self.feature_importance = {}
        
        self.logger.info("AI Predictor initialized")
    
    async def predict_success(self, token_discovery, market_data: Dict[str, Any], 
                            safety_score: int) -> Dict[str, Any]:
        """Predict token success probability"""
        try:
            # Extract features
            features = self._extract_features(token_discovery, market_data, safety_score)
            
            # Get predictions from multiple models
            predictions = {}
            
            # Machine learning predictions
            if HAS_SKLEARN and 'success_classifier' in self.models:
                ml_prediction = await self._predict_with_ml(features)
                predictions['ml_prediction'] = ml_prediction
            
            # Deep learning predictions
            if HAS_TENSORFLOW and 'success_neural_net' in self.models:
                dl_prediction = await self._predict_with_dl(features)
                predictions['dl_prediction'] = dl_prediction
            
            # Sentiment analysis
            sentiment_score = await self._analyze_sentiment(token_discovery.original_message)
            predictions['sentiment_score'] = sentiment_score
            
            # Technical analysis
            technical_score = self._analyze_technical_indicators(market_data)
            predictions['technical_score'] = technical_score
            
            # Social media hype score
            social_hype_score = self._calculate_social_hype(token_discovery)
            predictions['social_hype_score'] = social_hype_score
            
            # Combine predictions
            final_prediction = self._ensemble_predictions(predictions)
            
            # Calculate confidence
            confidence = self._calculate_confidence(predictions, features)
            
            result = {
                'success_probability': final_prediction,
                'confidence': confidence,
                'individual_predictions': predictions,
                'features_used': features,
                'prediction_timestamp': datetime.utcnow().isoformat(),
                'model_version': '1.0'
            }
            
            # Store for future training
            await self._store_prediction_data(token_discovery, market_data, safety_score, result)
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error predicting success: {e}")
            return {
                'success_probability': 0.5,
                'confidence': 0.1,
                'error': str(e)
            }
    
    def _extract_features(self, token_discovery, market_data: Dict[str, Any], 
                         safety_score: int) -> Dict[str, float]:
        """Extract features for ML prediction"""
        try:
            features = {}
            
            # Safety features
            features['safety_score'] = safety_score / 100.0  # Normalize to 0-1
            
            # Market features
            features['market_cap'] = np.log1p(market_data.get('unified_market_cap', 1))
            features['volume_24h'] = np.log1p(market_data.get('unified_volume_24h', 1))
            features['liquidity'] = np.log1p(market_data.get('unified_liquidity', 1))
            features['holder_count'] = np.log1p(market_data.get('holder_count', 1))
            features['age_hours'] = min(market_data.get('age_hours', 24), 168)  # Cap at 1 week
            features['volume_mc_ratio'] = market_data.get('volume_mc_ratio', 0)
            features['liquidity_mc_ratio'] = market_data.get('liquidity_mc_ratio', 0)
            features['distribution_score'] = market_data.get('distribution_score', 0)
            
            # Token features
            features['is_pumpfun_token'] = 1.0 if market_data.get('is_pumpfun_token', False) else 0.0
            features['liquidity_locked'] = 1.0 if market_data.get('liquidity_locked', False) else 0.0
            features['mint_disabled'] = 1.0 if market_data.get('mint_disabled', False) else 0.0
            
            # Social features
            features['source_twitter'] = 1.0 if token_discovery.source == 'twitter' else 0.0
            features['source_reddit'] = 1.0 if token_discovery.source == 'reddit' else 0.0
            features['source_discord'] = 1.0 if token_discovery.source == 'discord' else 0.0
            features['source_telegram'] = 1.0 if token_discovery.source == 'telegram' else 0.0
            features['source_tiktok'] = 1.0 if token_discovery.source == 'tiktok' else 0.0
            
            features['confidence_score'] = token_discovery.confidence_score
            
            # Text features
            message_features = self._extract_text_features(token_discovery.original_message)
            features.update(message_features)
            
            # Time features
            hour = token_discovery.timestamp.hour
            features['hour_sin'] = np.sin(2 * np.pi * hour / 24)
            features['hour_cos'] = np.cos(2 * np.pi * hour / 24)
            
            day_of_week = token_discovery.timestamp.weekday()
            features['weekday'] = 1.0 if day_of_week < 5 else 0.0  # 1 for weekday, 0 for weekend
            
            # Replace any NaN or inf values
            for key, value in features.items():
                if np.isnan(value) or np.isinf(value):
                    features[key] = 0.0
            
            return features
        
        except Exception as e:
            self.logger.error(f"Error extracting features: {e}")
            return {}
    
    def _extract_text_features(self, text: str) -> Dict[str, float]:
        """Extract features from text content"""
        try:
            if not text:
                return {}
            
            text_lower = text.lower()
            features = {}
            
            # Length features
            features['text_length'] = min(len(text), 1000) / 1000.0  # Normalize
            features['word_count'] = min(len(text.split()), 200) / 200.0
            
            # Keyword presence
            bullish_keywords = [
                'moon', 'pump', 'gem', 'diamond', 'hands', 'hodl', 'lambo',
                'rocket', 'fire', 'bullish', 'ape', 'buy', 'long', 'bull'
            ]
            
            bearish_keywords = [
                'dump', 'rug', 'scam', 'fake', 'avoid', 'sell', 'short',
                'bearish', 'caution', 'warning', 'suspicious'
            ]
            
            hype_keywords = [
                'new', 'launched', 'just', 'now', 'early', 'presale',
                'fair launch', 'stealth', 'gem', 'next', '100x', '1000x'
            ]
            
            features['bullish_score'] = sum(1 for word in bullish_keywords if word in text_lower) / len(bullish_keywords)
            features['bearish_score'] = sum(1 for word in bearish_keywords if word in text_lower) / len(bearish_keywords)
            features['hype_score'] = sum(1 for word in hype_keywords if word in text_lower) / len(hype_keywords)
            
            # Emoji features
            rocket_emojis = ['🚀', '📈', '💎', '🌙', '💰', '🔥']
            features['rocket_emoji_count'] = sum(text.count(emoji) for emoji in rocket_emojis)
            
            # Contract address presence
            features['has_contract_address'] = 1.0 if re.search(r'[A-HJ-NP-Z1-9]{32,44}', text) else 0.0
            
            # Ticker presence
            features['has_ticker'] = 1.0 if re.search(r'\\$[A-Z]{2,10}\\b', text) else 0.0
            
            # URL presence
            features['has_url'] = 1.0 if re.search(r'http[s]?://|www\\.', text) else 0.0
            
            # Exclamation marks (hype indicator)
            features['exclamation_ratio'] = text.count('!') / max(len(text), 1)
            
            # Caps ratio (shouting/excitement)
            caps_count = sum(1 for c in text if c.isupper())
            features['caps_ratio'] = caps_count / max(len(text), 1)
            
            return features
        
        except Exception as e:
            self.logger.error(f"Error extracting text features: {e}")
            return {}
    
    async def _predict_with_ml(self, features: Dict[str, float]) -> float:
        """Make prediction using machine learning model"""
        try:
            if 'success_classifier' not in self.models:
                return 0.5
            
            model = self.models['success_classifier']
            scaler = self.scalers.get('success_classifier')
            
            # Prepare feature vector
            feature_vector = np.array([features.get(col, 0.0) for col in self.feature_columns]).reshape(1, -1)
            
            # Scale features if scaler exists
            if scaler:
                feature_vector = scaler.transform(feature_vector)
            
            # Make prediction
            prediction = model.predict_proba(feature_vector)[0]
            
            # Return probability of success (assuming class 1 is success)
            return prediction[1] if len(prediction) > 1 else prediction[0]
        
        except Exception as e:
            self.logger.error(f"Error in ML prediction: {e}")
            return 0.5
    
    async def _predict_with_dl(self, features: Dict[str, float]) -> float:
        """Make prediction using deep learning model"""
        try:
            if not HAS_TENSORFLOW or 'success_neural_net' not in self.models:
                return 0.5
            
            model = self.models['success_neural_net']
            
            # Prepare feature vector
            feature_vector = np.array([features.get(col, 0.0) for col in self.feature_columns]).reshape(1, -1)
            
            # Make prediction
            prediction = model.predict(feature_vector, verbose=0)[0][0]
            
            return float(prediction)
        
        except Exception as e:
            self.logger.error(f"Error in DL prediction: {e}")
            return 0.5
    
    async def _analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment of the text"""
        try:
            if not self.sentiment_analyzer or not text:
                return 0.5
            
            # Get sentiment scores
            results = self.sentiment_analyzer(text[:512])  # Limit text length
            
            if results:
                # Convert to positive sentiment score
                for result in results[0]:
                    if result['label'] == 'LABEL_2':  # Positive
                        return result['score']
                    elif result['label'] == 'LABEL_1':  # Neutral
                        return 0.5
                    elif result['label'] == 'LABEL_0':  # Negative
                        return 1.0 - result['score']
            
            return 0.5
        
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment: {e}")
            return 0.5
    
    def _analyze_technical_indicators(self, market_data: Dict[str, Any]) -> float:
        """Analyze technical indicators"""
        try:
            score = 0.0
            factors = 0
            
            # Volume indicator
            volume_mc_ratio = market_data.get('volume_mc_ratio', 0)
            if volume_mc_ratio > 0.1:  # High volume relative to market cap
                score += 0.8
            elif volume_mc_ratio > 0.05:
                score += 0.6
            elif volume_mc_ratio > 0.01:
                score += 0.4
            else:
                score += 0.2
            factors += 1
            
            # Liquidity indicator
            liquidity_mc_ratio = market_data.get('liquidity_mc_ratio', 0)
            if liquidity_mc_ratio > 0.2:  # Very good liquidity
                score += 0.9
            elif liquidity_mc_ratio > 0.1:
                score += 0.7
            elif liquidity_mc_ratio > 0.05:
                score += 0.5
            else:
                score += 0.2
            factors += 1
            
            # Age factor (newer tokens have more potential but also more risk)
            age_hours = market_data.get('age_hours', 24)
            if age_hours < 6:  # Very new
                score += 0.7
            elif age_hours < 24:  # Less than a day
                score += 0.8
            elif age_hours < 72:  # Less than 3 days
                score += 0.6
            else:
                score += 0.4
            factors += 1
            
            # Holder distribution
            distribution_score = market_data.get('distribution_score', 0)
            score += distribution_score
            factors += 1
            
            return score / factors if factors > 0 else 0.5
        
        except Exception as e:
            self.logger.error(f"Error analyzing technical indicators: {e}")
            return 0.5
    
    def _calculate_social_hype(self, token_discovery) -> float:
        """Calculate social media hype score"""
        try:
            hype_score = 0.0
            
            # Base confidence score
            hype_score += token_discovery.confidence_score * 0.4
            
            # Source credibility
            source_weights = {
                'twitter': 0.3,
                'reddit': 0.25,
                'telegram': 0.2,
                'discord': 0.15,
                'tiktok': 0.1
            }
            hype_score += source_weights.get(token_discovery.source, 0.1)
            
            # Time factor (recent discoveries are more hyped)
            time_diff = (datetime.now() - token_discovery.timestamp).total_seconds()
            time_factor = max(0, 1.0 - (time_diff / 3600))  # Decay over 1 hour
            hype_score += time_factor * 0.3
            
            return min(1.0, hype_score)
        
        except Exception as e:
            self.logger.error(f"Error calculating social hype: {e}")
            return 0.5
    
    def _ensemble_predictions(self, predictions: Dict[str, float]) -> float:
        """Combine multiple predictions into final score"""
        try:
            weights = {
                'ml_prediction': 0.25,
                'dl_prediction': 0.25,
                'sentiment_score': 0.2,
                'technical_score': 0.2,
                'social_hype_score': 0.1
            }
            
            total_weight = 0.0
            weighted_sum = 0.0
            
            for pred_type, score in predictions.items():
                if pred_type in weights and score is not None:
                    weight = weights[pred_type]
                    weighted_sum += score * weight
                    total_weight += weight
            
            if total_weight > 0:
                return weighted_sum / total_weight
            else:
                return 0.5
        
        except Exception as e:
            self.logger.error(f"Error in ensemble predictions: {e}")
            return 0.5
    
    def _calculate_confidence(self, predictions: Dict[str, float], features: Dict[str, float]) -> float:
        """Calculate confidence in the prediction"""
        try:
            confidence_factors = []
            
            # Model agreement
            model_predictions = [
                predictions.get('ml_prediction'),
                predictions.get('dl_prediction')
            ]
            valid_predictions = [p for p in model_predictions if p is not None]
            
            if len(valid_predictions) >= 2:
                std_dev = np.std(valid_predictions)
                agreement = 1.0 - (std_dev * 2)  # Higher agreement = higher confidence
                confidence_factors.append(max(0, agreement))
            
            # Feature completeness
            non_zero_features = sum(1 for v in features.values() if v != 0.0)
            completeness = non_zero_features / max(len(features), 1)
            confidence_factors.append(completeness)
            
            # Data quality indicators
            safety_score = features.get('safety_score', 0)
            confidence_factors.append(safety_score)
            
            market_cap = features.get('market_cap', 0)
            if market_cap > 0:
                confidence_factors.append(0.8)
            else:
                confidence_factors.append(0.2)
            
            return np.mean(confidence_factors) if confidence_factors else 0.5
        
        except Exception as e:
            self.logger.error(f"Error calculating confidence: {e}")
            return 0.5
    
    async def _store_prediction_data(self, token_discovery, market_data: Dict[str, Any], 
                                   safety_score: int, prediction_result: Dict[str, Any]):
        """Store prediction data for future training"""
        try:
            data_point = {
                'timestamp': datetime.utcnow().isoformat(),
                'token_address': token_discovery.contract_address,
                'symbol': token_discovery.symbol,
                'source': token_discovery.source,
                'safety_score': safety_score,
                'market_data': market_data,
                'prediction': prediction_result,
                'features': prediction_result.get('features_used', {}),
                'message': token_discovery.original_message
            }
            
            self.historical_data.append(data_point)
            
            # Save to file periodically
            if len(self.historical_data) % 10 == 0:
                await self._save_training_data()
        
        except Exception as e:
            self.logger.error(f"Error storing prediction data: {e}")
    
    async def train_models(self, historical_results: List[Dict[str, Any]] = None):
        """Train or retrain the prediction models"""
        try:
            if not HAS_SKLEARN:
                self.logger.warning("Scikit-learn not available, skipping model training")
                return
            
            # Use provided data or load from storage
            training_data = historical_results or self.historical_data
            
            if len(training_data) < 50:  # Need minimum data for training
                self.logger.warning("Insufficient training data")
                return
            
            # Prepare training data
            X, y = self._prepare_training_data(training_data)
            
            if len(X) == 0:
                self.logger.warning("No valid training data prepared")
                return
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train Random Forest
            rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
            rf_model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = rf_model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            self.logger.info(f"Random Forest accuracy: {accuracy:.3f}")
            
            # Store model and scaler
            self.models['success_classifier'] = rf_model
            self.scalers['success_classifier'] = scaler
            
            # Train Gradient Boosting
            gb_model = GradientBoostingClassifier(n_estimators=100, random_state=42)
            gb_model.fit(X_train_scaled, y_train)
            
            y_pred_gb = gb_model.predict(X_test_scaled)
            accuracy_gb = accuracy_score(y_test, y_pred_gb)
            self.logger.info(f"Gradient Boosting accuracy: {accuracy_gb:.3f}")
            
            # Use the better model
            if accuracy_gb > accuracy:
                self.models['success_classifier'] = gb_model
                self.logger.info("Using Gradient Boosting model")
            else:
                self.logger.info("Using Random Forest model")
            
            # Train neural network if TensorFlow is available
            if HAS_TENSORFLOW:
                await self._train_neural_network(X_train_scaled, y_train, X_test_scaled, y_test)
            
            # Save models
            await self._save_models()
            
            self.logger.info("Model training completed")
        
        except Exception as e:
            self.logger.error(f"Error training models: {e}")
    
    def _prepare_training_data(self, training_data: List[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data for machine learning"""
        try:
            features_list = []
            labels = []
            
            for data_point in training_data:
                if 'features' in data_point and 'actual_outcome' in data_point:
                    features = data_point['features']
                    outcome = data_point['actual_outcome']  # This would need to be added later
                    
                    features_list.append(features)
                    labels.append(1 if outcome == 'success' else 0)
            
            if not features_list:
                return np.array([]), np.array([])
            
            # Convert to DataFrame for easier handling
            df = pd.DataFrame(features_list)
            
            # Store feature columns
            self.feature_columns = list(df.columns)
            
            # Handle missing values
            imputer = SimpleImputer(strategy='mean')
            X = imputer.fit_transform(df)
            y = np.array(labels)
            
            return X, y
        
        except Exception as e:
            self.logger.error(f"Error preparing training data: {e}")
            return np.array([]), np.array([])
    
    async def _train_neural_network(self, X_train, y_train, X_test, y_test):
        """Train a neural network model"""
        try:
            if not HAS_TENSORFLOW:
                return
            
            # Build model
            model = keras.Sequential([
                keras.layers.Dense(128, activation='relu', input_shape=(X_train.shape[1],)),
                keras.layers.Dropout(0.3),
                keras.layers.Dense(64, activation='relu'),
                keras.layers.Dropout(0.3),
                keras.layers.Dense(32, activation='relu'),
                keras.layers.Dense(1, activation='sigmoid')
            ])
            
            model.compile(
                optimizer='adam',
                loss='binary_crossentropy',
                metrics=['accuracy']
            )
            
            # Train
            history = model.fit(
                X_train, y_train,
                epochs=50,
                batch_size=32,
                validation_data=(X_test, y_test),
                verbose=0
            )
            
            # Evaluate
            test_accuracy = model.evaluate(X_test, y_test, verbose=0)[1]
            self.logger.info(f"Neural network accuracy: {test_accuracy:.3f}")
            
            # Store model
            self.models['success_neural_net'] = model
        
        except Exception as e:
            self.logger.error(f"Error training neural network: {e}")
    
    def _load_models(self):
        """Load saved models"""
        try:
            model_files = {
                'success_classifier': 'success_classifier.pkl',
                'success_neural_net': 'success_neural_net.h5'
            }
            
            for model_name, filename in model_files.items():
                filepath = os.path.join(self.model_dir, filename)
                
                if os.path.exists(filepath):
                    if model_name == 'success_neural_net' and HAS_TENSORFLOW:
                        self.models[model_name] = keras.models.load_model(filepath)
                    elif model_name == 'success_classifier':
                        with open(filepath, 'rb') as f:
                            self.models[model_name] = pickle.load(f)
                    
                    self.logger.info(f"Loaded model: {model_name}")
            
            # Load scalers
            scaler_file = os.path.join(self.model_dir, 'scalers.pkl')
            if os.path.exists(scaler_file):
                with open(scaler_file, 'rb') as f:
                    self.scalers = pickle.load(f)
            
            # Load feature columns
            features_file = os.path.join(self.model_dir, 'feature_columns.json')
            if os.path.exists(features_file):
                with open(features_file, 'r') as f:
                    self.feature_columns = json.load(f)
        
        except Exception as e:
            self.logger.error(f"Error loading models: {e}")
    
    async def _save_models(self):
        """Save trained models"""
        try:
            # Save scikit-learn models
            if 'success_classifier' in self.models:
                filepath = os.path.join(self.model_dir, 'success_classifier.pkl')
                with open(filepath, 'wb') as f:
                    pickle.dump(self.models['success_classifier'], f)
            
            # Save TensorFlow models
            if 'success_neural_net' in self.models and HAS_TENSORFLOW:
                filepath = os.path.join(self.model_dir, 'success_neural_net.h5')
                self.models['success_neural_net'].save(filepath)
            
            # Save scalers
            if self.scalers:
                scaler_file = os.path.join(self.model_dir, 'scalers.pkl')
                with open(scaler_file, 'wb') as f:
                    pickle.dump(self.scalers, f)
            
            # Save feature columns
            if self.feature_columns:
                features_file = os.path.join(self.model_dir, 'feature_columns.json')
                with open(features_file, 'w') as f:
                    json.dump(self.feature_columns, f)
            
            self.logger.info("Models saved successfully")
        
        except Exception as e:
            self.logger.error(f"Error saving models: {e}")
    
    def _load_training_data(self):
        """Load historical training data"""
        try:
            if os.path.exists(self.training_data_file):
                with open(self.training_data_file, 'r') as f:
                    self.historical_data = json.load(f)
                
                self.logger.info(f"Loaded {len(self.historical_data)} historical data points")
        
        except Exception as e:
            self.logger.error(f"Error loading training data: {e}")
    
    async def _save_training_data(self):
        """Save historical training data"""
        try:
            with open(self.training_data_file, 'w') as f:
                json.dump(self.historical_data[-1000:], f, indent=2)  # Keep last 1000 entries
        
        except Exception as e:
            self.logger.error(f"Error saving training data: {e}")
    
    async def update_outcome(self, token_address: str, outcome: str, performance_data: Dict[str, Any]):
        """Update the actual outcome for a token to improve training"""
        try:
            # Find the prediction data for this token
            for data_point in self.historical_data:
                if data_point.get('token_address') == token_address:
                    data_point['actual_outcome'] = outcome
                    data_point['performance_data'] = performance_data
                    data_point['outcome_timestamp'] = datetime.utcnow().isoformat()
                    break
            
            await self._save_training_data()
            
            # Retrain models if we have enough outcomes
            outcome_count = sum(1 for dp in self.historical_data if 'actual_outcome' in dp)
            if outcome_count > 0 and outcome_count % 50 == 0:  # Retrain every 50 new outcomes
                await self.train_models()
        
        except Exception as e:
            self.logger.error(f"Error updating outcome: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models"""
        return {
            'loaded_models': list(self.models.keys()),
            'feature_count': len(self.feature_columns),
            'training_data_points': len(self.historical_data),
            'has_sklearn': HAS_SKLEARN,
            'has_tensorflow': HAS_TENSORFLOW,
            'has_transformers': HAS_TRANSFORMERS,
            'sentiment_analyzer_available': self.sentiment_analyzer is not None
        }
