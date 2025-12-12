"""Streamlit web UI for Chat Test Project."""

import streamlit as st
import logging
import time
from src.utils import setup_logging
from src.chat_engine import ChatEngine
from config.settings import Settings, get_settings

# Set logging to WARNING level
setup_logging(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Initialize session state
if 'chat_engine' not in st.session_state:
    st.session_state.chat_engine = None
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'current_question' not in st.session_state:
    st.session_state.current_question = None
if 'is_processing' not in st.session_state:
    st.session_state.is_processing = False
if 'pending_question' not in st.session_state:
    st.session_state.pending_question = None
if 'processing_started' not in st.session_state:
    st.session_state.processing_started = False


def get_criteria_info(ragmetrics_result):
    """Extract criteria name and score from RagMetrics result.
    
    Returns:
        Tuple of (criteria_name, score) or (None, None) if not found
    """
    if not ragmetrics_result:
        return None, None
    
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
    
    if criteria_list and len(criteria_list) > 0:
        # Get the first criterion
        criterion = criteria_list[0]
        if isinstance(criterion, dict):
            criterion_name = criterion.get('criteria', criterion.get('name', criterion.get('criterion_name', 'Unknown')))
            score = criterion.get('score')
            
            # Convert score to int if possible
            score_int = None
            if isinstance(score, (int, float)):
                score_int = int(score)
            elif isinstance(score, str):
                try:
                    score_int = int(float(score))
                except (ValueError, TypeError):
                    pass
            
            if criterion_name and score_int is not None:
                return criterion_name, score_int
    
    return None, None


def has_error(ragmetrics_result, reg_score):
    """Check if there's an error (any criteria score >= reg_score)."""
    if not ragmetrics_result:
        return False
    
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
                score = criterion.get('score')
                score_int = None
                if isinstance(score, (int, float)):
                    score_int = int(score)
                elif isinstance(score, str):
                    try:
                        score_int = int(float(score))
                    except (ValueError, TypeError):
                        continue
                
                if score_int is not None and score_int >= reg_score:
                    return True
    
    return False


def truncate_to_words(text, max_words=80):
    """Truncate text to a maximum number of words, adding '...' if truncated."""
    if not text:
        return ""
    
    words = text.split()
    if len(words) <= max_words:
        return text
    
    truncated = " ".join(words[:max_words])
    return truncated + "..."


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="RagMetrics - Self Correcting Chatbot",
        page_icon="💬",
        layout="wide"
    )
    
    # Add custom CSS for scrollable conversation panel
    st.markdown("""
        <style>
        /* Prevent page-level scrolling */
        .main .block-container {
            overflow: hidden !important;
            max-width: 100%;
        }
        
        /* Make main content area scrollable */
        .main .block-container > div {
            height: calc(100vh - 150px);
            overflow-y: auto;
            overflow-x: hidden;
            scroll-behavior: smooth;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("RagMetrics - Self Correcting Chatbot")
    
    # Get settings instance (lazy initialization - only when needed)
    try:
        settings = get_settings()
    except Exception as e:
        st.error(f"Error loading configuration: {str(e)}")
        st.error("Please ensure all required environment variables are set in Streamlit Cloud Secrets.")
        st.stop()
    
    # Initialize chat engine
    if st.session_state.chat_engine is None:
        with st.spinner("Initializing chat engine..."):
            try:
                st.session_state.chat_engine = ChatEngine()
            except Exception as e:
                st.error(f"Error initializing chat engine: {str(e)}")
                st.stop()
    
    # Single column layout for conversation
    st.subheader("Ask questions about the US Constitution.")
    
    # Display all conversation history (scrolling up)
    for entry in st.session_state.conversation_history:
        # User message
        with st.chat_message("user"):
            st.write(entry['question'])
        
        # Bot message - show regenerated answer if available, otherwise original answer
        with st.chat_message("assistant"):
            if entry.get('regenerated_answer'):
                # Show regenerated answer if error occurred
                st.write(entry['regenerated_answer'])
            else:
                # Show original answer
                st.write(entry['answer'])
        
        # Show evaluation results inline with this conversation entry
        ragmetrics_result = entry.get('ragmetrics_result')
        if ragmetrics_result:
            criteria_name, criteria_score = get_criteria_info(ragmetrics_result)
            
            if criteria_name and criteria_score is not None:
                # Check if score >= REG_SCORE to show in red with "Answer Regenerated"
                if criteria_score >= settings.reg_score:
                    st.markdown(
                        f'<div style="color: red; font-size: 1.2em; font-weight: bold; margin-top: 10px; margin-bottom: 10px;">{criteria_name}: {criteria_score} | Answer Regenerated</div>',
                        unsafe_allow_html=True
                    )
                else:
                    # Show criteria name and score on same line with same font size
                    st.markdown(
                        f'<div style="font-size: 1.2em; margin-top: 10px; margin-bottom: 10px;">{criteria_name}: {criteria_score}</div>',
                        unsafe_allow_html=True
                    )
                
                # If error/regeneration occurred, show original question and answer
                if entry.get('has_error', False):
                    st.write("**Original Question:**")
                    st.write(entry['question'])
                    st.write("**Original Answer:**")
                    truncated_answer = truncate_to_words(entry['answer'], max_words=80)
                    st.write(truncated_answer)
    
    # Show current question if processing
    if st.session_state.is_processing and st.session_state.current_question:
        with st.chat_message("user"):
            st.write(st.session_state.current_question)
        with st.chat_message("assistant"):
            st.write("Processing...")
    
    # Process pending question if any (show question first)
    if st.session_state.pending_question and not st.session_state.is_processing:
        # Set processing state and show question immediately
        st.session_state.is_processing = True
        st.session_state.current_question = st.session_state.pending_question
        st.session_state.processing_started = False
        st.session_state.pending_question = None
        
        # Rerun to show the question before processing
        st.rerun()
    
    # Chat input - only show when not processing
    if not st.session_state.is_processing:
        user_question = st.chat_input("Ask a question...")
        
        if user_question:
            # Set pending question and rerun immediately to show it
            st.session_state.pending_question = user_question
            st.rerun()
    
    # Process question if we're in processing state but haven't started yet
    if st.session_state.is_processing and st.session_state.current_question and not st.session_state.processing_started:
            # Mark as started to prevent reprocessing
            st.session_state.processing_started = True
            
            # Process question
            start_time = time.time()
            result = st.session_state.chat_engine.process_question(st.session_state.current_question)
            
            # Get evaluation result
            ragmetrics_result = result.get('ragmetrics_result')
            
            # Check if regeneration is needed
            regenerated_answer = st.session_state.chat_engine.regenerate_answer_if_needed(
                question=result['question'],
                answer=result['answer'],
                context=result['context'],
                ragmetrics_result=ragmetrics_result
            )
            
            # Determine if there's an error
            has_error_flag = has_error(ragmetrics_result, settings.reg_score)
            
            # Calculate turnaround time
            turnaround_time_ms = int((time.time() - start_time) * 1000)
            
            # Store in conversation history
            conversation_entry = {
                'question': st.session_state.current_question,
                'answer': result['answer'],
                'regenerated_answer': regenerated_answer,
                'has_error': has_error_flag,
                'ragmetrics_result': ragmetrics_result,
                'turnaround_time_ms': turnaround_time_ms
            }
            st.session_state.conversation_history.append(conversation_entry)
            
            # Reset processing state
            st.session_state.is_processing = False
            st.session_state.current_question = None
            st.session_state.processing_started = False
            
            # Rerun to update the display
            st.rerun()


if __name__ == "__main__":
    main()

