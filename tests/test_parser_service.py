import pytest
from unittest.mock import patch, MagicMock
from app.services.parser_service import QueryParser

class TestParserService:
    
    # --- Rule-Based Extraction Tests ---

    def test_extract_duration_explicit_days(self, parser_service):
        """Test extraction of specific day counts."""
        assert parser_service._extract_duration("3 days") == 3
        assert parser_service._extract_duration("1 day") == 1
        assert parser_service._extract_duration("10 days") == 7  # Clamped to 7
        assert parser_service._extract_duration("0 days") == 1   # Clamped to 1

    def test_extract_duration_weeks(self, parser_service):
        """Test extraction of week-related keywords."""
        assert parser_service._extract_duration("next week") == 7
        assert parser_service._extract_duration("for a week") == 7

    def test_extract_diets(self, parser_service):
        """Test extraction of diet keywords."""
        assert "vegan" in parser_service._extract_diets("I want a vegan meal plan")
        assert "keto" in parser_service._extract_diets("strict keto diet")
        diets = parser_service._extract_diets("vegan and gluten-free")
        assert "vegan" in diets
        assert "gluten-free" in diets

    def test_extract_exclusions_explicit(self, parser_service):
        """Test extraction of explicit exclusions."""
        exclusions = parser_service._extract_exclusions("no dairy")
        assert "dairy" in exclusions
        
        exclusions = parser_service._extract_exclusions("exclude peanuts")
        assert "peanuts" in exclusions # Normalized synonym (if mapped) or substring match depending on logic

    def test_extract_exclusions_free_pattern(self, parser_service):
        """Test extraction of -free patterns."""
        exclusions = parser_service._extract_exclusions("gluten-free")
        assert "gluten" in exclusions
        
        exclusions = parser_service._extract_exclusions("dairy-free")
        assert "dairy" in exclusions

    def test_extract_calories(self, parser_service):
        """Test calorie extraction."""
        assert parser_service._extract_calories("2000 calories") == 2000
        assert parser_service._extract_calories("1500 kcal") == 1500
        assert parser_service._extract_calories("no calorie info") is None

    def test_extract_meals_per_day(self, parser_service):
        """Test meals per day logic."""
        assert parser_service._extract_meals_per_day("standard plan") == 3
        assert parser_service._extract_meals_per_day("include snacks") == 4

    # --- Integration / Full Parse Tests with Mocked LLM ---

    @patch('app.services.parser_service.QueryParser._try_llm_enhancement')
    def test_parse_simple_query(self, mock_llm, parser_service):
        """Test parsing a simple query without effective LLM enhancement."""
        # Setup mock to return None or empty dict, mimicking failure or no enhancement
        mock_llm.return_value = None
        
        query = "vegan meal plan for 3 days 2000 calories"
        result = parser_service.parse(query)
        
        assert result.days == 3
        assert "vegan" in result.diets
        assert result.calories == 2000
        assert result.meals_per_day == 3 # Default

    @patch('app.services.parser_service.QueryParser._try_llm_enhancement')
    def test_parse_with_llm_enhancement(self, mock_llm, parser_service):
        """Test that LLM results override or merge with rule-based results."""
        # Setup mock to return enhanced data
        mock_llm.return_value = {
            "original_prompt": "complicated query",
            "clarified_intent": "user wants high protein vegan",
            "duration_days": 5,
            "diets": ["vegan", "high-protein"],
            "exclusions": ["soy"],
            "calories": 2500,
            "meals_per_day": 5
        }
        
        query = "complicated query" 
        # Rule based might find nothing or different things
        # Let's say rule based finds "vegan" from the query string "complicated query" (unlikely but let's assume query was "vegan something")
        
        result = parser_service.parse(query)
        
        # Verify LLM overrides/merges
        assert result.days == 5 # Overrides default 3
        assert "vegan" in result.diets
        assert "high-protein" in result.diets
        assert "soy" in result.exclude
        assert result.calories == 2500
        assert result.meals_per_day == 5
        assert result.clarified_intent == "user wants high protein vegan"
