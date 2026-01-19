import pytest
from app.services.parser_service import QueryParser
from app.services.conflict_resolver import ConflictResolver

@pytest.fixture
def parser_service():
    """Fixture for QueryParser instance."""
    return QueryParser()

@pytest.fixture
def conflict_resolver():
    """Fixture for ConflictResolver instance."""
    return ConflictResolver()
