
"""
Prompt template for LLM Judge API calls
"""

#===============================================================
# Prompt template for LLM Judge API calls with score only
#===============================================================

DEBUG_MODE = False
MAX_TOKENS = 256
STOP_SEQUENCE = ["###"]
TEMPERATURE = 0.1
TOP_P = 0.8
TOP_K = 40
REPEAT_PENALTY = 1.1

# GBNF Grammar for JSON score response
# This enforces the model to return only valid JSON in the format: {"score": 1-5, "reason": "..."}
JSON_SCORE_GRAMMAR = r'''
root ::= json-object
json-object ::= "{" ws "\"score\"" ws ":" ws number ws "," ws "\"reason\"" ws ":" ws string ws "}"
number ::= [1-5]
string ::= "\"" string-char* "\""
string-char ::= [^"\\] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F])
ws ::= [ \t\n]*
'''

JSON_SCORE_GRAMMAR_SCORE_ONLY = r'''
root ::= json-object
json-object ::= "{" ws "\"score\"" ws ":" ws number ws "}"
number ::= [1-5]
ws ::= [ \t\n]*
'''



PROMPT_RATE_ANSWER_SCORE_ONLY = """
You are an impartial grader.
Review the candidate answer and the correct answer based on the following context as inidicated in the criteria:
Review all the criteria scores.

<Criteria>
{criteria_prompt}
</Criteria>


Output ONLY a valid JSON object. 
Do not output explanations, reasoning, or commentary.
Do not output any text before or after the JSON.
Do not restate the task.
Do not justify the score.

Your response MUST follow this exact JSON format:

{{
  "score": X,
}}

Replace X with your chosen integer score from 1 to 5.

<Question>
{question}
</Question>

<Candidate Answer>  
{candidate_answer}
</Candidate Answer>

<Ground Truth>
{ground_truth}
</Ground Truth>

<Context>
{context}
</Context>
"""

PROMPT_RATE_ANSWER = """
You are an impartial grader.
Review the candidate answer and the correct answer based on the following context as inidicated in the criteria:
Review all the scores defintions carefully and choose the best score based on the definitions.

<Criteria>
{criteria_prompt}
</Criteria>

Output ONLY a valid JSON object. 
Do not output any text before or after the JSON.
Do not restate the task.

Your response MUST follow this exact JSON format:

{{
  "score": X,
  "reason": "..."
}}

Replace X with your chosen integer score from 1 to 5.
Replace "..." with your chosen reason for the score.

<Question>
{question}
</Question>

<Ground Truth>
{ground_truth}
</Ground Truth>

<Candidate Answer>
{candidate_answer}
</Candidate Answer>

<Context> 
{context}
</Context>
"""
