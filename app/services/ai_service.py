import os
import json
from typing import Dict, Any, Optional, List
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
            return result
            
        except Exception as e:
            print(f"LLM enhancement failed: {e}")
            return None



    


    def batch_estimate_preparation_time(self, recipes: Dict[str, str]) -> Dict[str, int]:
        """
        Batch estimate preparation time for multiple recipes.
        Args:
            recipes: Dict mapping recipe_id -> instructions text
        Returns:
            Dict mapping recipe_id -> estimated total minutes
        """
        if not self.client or not recipes:
            return {}

        try:
            # Construct a prompt with all recipes
            items_str = ""
            for rid, instructions in recipes.items():
                items_str += f"\n--- Recipe ID: {rid} ---\n{instructions[:1000]}\n"

            prompt = f"""
            Analyze the instructions for the following recipes and estimate the TOTAL time required (Preparation + Cooking + Wait Time) for EACH.
            
            Return ONLY a valid JSON object where keys are the Recipe IDs and values are the total minutes (integer).
            Example: {{"1": 45, "mealdb_52772": 30}}
            If no time is mentioned, default to 30.

            Recipes:
            {items_str}
            """

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
            
            # Ensure all requested IDs are in the result
            final_estimates = {}
            for rid in recipes.keys():
                # Cast keys to string just in case LLM returns numbers or strings mixed
                val = result.get(str(rid)) or result.get(rid)
                final_estimates[rid] = int(val) if val else 30
                
            return final_estimates

        except Exception as e:
            print(f"Batch time estimation failed: {e}")
            # Fallback for all
            return {rid: 30 for rid in recipes}



    def batch_process_recipes(self, recipes: Dict[str, str], estimate_time: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Batch process recipes to format instructions and optionally estimate time in ONE LLM call.
        
        Args:
            recipes: Dict mapping unique_id -> instructions text
            estimate_time: Whether to also estimate preparation time
            
        Returns:
            Dict mapping unique_id -> {
                "instructions": List[str],  # Formatted steps
                "total_minutes": int (optional)
            }
        """
        if not self.client or not recipes:
            return {}

        try:
            # Construct a prompt with all recipes
            items_str = ""
            for rid, instructions in recipes.items():
                items_str += f"\n--- Recipe ID: {rid} ---\n{instructions[:1000]}\n"

            task_desc = "1. Reformat instructions into clean list of strings."
            response_structure = '"steps": ["Step 1", "Step 2"]'
            
            if estimate_time:
                task_desc += "\n            2. Estimate TOTAL preparation + cooking time in minutes."
                response_structure += ', "total_minutes": 45'
            
            prompt = f"""
            Analyze the following recipes. For EACH recipe:
            {task_desc}
            
            Return ONLY a valid JSON object where keys are the Recipe IDs and values are objects containing:
            {{{response_structure}}}
            
            If time cannot be estimated, default to 30.
            
            Recipes:
            {items_str}
            """

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
            
            # Normalize result keys
            final_results = {}
            for rid in recipes.keys():
                # Handle potential key mismatch (str vs int)
                data = result.get(str(rid)) or result.get(rid)
                
                processed = {}
                if data:
                    processed["instructions"] = data.get("steps", [])
                    if estimate_time:
                        processed["total_minutes"] = int(data.get("total_minutes", 30))
                else:
                     # Fallback
                     processed["instructions"] = [] # specialized fallback handled by caller? Or just return empty here
                
                final_results[rid] = processed
                    
            return final_results

        except Exception as e:
            print(f"Batch processing failed: {e}")
            return {}

ai_service = AIService()
