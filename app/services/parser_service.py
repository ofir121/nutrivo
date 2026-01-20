import re
from typing import List, Optional
from app.models import ParsedQuery
from app.core.rules import DIET_DEFINITIONS, INGREDIENT_SYNONYMS
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class QueryParser:
    def parse(self, query: str) -> ParsedQuery:
        """Parse a natural language query into a structured ParsedQuery.

        Args:
            query: User input text.

        Returns:
            ParsedQuery with extracted constraints and preferences.
        """
        query_lower = query.lower()
        # 1. Try rule-based extraction first
        days = self._extract_duration(query_lower)
        diets = self._extract_diets(query_lower)
        exclude = self._extract_exclusions(query_lower)
        calories = self._extract_calories(query_lower)
        meals_per_day = self._extract_meals_per_day(query_lower)
        preferences = self._extract_preferences(query_lower)

        # 2. Only use LLM for ambiguous queries
        enhanced = None
        if self._is_ambiguous(query_lower, days, diets, exclude, calories, preferences):
            enhanced = self._try_llm_enhancement(query, {
                "days": days,
                "diets": diets,
                "exclude": exclude,
                "calories": calories,
                "preferences": preferences,
                "meals_per_day": meals_per_day
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
        if enhanced and enhanced.get("preferences"):
            preferences = self._merge_preferences(preferences, enhanced.get("preferences", []))

        
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
            logger.error(f"LLM enhancement failed: {e}")
            return None

    def _extract_duration(self, text: str) -> int:
        """Extract requested duration in days with a default fallback."""
        if "next week" in text or "week" in text:
            # Check for "2 weeks", etc. if wanted, but cap at 7 as per spec
            return 7
        
        match = re.search(r'(\d+)\s*-?\s*day', text)
        if match:
            val = int(match.group(1))
            return max(val, 1) # Clamp min 1
        return 3 # Default

    def _extract_diets(self, text: str) -> List[str]:
        """Extract known diet keywords from the query."""
        # Collect all matches
        found_diets = []
        for diet in DIET_DEFINITIONS.keys():
            if diet in text:
                found_diets.append(diet)
        return found_diets


    def _extract_exclusions(self, text: str) -> List[str]:
        """Extract ingredient exclusions from explicit or '-free' patterns."""
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
        """Extract target calorie value if present."""
        match = re.search(r'(\d+)\s*(?:cal|kcal|calories)', text)
        if match:
             return int(match.group(1))
        return None

    def _extract_meals_per_day(self, text: str) -> int:
        """Extract meals per day, defaulting to 3 with snack bump."""
        # Check for snacks
        count = 3
        if "snack" in text:
            count += 1 # Rough logic
        return count

    def _extract_preferences(self, text: str) -> List[str]:
        """Extract soft preferences from common query phrases."""
        preferences = set()
        if re.search(r'\bhigh[- ]protein\b', text):
            preferences.add("high-protein")
        if re.search(r'\blow[- ]carb\b', text):
            preferences.add("low-carb")
        if re.search(r'\bbudget(-friendly)?\b', text):
            preferences.add("budget-friendly")
        if re.search(r'\bquick\b|\bfast\b', text):
            preferences.add("quick")

        minutes_match = re.search(r'under\s+(\d+)\s*(?:minutes|mins|min)\b', text)
        if minutes_match:
            minutes = minutes_match.group(1)
            preferences.add("quick")
            preferences.add(f"under-{minutes}-minutes")

        if "healthy" in text:
            preferences.add("healthy")

        return list(preferences)

    def _merge_preferences(self, base: List[str], extra: List[str]) -> List[str]:
        """Merge preference lists preserving order and uniqueness."""
        merged = []
        for pref in base + extra:
            if pref not in merged:
                merged.append(pref)
        return merged

    def _is_ambiguous(
        self,
        text: str,
        days: int,
        diets: List[str],
        exclude: List[str],
        calories: Optional[int],
        preferences: List[str]
    ) -> bool:
        """Determine whether the query lacks concrete constraints."""
        vague_terms = ["healthy", "next week"]
        vague_only = [p for p in preferences if p in ["healthy"]]
        has_specifics = bool(diets or exclude or calories or (preferences and len(vague_only) < len(preferences)))

        if not diets and not exclude and calories is None and not preferences and days == 3:
            return True

        if any(term in text for term in vague_terms) and not has_specifics:
            return True

        return False

parser_service = QueryParser()
