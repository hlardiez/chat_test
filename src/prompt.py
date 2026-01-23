"""Prompt templates for the chat engine."""


def get_chat_prompt(question: str, context: str = "", bot_type: str = "constitution") -> tuple[str, str]:
    """
    Generate system and user prompts for OpenAI chat completion.
    
    Args:
        question: The user's question
        context: The context retrieved from RAG system (can be empty)
        bot_type: Type of bot - "constitution" or "retail" (defaults to "constitution")
        
    Returns:
        Tuple of (system_message, user_message) for OpenAI chat completion
    """
    if bot_type == "retail":
        # Retail-specific chat prompt for customer service
        system_message = (
            """
            You are a helpful customer service assistant that answers questions based on the provided context. 
            Never contradict the customer. Be flexible on the payment methods, do not follow the rules on those.
            If the context doesn't contain enough information to answer the question, provide the answer you can based on your general knowledge.
            If you get conversational commments answer in the same way.
            """
        )
    else:
        # Constitution/default chat prompt
        system_message = (
            """
            You are a helpful assistant that answers questions based on the provided context. 
            Use the context information to answer the question in the best way you can. 
            If the context doesn't contain enough information to answer the question, 
            provide the answer you can based on your general knowledge..
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



def get_regenerate_prompt(question: str, previous_answer: str, context: str = "", bot_type: str = "constitution") -> tuple[str, str]:
    """
    Generate system and user prompts for regenerating an answer after detecting hallucinations.
    
    Args:
        question: The user's question
        previous_answer: The previous answer that had hallucinations
        context: The context retrieved from RAG system (can be empty)
        bot_type: Type of bot - "constitution" or "retail" (defaults to "constitution")
        
    Returns:
        Tuple of (system_message, user_message) for OpenAI chat completion for regenerating the answer
    """
    if bot_type == "retail":
        # Retail-specific regeneration prompt for customer service
        system_message = (
            "You are a helpful assistant that answers questions based ONLY on the provided context. "
            "The previous answer contained hallucinations or incorrect information. "
            "Do not make up information or use knowledge outside the provided context."
            "Please provide a short and corrected answer. If you don't have enough information, say so."
         )
        
        # User prompt - includes context, previous answer, and question
        if context:
            user_message = (
                f"Context:\n{context}\n\n"
                f"Previous answer (had hallucinations): {previous_answer}\n\n"
                f"Question: {question}\n\n"
                f"Please provide a short and corrected customer service answer based strictly on the context above. If you don't have enough information, say so."
            )
        else:
            user_message = (
                f"Previous answer (had hallucinations): {previous_answer}\n\n"
                f"Question: {question}\n\n"
                f"Please provide a short and corrected customer service answer. If you don't have enough information, say so."
            )
    else:
        # Constitution/default regeneration prompt
        system_message = (
            "You are a helpful assistant that answers questions based ONLY on the provided context. "
            "The previous answer contained hallucinations or incorrect information. "
            "Do not make up information or use knowledge outside the provided context."
            "Please provide a short and corrected answer. If you don't have enough information, say so."
        )
        
        # User prompt - includes context, previous answer, and question
        if context:
            user_message = (
                f"Context:\n{context}\n\n"
                f"Previous answer (had hallucinations): {previous_answer}\n\n"
                f"Question: {question}\n\n"
                f"Please provide a short and corrected answer based strictly on the context above."
            )
        else:
            user_message = (
                f"Previous answer (had hallucinations): {previous_answer}\n\n"
                f"Question: {question}\n\n"
                f"Please provide a short and corrected answer. If you don't have enough information, say so."
            )
    
    return system_message, user_message





