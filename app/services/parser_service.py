import re
from typing import List, Optional, Set
from app.models import ParsedQuery
from app.core.rules import DIET_DEFINITIONS, INGREDIENT_SYNONYMS

class QueryParser:
    def parse(self, query: str) -> ParsedQuery:
        query_lower = query.lower()
        

        
        # 1. Try rule-based extraction first

        days = self._extract_duration(query_lower)
        diets = self._extract_diets(query_lower)
        exclude = self._extract_exclusions(query_lower)
        calories = self._extract_calories(query_lower)
        meals_per_day = self._extract_meals_per_day(query_lower)
        


        # 2. Always use LLM for intent extraction (parallel enrichment)

        
        enhanced = self._try_llm_enhancement(query, {
            "days": days,
            "diets": diets,
            "exclude": exclude,
            "calories": calories
        })
        
        if enhanced:

            
            # Merge LLM results with rule-based results
            # Prefer LLM if it has meaningful data, otherwise use rule-based
            days = enhanced.get("duration_days") if enhanced.get("duration_days") else days
            
            # Merge diets (combine both sources, remove duplicates)
            llm_diets = enhanced.get("diets", [])
            combined_diets = list(set(diets + llm_diets))
            diets = combined_diets if combined_diets else diets
            
            # Merge exclusions (combine both sources, remove duplicates)
            llm_exclude = enhanced.get("exclusions", [])
            combined_exclude = list(set(exclude + llm_exclude))
            exclude = combined_exclude if combined_exclude else exclude
            
            # Use LLM calories if available
            if enhanced.get("calories"):
                calories = enhanced.get("calories")
            
            # Use LLM meals_per_day if available
            if enhanced.get("meals_per_day"):
                meals_per_day = enhanced.get("meals_per_day")
            
        # Extract preferences from LLM response
        preferences = []
        if enhanced and enhanced.get("preferences"):
            preferences = enhanced.get("preferences", [])

        
        # Extract clarified intent from LLM response
        clarified_intent = None
        if enhanced and enhanced.get("clarified_intent"):
            clarified_intent = enhanced.get("clarified_intent")
        


        return ParsedQuery(
            days=days,
            diets=diets,
            calories=calories,
            exclude=exclude,
            preferences=preferences,
            meals_per_day=meals_per_day,
            clarified_intent=clarified_intent
        )
    

    
    def _try_llm_enhancement(self, query: str, current_parse: dict) -> Optional[dict]:
        """
        Call LLM to enhance the parse for ambiguous queries.
        """
        try:
            from app.services.ai_service import ai_service
            return ai_service.enhance_query(query, current_parse)
        except Exception as e:
            print(f"LLM enhancement failed: {e}")
            return None

    def _extract_duration(self, text: str) -> int:
        if "next week" in text or "week" in text:
            # Check for "2 weeks", etc. if wanted, but cap at 7 as per spec
            return 7
        
        match = re.search(r'(\d+)\s*-?\s*day', text)
        if match:
            val = int(match.group(1))
            return max(val, 1) # Clamp min 1
        return 3 # Default

    def _extract_diets(self, text: str) -> List[str]:
        # Collect all matches
        found_diets = []
        for diet in DIET_DEFINITIONS.keys():
            if diet in text:
                found_diets.append(diet)
        return found_diets


    def _extract_exclusions(self, text: str) -> List[str]:
        exclusions = set()
        
        # Check for explicit "no X", "exclude X", "without X"
        # Regex for "no [word]" or "exclude [word]"
        matches = re.findall(r'(?:no|exclude|without)\s+([a-z]+)', text)
        for match in matches:
             # Normalize if synonym exists
             key = match
             # Simple check: if key is in SYNONYMS keys
             if key in INGREDIENT_SYNONYMS:
                 exclusions.add(key)
             else:
                 # It might be a direct ingredient
                 exclusions.add(key)
        
        # Also check for "-free" patterns like "gluten-free" -> exclude gluten
        # This is slightly overlapping with diet types, but "gluten-free" is both a diet and an exclusion.
        free_matches = re.findall(r'([a-z]+)-free', text)
        for match in free_matches:
            if match == "gluten": exclusions.add("gluten") # explicit handling?
            if match == "dairy": exclusions.add("dairy")
            if match == "nut": exclusions.add("nut")
            if match == "sugar": exclusions.add("sugar")
        
        return list(exclusions)

    def _extract_calories(self, text: str) -> Optional[int]:
        match = re.search(r'(\d+)\s*(?:cal|kcal|calories)', text)
        if match:
             return int(match.group(1))
        return None

    def _extract_meals_per_day(self, text: str) -> int:
        # Check for snacks
        count = 3
        if "snack" in text:
            count += 1 # Rough logic
        return count

parser_service = QueryParser()
