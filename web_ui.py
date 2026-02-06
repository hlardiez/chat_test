"""Streamlit web UI for Chat Test Project."""

import streamlit as st
import logging
import requests
from src.utils import setup_logging
from src.chat_engine import ChatEngine
from config.settings import Settings, get_settings
from fast_utils import append_log_row, log_timestamp_utc

# Set logging to WARNING level
setup_logging(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Initialize session state
if 'bot_type' not in st.session_state:
    st.session_state.bot_type = None
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
if 'judge_base_url' not in st.session_state:
    st.session_state.judge_base_url = None


def get_criteria_info(ragmetrics_result):
    """Extract criteria name and score from RagMetrics or Fast evaluation result.
    
    Handles both RagMetrics format (criteria list) and Fast format ({score: X}).
    Returns:
        Tuple of (criteria_name, score) or (None, None) if not found
    """
    if not ragmetrics_result:
        return None, None
    
    # Fast evaluation format: simple {score: X}
    if 'score' in ragmetrics_result and 'criteria' not in ragmetrics_result and 'raw_response' not in ragmetrics_result:
        score = ragmetrics_result.get('score')
        score_int = None
        if isinstance(score, (int, float)):
            score_int = int(score)
        elif isinstance(score, str):
            try:
                score_int = int(float(score))
            except (ValueError, TypeError):
                pass
        if score_int is not None:
            return "Contextual_Hallucination", score_int
        return None, None
    
    # Get criteria list (RagMetrics format)
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
    
    # Fast evaluation format: simple {score: X}
    if 'score' in ragmetrics_result and 'criteria' not in ragmetrics_result and 'raw_response' not in ragmetrics_result:
        score = ragmetrics_result.get('score')
        score_int = None
        if isinstance(score, (int, float)):
            score_int = int(score)
        elif isinstance(score, str):
            try:
                score_int = int(float(score))
            except (ValueError, TypeError):
                return False
        return score_int is not None and score_int >= reg_score
    
    # Get criteria list (RagMetrics format)
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


def check_llama_server(base_url: str, timeout: int = 5) -> tuple[bool, str]:
    """
    Check if the Llama server is up by calling GET {base_url}/api/tags.
    Returns (True, None) if server is up, (False, error_message) otherwise.
    """
    url = base_url.rstrip("/") + "/api/tags"
    try:
        r = requests.get(url, timeout=timeout)
        if r.ok:
            return True, None
        return False, f"Server returned status {r.status_code}"
    except requests.exceptions.ConnectionError as e:
        return False, "Cannot connect to server. Is it running?"
    except requests.exceptions.Timeout:
        return False, "Connection timed out."
    except Exception as e:
        return False, str(e)


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
    
    # Get settings instance (lazy initialization - only when needed)
    try:
        settings = get_settings()
    except Exception as e:
        st.error(f"Error loading configuration: {str(e)}")
        st.error("Please ensure all required environment variables are set in Streamlit Cloud Secrets.")
        st.stop()
    
    # Bot selection - show if not selected yet
    if st.session_state.bot_type is None:
        st.title("RagMetrics - Self Correcting Chatbot")
        st.subheader("Select a bot to get started")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🇺🇸 Constitution Bot", use_container_width=True, type="primary"):
                st.session_state.bot_type = "constitution"
                st.session_state.chat_engine = None
                st.session_state.conversation_history = []
                st.session_state.judge_base_url = None
                st.rerun()
        
        with col2:
            if st.button("🛒 Retail Bot", use_container_width=True, type="primary"):
                st.session_state.bot_type = "retail"
                st.session_state.chat_engine = None
                st.session_state.conversation_history = []
                st.session_state.judge_base_url = None
                st.rerun()
        
        with col3:
            if st.button("⚡ Fast Constitution", use_container_width=True, type="primary"):
                st.session_state.bot_type = "fast_constitution"
                st.session_state.chat_engine = None
                st.session_state.conversation_history = []
                st.session_state.judge_base_url = None
                st.rerun()
        
        st.stop()
    
    # Fast Constitution: require Judge API URL before creating engine
    if st.session_state.bot_type == "fast_constitution" and st.session_state.chat_engine is None:
        st.title("Fast Constitution")
        st.subheader("Enter the Judge API address and port")
        st.caption("Example: http://10.10.10.10:8080")
        
        judge_url = st.text_input(
            "Judge API base URL",
            value=st.session_state.judge_base_url or "http://",
            placeholder="http://host:port",
            key="fast_judge_url"
        )
        
        if st.button("Connect and Start"):
            url = (judge_url or "").strip()
            if not url or url == "http://":
                st.error("Please enter a valid Judge API URL (e.g. http://10.10.10.10:8080)")
            else:
                with st.spinner("Checking if server is running..."):
                    server_ok, server_error = check_llama_server(url)
                
                if not server_ok:
                    st.error(f"**Judge server is not available.** {server_error}")
                    st.info("You can re-enter the URL above and try again, or go back to the main screen.")
                    if st.button("← Back to main screen"):
                        st.session_state.bot_type = None
                        st.session_state.judge_base_url = None
                        st.rerun()
                else:
                    try:
                        from fast_utils import get_criteria_from_csv
                        from fast_chat_engine import FastChatEngine
                        criteria_prompt = get_criteria_from_csv("criteria.csv", "Contextual_Hallucination")
                        if not criteria_prompt:
                            st.error("Failed to load criteria from criteria.csv (Contextual_Hallucination).")
                        else:
                            with st.spinner("Initializing chat engine..."):
                                st.session_state.judge_base_url = url
                                st.session_state.chat_engine = FastChatEngine(
                                    base_url=url,
                                    criteria_prompt=criteria_prompt
                                )
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error initializing Fast Constitution: {str(e)}")
        else:
            # Show "Back to main screen" even when not connecting, so user can go back
            if st.button("← Back to main screen", key="fast_back_main"):
                st.session_state.bot_type = None
                st.session_state.judge_base_url = None
                st.rerun()
        st.stop()
    
    # Set title and topic based on bot type
    if st.session_state.bot_type == "retail":
        page_title = "Customer Service"
        topic = "customer service"
    elif st.session_state.bot_type == "fast_constitution":
        page_title = "Fast Constitution"
        topic = settings.topic
    else:
        page_title = "RagMetrics - Self Correcting Chatbot"
        topic = settings.topic
    
    # Title with bot switcher
    col_title, col_switch = st.columns([4, 1])
    with col_title:
        st.title(page_title)
    with col_switch:
        if st.button("🔄 Switch Bot", use_container_width=True):
            st.session_state.bot_type = None
            st.session_state.chat_engine = None
            st.session_state.conversation_history = []
            st.session_state.judge_base_url = None
            st.rerun()
    
    # Initialize chat engine (Constitution and Retail use ChatEngine; Fast Constitution is created in URL step)
    if st.session_state.chat_engine is None:
        with st.spinner("Initializing chat engine..."):
            try:
                st.session_state.chat_engine = ChatEngine(bot_type=st.session_state.bot_type)
            except Exception as e:
                st.error(f"Error initializing chat engine: {str(e)}")
                st.stop()
    
    # Single column layout for conversation
    st.subheader(f"Ask questions about {topic}")
    
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
            result = st.session_state.chat_engine.process_question(st.session_state.current_question)
            
            # Fast Constitution uses evaluation_result; others use ragmetrics_result
            if st.session_state.bot_type == "fast_constitution":
                evaluation_result = result.get("evaluation_result")
                ragmetrics_result = evaluation_result  # store for display (get_criteria_info handles {score})
                regenerated_answer = st.session_state.chat_engine.regenerate_answer_if_needed(
                    question=result["question"],
                    answer=result["answer"],
                    context=result["context"],
                    evaluation_result=evaluation_result
                )
            else:
                ragmetrics_result = result.get("ragmetrics_result")
                regenerated_answer = st.session_state.chat_engine.regenerate_answer_if_needed(
                    question=result["question"],
                    answer=result["answer"],
                    context=result["context"],
                    ragmetrics_result=ragmetrics_result
                )
            
            # Determine if there's an error
            has_error_flag = has_error(ragmetrics_result, settings.reg_score)
            
            # Store in conversation history
            conversation_entry = {
                "question": st.session_state.current_question,
                "answer": result["answer"],
                "regenerated_answer": regenerated_answer,
                "has_error": has_error_flag,
                "ragmetrics_result": ragmetrics_result,
            }
            st.session_state.conversation_history.append(conversation_entry)
            
            # Log to logs_fast.csv (same format as fast_main.py)
            criteria_name, criteria_score = get_criteria_info(ragmetrics_result)
            bot_name = (
                "fast-constitution" if st.session_state.bot_type == "fast_constitution"
                else "retail" if st.session_state.bot_type == "retail"
                else "constitution"
            )
            answer_to_log = regenerated_answer if regenerated_answer else result["answer"]
            try:
                append_log_row(
                    timestamp=log_timestamp_utc(),
                    bot_name=bot_name,
                    question=result["question"],
                    answer=answer_to_log,
                    context=result["context"],
                    criteria=criteria_name or "",
                    score=criteria_score,
                )
            except Exception as e:
                logger.warning(f"Failed to write to logs_fast.csv: {e}")
            
            # Reset processing state
            st.session_state.is_processing = False
            st.session_state.current_question = None
            st.session_state.processing_started = False
            
            # Rerun to update the display
            st.rerun()


if __name__ == "__main__":
    main()

