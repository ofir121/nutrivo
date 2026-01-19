import os
import json
from typing import Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class AIService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Warning: OPENAI_API_KEY not set. LLM enhancement will be disabled.")
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key)
    
    def enhance_query(self, query: str, low_confidence_parse: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Use LLM to extract structured intent from ambiguous queries.
        
        Args:
            query: The original natural language query
            low_confidence_parse: The parser's best attempt (for context)
        
        Returns:
            Enhanced parsed data or None if LLM unavailable
        """
        if not self.client:
            return None
        
        
        prompt = f"""You are a meal planning assistant. Extract structured information from the user's query.

User Query: "{query}"

Analyze the query and return a JSON object with the following structure:

{{
  "original_prompt": "The exact original query text",
  "clarified_intent": "A clear, expanded version explaining what the user wants",
  "duration_days": <number 1-7, or null if not specified>,
  "diets": ["dietary restrictions like vegetarian, vegan, etc. Empty array [] if none"],
  "preferences": ["preferences like high-protein, low-carb, etc. Empty array [] if none"],
  "exclusions": ["ingredients to avoid like dairy, nuts, etc. Empty array [] if none"],
  "calories": <target calories per day as number, or null if not specified>,
  "meals_per_day": <number of meals (default 3), or null if not specified>
}}

Guidelines:
- Use null for numeric fields when not specified
- Use empty arrays [] for list fields when nothing is mentioned
- Extract preferences from words like "healthy", "quick", "budget"
- Default meals_per_day to 3

Now extract from: "{query}"
"""

        try:
            print(f"\n  📝 Constructing LLM Prompt:")
            print(f"  {'-'*66}")
            print(f"  Model: gpt-4o-mini")
            print(f"  Temperature: 0.1 (deterministic)")
            print(f"  Format: JSON")
            print(f"\n  Prompt Content:")
            print(f"  {'-'*66}")
            for line in prompt.split('\n')[:15]:  # Show first 15 lines
                print(f"  {line}")
            print(f"  ... (truncated)")
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Cost-effective model
                messages=[
                    {"role": "system", "content": "You are a precise data extraction assistant. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistency
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            print(f"\n  📨 Raw LLM Response:")
            print(f"  {'-'*66}")
            print(f"  {json.dumps(result, indent=2)}")
            
            return result
            
        except Exception as e:
            print(f"LLM enhancement failed: {e}")
            return None

    def format_instructions(self, raw_instructions: list[str]) -> list[str]:
        """
        Use LLM to format recipe instructions into a clean, numbered list.
        """
        if not self.client:
            return raw_instructions

        if not raw_instructions:
            return []
            
        # Join into a single block to contextually understand the flow
        text_block = "\n".join(raw_instructions)
        
        prompt = f"""
        Reformat the following recipe instructions into a clean, step-by-step list of strings.
        Remove any existing "Step 1", "Step 2" labels or numbering from the text itself, as the UI will handle numbering.
        Split complex paragraphs into logical individual steps.
        Return ONLY a JSON object with a single key "steps" containing the list of strings.

        Input Instructions:
        {text_block}
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful culinary assistant. Output valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("steps", raw_instructions)
            
        except Exception as e:
            print(f"Instruction formatting failed: {e}")
            return raw_instructions

ai_service = AIService()
