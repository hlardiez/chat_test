"""Prompt templates for the chat engine."""


def get_chat_prompt(question: str, context: str = "") -> tuple[str, str]:
    """
    Generate system and user prompts for OpenAI chat completion.
    
    Args:
        question: The user's question
        context: The context retrieved from RAG system (can be empty)
        
    Returns:
        Tuple of (system_message, user_message) for OpenAI chat completion
    """
    # System prompt - instructions for the assistant
    system_message = (
        """
        You are a helpful assistant that answers questions based on the provided context. 
        Use the context information to answer the question accurately. 
        If the context doesn't contain enough information to answer the question, 
        provide the best answer you can based on your general knowledge.
        If you get conversational commments answer in the same way.
        """
    )
    
    # User prompt - includes context and question
    if context:
        user_message = (
            f"Context:\n{context}\n\n"
            f"Question: {question}"
        )
    else:
        user_message = question
    
    return system_message, user_message



def get_regenerate_prompt(question: str, previous_answer: str, context: str = "") -> tuple[str, str]:
    """
    Generate system and user prompts for regenerating an answer after detecting hallucinations.
    
    Args:
        question: The user's question
        previous_answer: The previous answer that had hallucinations
        context: The context retrieved from RAG system (can be empty)
        
    Returns:
        Tuple of (system_message, user_message) for OpenAI chat completion for regenerating the answer
    """
    # System prompt - instructions for the assistant
    system_message = (
        "You are a helpful assistant that answers questions based ONLY on the provided context. "
        "The previous answer contained hallucinations or incorrect information. "
        "Please provide a new answer that strictly adheres to the context provided. "
        "If the context doesn't contain enough information to answer the question, "
        "you must clearly state that you don't have enough information in the context. "
        "Do not make up information or use knowledge outside the provided context."
    )
    
    # User prompt - includes context, previous answer, and question
    if context:
        user_message = (
            f"Context:\n{context}\n\n"
            f"Previous answer (had hallucinations): {previous_answer}\n\n"
            f"Question: {question}\n\n"
            f"Please provide a corrected answer based strictly on the context above."
        )
    else:
        user_message = (
            f"Previous answer (had hallucinations): {previous_answer}\n\n"
            f"Question: {question}\n\n"
            f"Please provide a corrected answer. If you don't have enough information, say so."
        )
    
    return system_message, user_message





