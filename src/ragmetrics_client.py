"""RagMetrics API client for sending evaluation data."""

import logging
import requests
from typing import Optional, Dict, Any
from config.settings import settings

logger = logging.getLogger(__name__)


class RagMetricsClient:
    """Client for sending evaluation data to RagMetrics API."""
    
    def __init__(self, eval_group_id: str = None):
        """
        Initialize RagMetrics client with API key and base URL.
        
        Args:
            eval_group_id: Optional eval group ID override (defaults to settings.ragmetrics_eval_group_id)
        """
        # Handle case where URL includes the full path
        url = settings.ragmetrics_base_url.rstrip('/')
        # Remove /v2/single-evaluation if present
        if '/v2/single-evaluation' in url:
            self.base_url = url.split('/v2/single-evaluation')[0].rstrip('/')
        else:
            self.base_url = url
        self.api_key = settings.ragmetrics_api_key
        self.eval_group_id = eval_group_id or settings.ragmetrics_eval_group_id
        self.eval_type = settings.ragmetrics_type
        self.conversation_id = settings.ragmetrics_conversation_id
        self.endpoint = f"{self.base_url}/v2/single-evaluation/"
    
    def send_evaluation(
        self,
        question: str,
        answer: str,
        context: str,
        ground_truth: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Send evaluation data to RagMetrics API.
        
        Args:
            question: The user's question
            answer: The generated answer from the chatbot
            context: The context retrieved from RAG system
            ground_truth: The ground truth answer (default: empty string)
            
        Returns:
            Dictionary containing evaluation results with 'score' and 'reasoning' if successful,
            None otherwise
        """
        payload = {
            "question": question,
            "ground_truth": ground_truth,
            "answer": answer,
            "eval_group_id": self.eval_group_id,
            "context": context,
            "type": self.eval_type,
            "conversation_id": self.conversation_id
        }
        
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            # Accept any 2xx status code as success (200, 201, 202, etc.)
            if 200 <= response.status_code < 300:
                logger.info(f"Successfully sent evaluation to RagMetrics (status {response.status_code})")
                
                # Parse response to extract score and reasoning
                try:
                    response_data = response.json()
                    evaluation_result = {
                        "success": True,
                        "status_code": response.status_code
                    }
                    
                    # Extract score and reasoning from response
                    # These field names may vary - adjust based on actual API response
                    if "score" in response_data:
                        evaluation_result["score"] = response_data["score"]
                    elif "evaluation_score" in response_data:
                        evaluation_result["score"] = response_data["evaluation_score"]
                    
                    if "reasoning" in response_data:
                        evaluation_result["reasoning"] = response_data["reasoning"]
                    elif "evaluation_reasoning" in response_data:
                        evaluation_result["reasoning"] = response_data["evaluation_reasoning"]
                    elif "explanation" in response_data:
                        evaluation_result["reasoning"] = response_data["explanation"]
                    
                    # Extract criteria if present (for multiple criteria evaluations)
                    if "results" in response_data and isinstance(response_data["results"], list):
                        # RagMetrics returns criteria in a 'results' array
                        evaluation_result["criteria"] = response_data["results"]
                    elif "criteria" in response_data:
                        evaluation_result["criteria"] = response_data["criteria"]
                    
                    # Include full response for debugging
                    evaluation_result["raw_response"] = response_data
                    
                    return evaluation_result
                    
                except (ValueError, KeyError) as e:
                    # If JSON parsing fails or fields are missing, still return success
                    logger.warning(f"Could not parse evaluation response: {str(e)}")
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "raw_response": response.text
                    }
            else:
                logger.warning(
                    f"RagMetrics API returned status {response.status_code}: "
                    f"{response.text}"
                )
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending evaluation to RagMetrics: {str(e)}")
            return None

