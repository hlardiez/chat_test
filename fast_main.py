"""Fast CLI entry point for the Chat Test Project using completion API."""

import sys
import argparse
import logging
import time
from src.utils import setup_logging
from fast_chat_engine import FastChatEngine
from fast_utils import get_criteria_from_csv, append_log_row, log_timestamp_utc, LOGS_FAST_CSV

# Set logging to WARNING level to suppress INFO/DEBUG messages
setup_logging(level=logging.WARNING)
logger = logging.getLogger(__name__)

CRITERIA_NAME = "Contextual_Hallucination"


def main():
    """Main CLI entry point."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Fast Chat Test Project - RAG-based Chat Engine with Completion API')
    parser.add_argument('--u', '--url', dest='base_url', required=True,
                        help='Base URL for the completion API (e.g., http://10.10.10.10:8080)')
    parser.add_argument('-nl', '--no-logs', dest='no_logs', action='store_true',
                        help='Do not log Q&A to logs_fast.csv (logging is on by default)')
    args = parser.parse_args()
    logs_enabled = not args.no_logs
    
    # Get criteria from CSV
    criteria_prompt = get_criteria_from_csv('criteria.csv', 'Contextual_Hallucination')
    if not criteria_prompt:
        logger.error("Failed to load Contextual_Hallucination criteria from criteria.csv")
        print("\n[ERROR] Failed to load criteria from criteria.csv")
        sys.exit(1)
    
    print("=" * 60)
    print("Fast Chat Test Project - RAG-based Chat Engine")
    print("=" * 60)
    print(f"Completion API: {args.base_url}")
    if logs_enabled:
        print(f"Logging enabled: writing to {LOGS_FAST_CSV}")
    else:
        print("Logging disabled (-nl)")
    print("Type 'quit' or 'exit' to end the session")
    print("=" * 60)
    print()
    
    try:
        # Initialize chat engine
        print("Initializing chat engine...")
        engine = FastChatEngine(base_url=args.base_url, criteria_prompt=criteria_prompt)
        print("Chat engine ready!\n")
        
        # Interactive chat loop
        while True:
            try:
                # Get user input
                question = input("\nYou: ").strip()
                
                # Check for exit commands
                if question.lower() in ['quit', 'exit', 'q']:
                    print("\nGoodbye!")
                    break
                
                if not question:
                    print("Please enter a question.")
                    continue
                
                # Start overall turnaround time tracking
                overall_start_time = time.time()
                
                # Process the question
                print("\nProcessing...", end='', flush=True)
                result = engine.process_question(question)
                
                # Step 1 & 2: Show bot's answer first (replace "Processing..." line)
                print("\r" + " " * 60 + "\r" + "-" * 60)
                print("Bot:", result['answer'])
                print("-" * 60)
                
                # Step 3 & 4: Show evaluation results
                evaluation_result = result.get('evaluation_result')
                evaluation_time = result.get('evaluation_time')
                if evaluation_result:
                    score = evaluation_result.get('score')
                    if score is not None:
                        print("\nEvaluation")
                        print("-" * 60)
                        print(f"Contextual_Hallucination - Score: {score}")
                        if evaluation_time is not None:
                            print(f"Evaluation time: {evaluation_time:.3f}s")
                
                # Step 5: Check if regeneration is needed
                regenerated_answer = engine.regenerate_answer_if_needed(
                    question=result['question'],
                    answer=result['answer'],
                    context=result['context'],
                    evaluation_result=evaluation_result
                )
                
                # Step 5.2: If regenerated, show ERRONEOUS ANSWER and regenerated answer
                if regenerated_answer:
                    print("\nERRONEOUS ANSWER")
                    print("-" * 60)
                    print("Regenerated Answer:", regenerated_answer)
                    print("-" * 60)
                
                # Calculate and display overall turnaround time
                overall_time = time.time() - overall_start_time
                print(f"\nOverall turnaround time: {overall_time:.3f}s")
                print("-" * 60)
                
                # Log to CSV by default (use -nl to disable)
                if logs_enabled:
                    answer_to_log = regenerated_answer if regenerated_answer else result['answer']
                    score_val = evaluation_result.get('score') if evaluation_result else None
                    append_log_row(
                        timestamp=log_timestamp_utc(),
                        bot_name="fast-constitution",
                        question=result['question'],
                        answer=answer_to_log,
                        context=result['context'],
                        criteria=CRITERIA_NAME,
                        score=score_val,
                    )
                
            except KeyboardInterrupt:
                print("\n\nInterrupted by user. Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error processing question: {str(e)}")
                print(f"\n[ERROR] Error: {str(e)}")
                print("Please try again or type 'quit' to exit.")
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print(f"\n[ERROR] Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

