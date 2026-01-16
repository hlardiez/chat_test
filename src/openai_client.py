"""OpenAI API client for chat completion."""

import logging
from typing import Optional
from openai import OpenAI
from config.settings import settings
from src.prompt import get_chat_prompt, get_regenerate_prompt

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client for interacting with OpenAI API."""
    
    def __init__(self):
        """Initialize OpenAI client with API key from settings."""
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
    
    def generate_answer(
        self, 
        question: str, 
        context: Optional[str] = None,
        bot_type: str = "constitution"
    ) -> str:
        """
        Generate an answer to a question using OpenAI chat completion.
        
        Args:
            question: The user's question
            context: Optional context from RAG system to include in the prompt
            bot_type: Type of bot - "constitution" or "retail" (defaults to "constitution")
            
        Returns:
            The generated answer string
        """
        try:
            # Get prompts from prompt.py
            context_str = context if context else ""
            system_content, user_content = get_chat_prompt(
                question=question,
                context=context_str,
                bot_type=bot_type
            )
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content.strip()
            logger.info(f"Generated answer using model: {self.model}")
            return answer
            
        except Exception as e:
            logger.error(f"Error generating answer from OpenAI: {str(e)}")
            raise
    
    def regenerate_answer(
        self,
        question: str,
        previous_answer: str,
        context: Optional[str] = None,
        bot_type: str = "constitution"
    ) -> str:
        """
        Regenerate an answer after detecting hallucinations.
        
        Args:
            question: The user's question
            previous_answer: The previous answer that had hallucinations
            context: Optional context from RAG system to include in the prompt
            bot_type: Type of bot - "constitution" or "retail" (defaults to "constitution")
            
        Returns:
            The regenerated answer string
        """
        try:
            # Get regenerate prompts from prompt.py
            context_str = context if context else ""
            system_content, user_content = get_regenerate_prompt(
                question=question,
                previous_answer=previous_answer,
                context=context_str,
                bot_type=bot_type
            )
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content.strip()
            logger.info(f"Regenerated answer using model: {self.model}")
            return answer
            
        except Exception as e:
            logger.error(f"Error regenerating answer from OpenAI: {str(e)}")
            raise

