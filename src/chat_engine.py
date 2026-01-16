"""Main chat engine orchestrator."""

import logging
import time
from typing import Optional
from src.openai_client import OpenAIClient
from src.pinecone_rag import PineconeRAG
from src.ragmetrics_client import RagMetricsClient
from config.settings import settings

logger = logging.getLogger(__name__)


class ChatEngine:
    """Main chat engine that orchestrates RAG, OpenAI, and RagMetrics."""
    
    def __init__(self, bot_type: str = "constitution"):
        """
        Initialize the chat engine with all required clients.
        
        Args:
            bot_type: Type of bot - "constitution" or "retail" (defaults to "constitution")
        """
        try:
            self.bot_type = bot_type
            self.openai_client = OpenAIClient()
            
            # Set up Pinecone and RagMetrics based on bot type
            if bot_type == "retail":
                # Use retail index and host
                index_name = settings.pinecone_retail_index
                host = settings.pinecone_retail_host
                eval_group_id = settings.ragmetrics_retail_eval_group_id
                logger.info(f"Initializing retail bot with index: {index_name}")
            else:
                # Use constitution index and host
                index_name = settings.pinecone_index_name
                host = settings.pinecone_host
                eval_group_id = settings.ragmetrics_eval_group_id
                logger.info(f"Initializing constitution bot with index: {index_name}")
            
            self.pinecone_rag = PineconeRAG(index_name=index_name, host=host)
            self.ragmetrics_client = RagMetricsClient(eval_group_id=eval_group_id)
            logger.info("Chat engine initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing chat engine: {str(e)}")
            raise
    
    def process_question(self, question: str) -> dict:
        """
        Process a question through the full pipeline:
        1. Retrieve context from Pinecone RAG
        2. Generate answer using OpenAI
        3. Send evaluation to RagMetrics
        
        Args:
            question: The user's question
            
        Returns:
            Dictionary containing:
                - question: The original question
                - answer: The generated answer
                - context: The retrieved context
                - ragmetrics_result: Dictionary with evaluation results (score, reasoning) or None if failed
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
            answer = self.openai_client.generate_answer(question, context, bot_type=self.bot_type)
            logger.info(f"Generated answer ({len(answer)} characters)")
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            # If OpenAI fails, we can't continue
            raise
        
        # Step 3: Send evaluation to RagMetrics
        ragmetrics_result = None
        evaluation_time = None
        try:
            start_time = time.time()
            ragmetrics_result = self.ragmetrics_client.send_evaluation(
                question=question,
                answer=answer,
                context=context,
                ground_truth=""  # Empty string as per requirements
            )
            evaluation_time = time.time() - start_time
        except Exception as e:
            logger.error(f"Error sending to RagMetrics: {str(e)}")
            # Log and continue - don't fail the whole process
        
        if not ragmetrics_result:
            logger.warning("RagMetrics submission failed - continuing anyway")
        
        return {
            "question": question,
            "answer": answer,
            "context": context,
            "ragmetrics_result": ragmetrics_result,
            "evaluation_time": evaluation_time
        }
    
    def regenerate_answer_if_needed(self, question: str, answer: str, context: str, ragmetrics_result: Optional[dict]) -> Optional[str]:
        """
        Check if answer needs regeneration based on any criteria score.
        If any criteria score >= reg_score, regenerate the answer.
        
        Args:
            question: The user's question
            answer: The current answer
            context: The RAG context
            ragmetrics_result: The evaluation result
            
        Returns:
            Regenerated answer if any criteria >= reg_score, None otherwise
        """
        reg_score = settings.reg_score
        should_regenerate, triggering_criteria = self._should_regenerate(ragmetrics_result, reg_score)
        
        logger.info(f"Regeneration check: reg_score={reg_score}, should_regenerate={should_regenerate}")
        if triggering_criteria:
            logger.info(f"Triggering criteria: {triggering_criteria}")
        
        if should_regenerate:
            try:
                logger.info(f"Criteria score(s) >= {reg_score}, regenerating answer...")
                regenerated_answer = self.openai_client.regenerate_answer(
                    question=question,
                    previous_answer=answer,
                    context=context,
                    bot_type=self.bot_type
                )
                return regenerated_answer
            except Exception as e:
                logger.error(f"Error regenerating answer: {str(e)}")
                return None
        
        return None
    
    def _should_regenerate(self, ragmetrics_result: Optional[dict], reg_score: int) -> tuple[bool, list[dict]]:
        """
        Check if regeneration is needed based on any criteria score.
        Returns True if any criteria score >= reg_score.
        
        Args:
            ragmetrics_result: The RagMetrics evaluation result
            reg_score: The regeneration threshold score
            
        Returns:
            Tuple of (should_regenerate: bool, triggering_criteria: list[dict])
            triggering_criteria contains dicts with 'name' and 'score' keys
        """
        if not ragmetrics_result:
            logger.debug("No ragmetrics_result provided")
            return False, []
        
        # Get criteria list
        criteria_list = None
        if 'criteria' in ragmetrics_result and isinstance(ragmetrics_result['criteria'], list):
            criteria_list = ragmetrics_result['criteria']
            logger.debug(f"Found criteria list in ragmetrics_result['criteria']: {len(criteria_list)} items")
        elif 'raw_response' in ragmetrics_result and isinstance(ragmetrics_result['raw_response'], dict):
            raw = ragmetrics_result['raw_response']
            if 'results' in raw and isinstance(raw['results'], list):
                criteria_list = raw['results']
                logger.debug(f"Found criteria list in raw_response['results']: {len(criteria_list)} items")
            elif 'criteria' in raw and isinstance(raw['criteria'], list):
                criteria_list = raw['criteria']
                logger.debug(f"Found criteria list in raw_response['criteria']: {len(criteria_list)} items")
        
        triggering_criteria = []
        
        if criteria_list:
            for criterion in criteria_list:
                if isinstance(criterion, dict):
                    criterion_name = criterion.get('criteria', criterion.get('name', ''))
                    score = criterion.get('score')
                    
                    # Convert score to int if possible
                    score_int = None
                    if isinstance(score, (int, float)):
                        score_int = int(score)
                    elif isinstance(score, str):
                        try:
                            score_int = int(float(score))
                        except (ValueError, TypeError):
                            logger.debug(f"Could not convert score to int: {score} for criterion {criterion_name}")
                            continue
                    else:
                        logger.debug(f"Score is not numeric: {score} (type: {type(score)}) for criterion {criterion_name}")
                        continue
                    
                    logger.debug(f"Checking criterion: {criterion_name}, score: {score_int}, reg_score: {reg_score}")
                    
                    if score_int is not None and score_int >= reg_score:
                        triggering_criteria.append({
                            'name': criterion_name,
                            'score': score_int
                        })
                        logger.info(f"Criterion '{criterion_name}' score {score_int} >= {reg_score}, triggering regeneration")
        else:
            logger.debug("No criteria list found in ragmetrics_result")
        
        return len(triggering_criteria) > 0, triggering_criteria
    
    def _get_hallucination_score(self, ragmetrics_result: Optional[dict]) -> Optional[int]:
        """
        Extract hallucination score from RagMetrics result.
        (Kept for backward compatibility/debugging)
        
        Args:
            ragmetrics_result: The RagMetrics evaluation result
            
        Returns:
            Hallucination score as integer, or None if not found
        """
        if not ragmetrics_result:
            return None
        
        # Get criteria list
        criteria_list = None
        if 'criteria' in ragmetrics_result and isinstance(ragmetrics_result['criteria'], list):
            criteria_list = ragmetrics_result['criteria']
        elif 'raw_response' in ragmetrics_result and isinstance(ragmetrics_result['raw_response'], dict):
            raw = ragmetrics_result['raw_response']
            if 'results' in raw and isinstance(raw['results'], list):
                criteria_list = raw['results']
            elif 'criteria' in raw and isinstance(raw['criteria'], list):
                criteria_list = raw['criteria']
        
        if criteria_list:
            for criterion in criteria_list:
                if isinstance(criterion, dict):
                    criterion_name = criterion.get('criteria', criterion.get('name', ''))
                    if criterion_name.lower() == 'hallucination':
                        score = criterion.get('score')
                        if isinstance(score, (int, float)):
                            return int(score)
                        elif isinstance(score, str):
                            try:
                                return int(float(score))
                            except (ValueError, TypeError):
                                pass
        
        return None


