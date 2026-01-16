"""Fast chat engine orchestrator using completion API."""

import logging
import time
from typing import Optional
from src.openai_client import OpenAIClient
from src.pinecone_rag import PineconeRAG
from fast_evaluation_client import FastEvaluationClient

logger = logging.getLogger(__name__)


class FastChatEngine:
    """Fast chat engine that orchestrates RAG, OpenAI, and completion API evaluation."""
    
    def __init__(self, base_url: str, criteria_prompt: str):
        """
        Initialize the fast chat engine.
        
        Args:
            base_url: Base URL for the completion API
            criteria_prompt: The criteria definition to use for evaluation
        """
        try:
            self.openai_client = OpenAIClient()
            self.pinecone_rag = PineconeRAG()
            self.evaluation_client = FastEvaluationClient(base_url)
            self.criteria_prompt = criteria_prompt
            logger.info("Fast chat engine initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing fast chat engine: {str(e)}")
            raise
    
    def process_question(self, question: str) -> dict:
        """
        Process a question through the full pipeline:
        1. Retrieve context from Pinecone RAG
        2. Generate answer using OpenAI
        3. Send evaluation to completion API
        
        Args:
            question: The user's question
            
        Returns:
            Dictionary containing:
                - question: The original question
                - answer: The generated answer
                - context: The retrieved context
                - evaluation_result: Dictionary with evaluation score or None if failed
                - evaluation_time: Time taken for evaluation in seconds
        """
        logger.info(f"Processing question: {question}")
        
        # Step 1: Retrieve context from Pinecone RAG
        try:
            context, raw_results = self.pinecone_rag.retrieve_context(question)
            logger.info(f"Retrieved context ({len(context)} characters)")
        except Exception as e:
            logger.error(f"Error retrieving RAG context: {str(e)}")
            context = ""
            raw_results = []
            # Continue with empty context
        
        # Step 2: Generate answer using OpenAI
        try:
            answer = self.openai_client.generate_answer(question, context)
            logger.info(f"Generated answer ({len(answer)} characters)")
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            # If OpenAI fails, we can't continue
            raise
        
        # Step 3: Send evaluation to completion API
        evaluation_result = None
        evaluation_time = None
        try:
            start_time = time.time()
            evaluation_result = self.evaluation_client.evaluate_answer(
                question=question,
                answer=answer,
                context=context,
                ground_truth="",  # Empty string as per requirements
                criteria_prompt=self.criteria_prompt
            )
            evaluation_time = time.time() - start_time
        except Exception as e:
            logger.error(f"Error sending to completion API: {str(e)}")
            # Log and continue - don't fail the whole process
        
        if not evaluation_result:
            logger.warning("Completion API evaluation failed - continuing anyway")
        
        return {
            "question": question,
            "answer": answer,
            "context": context,
            "evaluation_result": evaluation_result,
            "evaluation_time": evaluation_time
        }
    
    def regenerate_answer_if_needed(
        self, 
        question: str, 
        answer: str, 
        context: str, 
        evaluation_result: Optional[dict]
    ) -> Optional[str]:
        """
        Check if answer needs regeneration based on evaluation score.
        If score >= 3, regenerate the answer.
        
        Args:
            question: The user's question
            answer: The current answer
            context: The RAG context
            evaluation_result: The evaluation result with score
            
        Returns:
            Regenerated answer if score >= 3, None otherwise
        """
        if not evaluation_result:
            logger.debug("No evaluation_result provided")
            return None
        
        score = evaluation_result.get('score')
        if score is None:
            logger.debug("No score in evaluation_result")
            return None
        
        # Convert to int if needed
        try:
            score_int = int(score)
        except (ValueError, TypeError):
            logger.debug(f"Could not convert score to int: {score}")
            return None
        
        logger.info(f"Regeneration check: score={score_int}, threshold=3")
        
        # If score >= 3, regenerate
        if score_int >= 3:
            try:
                logger.info(f"Score {score_int} >= 3, regenerating answer...")
                regenerated_answer = self.openai_client.regenerate_answer(
                    question=question,
                    previous_answer=answer,
                    context=context
                )
                return regenerated_answer
            except Exception as e:
                logger.error(f"Error regenerating answer: {str(e)}")
                return None
        
        return None



