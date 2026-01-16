"""Utility functions for fast_main."""

import csv
import logging
from typing import Optional

logger = logging.getLogger(__name__)


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

