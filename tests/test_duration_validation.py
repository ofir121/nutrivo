import pytest
from app.services.conflict_resolver import ConflictResolver
from app.services.parser_service import QueryParser
from app.models import ParsedQuery
from fastapi import HTTPException

# Test Parser Service
def test_parser_extracts_large_numbers():
    parser = QueryParser()
    parsed = parser.parse("Create a 10 day meal plan")
    assert parsed.days == 10

def test_parser_extracts_normal_numbers():
    parser = QueryParser()
    parsed = parser.parse("Create a 5 day meal plan")
    assert parsed.days == 5

# Test Conflict Resolver
def test_validation_raises_error_for_large_duration():
    resolver = ConflictResolver()
    parsed = ParsedQuery(days=10)
    
    with pytest.raises(HTTPException) as excinfo:
        resolver.validate(parsed)
    
    assert excinfo.value.status_code == 400
    assert excinfo.value.detail["error_code"] == "DURATION_LIMIT_EXCEEDED"
    assert "maximum is 7 days" in excinfo.value.detail["message"]

def test_validation_passes_for_valid_duration():
    resolver = ConflictResolver()
    parsed = ParsedQuery(days=7)
    try:
        resolver.validate(parsed)
    except HTTPException:
        pytest.fail("Validation raised HTTPException unexpectedly for 7 days")

    parsed_small = ParsedQuery(days=3)
    try:
        resolver.validate(parsed_small)
    except HTTPException:
        pytest.fail("Validation raised HTTPException unexpectedly for 3 days")
