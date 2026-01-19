import pytest
from fastapi import HTTPException
from app.models import ParsedQuery

class TestConflictResolver:
    
    def test_validate_no_conflicts(self, conflict_resolver):
        """Test validation with compatible diets."""
        # Vegan and Gluten-Free are compatible
        parsed = ParsedQuery(
            days=3,
            diets=["vegan", "gluten-free"],
            calories=2000,
            exclude=[],
            meals_per_day=3
        )
        # Should not raise exception
        conflict_resolver.validate(parsed)

    def test_validate_conflict_vegan_pescatarian(self, conflict_resolver):
        """Test that Vegan + Pescatarian raises 409 Conflict."""
        parsed = ParsedQuery(
            days=3,
            diets=["vegan", "pescatarian"],
            calories=2000,
            exclude=[],
            meals_per_day=3
        )
        
        with pytest.raises(HTTPException) as exc_info:
            conflict_resolver.validate(parsed)
        
        assert exc_info.value.status_code == 409
        assert "CONFLICTING_DIETS" in exc_info.value.detail["error_code"]
        assert "vegan" in exc_info.value.detail["message"].lower()

    def test_validate_conflict_vegetarian_paleo(self, conflict_resolver):
        """Test that Vegetarian + Paleo raises 409 Conflict."""
        parsed = ParsedQuery(
            days=3,
            diets=["vegetarian", "paleo"],
            calories=2000,
            exclude=[],
            meals_per_day=3
        )
        
        with pytest.raises(HTTPException) as exc_info:
            conflict_resolver.validate(parsed)
            
        assert exc_info.value.status_code == 409
        assert "CONFLICTING_DIETS" in exc_info.value.detail["error_code"]

    def test_validate_duration_limit_exceeded(self, conflict_resolver):
        """Test that requesting > 7 days raises 400 Bad Request."""
        parsed = ParsedQuery(
            days=8,
            diets=["vegan"],
            calories=2000,
            exclude=[],
            meals_per_day=3
        )
        
        with pytest.raises(HTTPException) as exc_info:
            conflict_resolver.validate(parsed)
            
        assert exc_info.value.status_code == 400
        assert "DURATION_LIMIT_EXCEEDED" in exc_info.value.detail["error_code"]

    def test_validate_duration_limit_boundary(self, conflict_resolver):
        """Test that requesting 7 days is valid."""
        parsed = ParsedQuery(
            days=7,
            diets=["vegan"],
            calories=2000,
            exclude=[],
            meals_per_day=3
        )
        conflict_resolver.validate(parsed)
