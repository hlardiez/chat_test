"""Utility functions for fast_main and web_ui logging."""

import csv
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

LOGS_FAST_CSV = "logs_fast.csv"


def append_log_row(
    timestamp: str,
    bot_name: str,
    question: str,
    answer: str,
    context: str,
    criteria: str,
    score,
) -> None:
    """Append one row to logs_fast.csv. Creates file with header if it doesn't exist."""
    file_exists = os.path.isfile(LOGS_FAST_CSV)
    score_str = "" if score is None else str(score)
    row = [timestamp, bot_name, question, answer, context, criteria, score_str]
    with open(LOGS_FAST_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "bot_name", "question", "answer", "context", "criteria", "score"])
        writer.writerow(row)


def log_timestamp_utc() -> str:
    """Return current UTC time as ISO string for logs."""
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def get_criteria_from_csv(csv_file: str, criteria_name: str) -> Optional[str]:
    """
    Read criteria definition from CSV file.
    
    Args:
        csv_file: Path to the criteria CSV file
        criteria_name: Name of the criteria to extract (e.g., "Contextual_Hallucination")
        
    Returns:
        The criteria prompt string, or None if not found
    """
    try:
        # Open with utf-8-sig to handle BOM (Byte Order Mark)
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Get criteria value - handle BOM in field name
                criteria_key = 'criteria'
                if criteria_key not in row:
                    # Try with BOM prefix
                    criteria_key = '\ufeffcriteria'
                
                criteria_value = row.get(criteria_key, '').strip()
                # Check if criteria name matches (case-insensitive)
                if criteria_value.lower() == criteria_name.lower():
                    prompt = row.get('prompt', '').strip()
                    if prompt:
                        logger.info(f"Found criteria '{criteria_name}' in CSV")
                        return prompt
                    else:
                        logger.warning(f"Criteria '{criteria_name}' found but prompt is empty")
                        return None
        
        logger.error(f"Criteria '{criteria_name}' not found in CSV file")
        return None
        
    except FileNotFoundError:
        logger.error(f"CSV file not found: {csv_file}")
        return None
    except Exception as e:
        logger.error(f"Error reading CSV file: {str(e)}")
        return None

