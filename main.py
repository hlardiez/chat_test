"""CLI entry point for the Chat Test Project."""

import sys
import argparse
import logging
from src.utils import setup_logging
from src.chat_engine import ChatEngine

# Set logging to WARNING level to suppress INFO/DEBUG messages
setup_logging(level=logging.WARNING)
logger = logging.getLogger(__name__)


def main():
    """Main CLI entry point."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Chat Test Project - RAG-based Chat Engine')
    # Support both -t and -T flags (both set the same destination)
    parser.add_argument('-t', dest='show_eval_time', action='store_true',
                        help='Show evaluation time with evaluation results')
    parser.add_argument('-T', dest='show_eval_time', action='store_true',
                        help='Show evaluation time with evaluation results (same as -t)')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Chat Test Project - RAG-based Chat Engine")
    print("=" * 60)
    print("Type 'quit' or 'exit' to end the session")
    if args.show_eval_time:
        print("Evaluation time display: ENABLED")
    print("=" * 60)
    print()
    
    try:
        # Initialize chat engine
        print("Initializing chat engine...")
        engine = ChatEngine()
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
                
                # Process the question
                print("\nProcessing...", end='', flush=True)
                result = engine.process_question(question)
                
                # Step 1 & 2: Show bot's answer first (replace "Processing..." line)
                print("\r" + " " * 60 + "\r" + "-" * 60)
                print("Bot:", result['answer'])
                print("-" * 60)
                
                # Step 3 & 4: Show evaluation results
                ragmetrics_result = result.get('ragmetrics_result')
                evaluation_time = result.get('evaluation_time')
                if ragmetrics_result:
                    criteria_list = None
                    
                    # Check if we have criteria in the result
                    if 'criteria' in ragmetrics_result and isinstance(ragmetrics_result['criteria'], list):
                        criteria_list = ragmetrics_result['criteria']
                    elif 'raw_response' in ragmetrics_result and isinstance(ragmetrics_result['raw_response'], dict):
                        raw = ragmetrics_result['raw_response']
                        if 'results' in raw and isinstance(raw['results'], list):
                            criteria_list = raw['results']
                        elif 'criteria' in raw and isinstance(raw['criteria'], list):
                            criteria_list = raw['criteria']
                    
                    # Display criteria if found
                    if criteria_list:
                        print("\nEvaluation")
                        print("-" * 60)
                        for criterion in criteria_list:
                            if isinstance(criterion, dict):
                                name = criterion.get('criteria', criterion.get('name', criterion.get('criterion_name', 'Unknown')))
                                score = criterion.get('score', 'N/A')
                                reason = criterion.get('reason', criterion.get('reasoning', criterion.get('explanation', 'N/A')))
                                print(f"{name} - {score}: {reason}")
                            else:
                                print(f"{criterion}")
                        # Show evaluation time if flag is set
                        if args.show_eval_time and evaluation_time is not None:
                            print(f"\nEvaluation time: {evaluation_time:.3f}s")
                    # Fallback: Check for single score and reasoning
                    elif 'score' in ragmetrics_result or 'reasoning' in ragmetrics_result:
                        print("\nEvaluation")
                        print("-" * 60)
                        score = ragmetrics_result.get('score', 'N/A')
                        reasoning = ragmetrics_result.get('reason', ragmetrics_result.get('reasoning', ragmetrics_result.get('explanation', 'N/A')))
                        criterion_name = ragmetrics_result.get('criteria', ragmetrics_result.get('criterion_name', ragmetrics_result.get('name', 'Overall')))
                        print(f"{criterion_name} - {score}: {reasoning}")
                        # Show evaluation time if flag is set
                        if args.show_eval_time and evaluation_time is not None:
                            print(f"\nEvaluation time: {evaluation_time:.3f}s")
                
                # Step 5: Check if regeneration is needed
                regenerated_answer = engine.regenerate_answer_if_needed(
                    question=result['question'],
                    answer=result['answer'],
                    context=result['context'],
                    ragmetrics_result=ragmetrics_result
                )
                
                # Step 5.2: If regenerated, show ERRONEOUS ANSWER and regenerated answer
                if regenerated_answer:
                    print("\nERRONEOUS ANSWER")
                    print("-" * 60)
                    print("Regenerated Answer:", regenerated_answer)
                    print("-" * 60)
                
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

