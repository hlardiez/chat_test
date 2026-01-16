"""Fast evaluation client for completion API."""

import logging
import json
import requests
from typing import Optional, Dict
from prompt import PROMPT_RATE_ANSWER_SCORE_ONLY, JSON_SCORE_GRAMMAR_SCORE_ONLY, MAX_TOKENS, TEMPERATURE, TOP_P, TOP_K, REPEAT_PENALTY, STOP_SEQUENCE

logger = logging.getLogger(__name__)


class FastEvaluationClient:
    """Client for evaluating answers using the completion API."""
    
    def __init__(self, base_url: str):
        """
        Initialize the fast evaluation client.
        
        Args:
            base_url: Base URL for the completion API (e.g., http://10.10.10.10:8080)
        """
        self.base_url = base_url.rstrip('/')
        self.completion_url = f"{self.base_url}/completion"
        logger.info(f"FastEvaluationClient initialized with base_url: {self.base_url}")
        logger.info(f"Completion URL: {self.completion_url}")
    
    def evaluate_answer(
        self,
        question: str,
        answer: str,
        context: str,
        ground_truth: str,
        criteria_prompt: str
    ) -> Optional[Dict]:
        """
        Evaluate an answer using the completion API.
        
        Args:
            question: The user's question
            answer: The candidate answer to evaluate
            context: The context retrieved from RAG
            ground_truth: The ground truth answer (empty string in this case)
            criteria_prompt: The criteria definition to use
            
        Returns:
            Dictionary with 'score' (int) or None if evaluation failed
        """
        try:
            # Generate prompt using prompt.py
            prompt = PROMPT_RATE_ANSWER_SCORE_ONLY.format(
                criteria_prompt=criteria_prompt,
                question=question,
                candidate_answer=answer,
                ground_truth=ground_truth,
                context=context
            )
            
            # Prepare API request payload
            payload = {
                "prompt": prompt,
                "n_predict": MAX_TOKENS,
                "temperature": TEMPERATURE,
                "top_p": TOP_P,
                "top_k": TOP_K,
                "repeat_penalty": REPEAT_PENALTY,
                "max_tokens": MAX_TOKENS,
                "grammar": JSON_SCORE_GRAMMAR_SCORE_ONLY,
                "stop": STOP_SEQUENCE
            }
            
            logger.info(f"Sending evaluation request to {self.completion_url}")
            logger.debug(f"Payload keys: {list(payload.keys())}")
            
            # Make API request
            response = requests.post(
                self.completion_url,
                json=payload,
                timeout=60  # 60 second timeout
            )
            response.raise_for_status()
            
            # Parse response
            response_data = response.json()
            logger.debug(f"API response keys: {list(response_data.keys())}")
            
            # Extract content from response
            content = response_data.get('content', '')
            if not content:
                logger.error("No 'content' field in API response")
                return None
            
            # Parse the JSON string from content
            try:
                # The content is a JSON string, parse it
                score_data = json.loads(content)
                score = score_data.get('score')
                
                if score is None:
                    logger.error("No 'score' field in parsed JSON")
                    return None
                
                # Convert to int
                score_int = int(score)
                
                logger.info(f"Evaluation successful: score={score_int}")
                return {
                    'score': score_int
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from content: {content}")
                logger.error(f"JSON decode error: {str(e)}")
                return None
            except (ValueError, TypeError) as e:
                logger.error(f"Failed to convert score to int: {str(e)}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making API request: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in evaluation: {str(e)}")
            return None



