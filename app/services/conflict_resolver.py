from typing import List, Optional
from fastapi import HTTPException
from app.models import ParsedQuery
from app.core.rules import INCOMPATIBLE_DIETS

class ConflictResolver:
    def validate(self, parsed: ParsedQuery):
        """
        Checks for inherent conflicts in the parsed query.
        Raises HTTPException(409) if a conflict is found.
        """
        
        # 1. Check Duration Limit
        if parsed.days > 7:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "DURATION_LIMIT_EXCEEDED",
                    "message": f"You requested a plan for {parsed.days} days, but the maximum is 7 days.",
                    "suggestion": "Please request a meal plan for 7 days or fewer."
                }
            )

        # 2. Check Diet Conflicts
        # Checks if the user requested any pair of diets that are known to be incompatible.
        detected = set(parsed.diets)
        
        for incompatible_set in INCOMPATIBLE_DIETS:
            # If the user's diets contain BOTH elements of an incompatible pair
            if incompatible_set.issubset(detected):
                conflicts = list(incompatible_set)
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error_code": "CONFLICTING_DIETS",
                        "message": f"You requested conflicting diets: {', '.join(conflicts)}",
                        "suggestion": f"Please choose either {conflicts[0]} or {conflicts[1]}, but not both."
                    }
                )

conflict_resolver = ConflictResolver()

