import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging_config import get_logger
from app.models import Recipe
from app.services.ai_service import ai_service

logger = get_logger(__name__)


class RerankerService:
    def __init__(self) -> None:
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl_seconds = int(os.getenv("RERANK_CACHE_TTL_SECONDS", "86400"))

    def rerank(
        self,
        query: str,
        meal_slot: str,
        meal_type: str,
        candidates: List[Recipe],
        scores_by_id: Dict[str, float],
        constraints: Dict[str, Any],
        history: Dict[str, Any],
        fallback_id: str
    ) -> Tuple[str, Optional[List[str]]]:
        """Return the chosen candidate id and optional reasons from the LLM."""
        if not candidates or len(candidates) < 2:
            return fallback_id, None
        if not ai_service.client:
            return fallback_id, None

        candidate_ids = [c.id for c in candidates]
        cache_key = self._cache_key(query, meal_slot, candidate_ids, constraints, history)
        cached = self._cache_get(cache_key)
        if cached:
            chosen = self._choose_valid_id(cached, set(candidate_ids))
            if chosen:
                return chosen, self._extract_reasons(cached)
            return fallback_id, None

        payload = self._build_payload(meal_type, candidates, scores_by_id, constraints, history)
        prompt = self._build_prompt(payload)
        result = self._call_llm(prompt)
        if not result:
            return fallback_id, None

        self._cache_set(cache_key, result)
        chosen = self._choose_valid_id(result, set(candidate_ids))
        if chosen:
            return chosen, self._extract_reasons(result)
        return fallback_id, None

    def _build_payload(
        self,
        meal_type: str,
        candidates: List[Recipe],
        scores_by_id: Dict[str, float],
        constraints: Dict[str, Any],
        history: Dict[str, Any]
    ) -> Dict[str, Any]:
        scores = [scores_by_id.get(r.id, 0.0) for r in candidates]
        min_score = min(scores) if scores else 0.0
        max_score = max(scores) if scores else 0.0

        def score_to_100(raw: float) -> float:
            if max_score == min_score:
                return 50.0
            return round((raw - min_score) / (max_score - min_score) * 100.0, 2)

        return {
            "meal_type": meal_type,
            "constraints": constraints,
            "history": history,
            "candidates": [
                {
                    "id": recipe.id,
                    "title": recipe.title,
                    "key_ingredients": self._extract_key_ingredients(recipe.ingredients),
                    "meal_type": meal_type,
                    "cuisine_or_tags": recipe.dish_types or recipe.diets,
                    "prep_time_minutes": recipe.ready_in_minutes,
                    "macros": {
                        "calories": recipe.nutrition.calories,
                        "protein_g": recipe.nutrition.protein,
                        "carbs_g": recipe.nutrition.carbs,
                        "fat_g": recipe.nutrition.fat
                    },
                    "your_score": score_to_100(scores_by_id.get(recipe.id, 0.0)),
                    "short_notes": None
                }
                for recipe in candidates
            ]
        }

    def _build_prompt(self, payload: Dict[str, Any]) -> str:
        payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
        return (
            "You are a meal-plan reranking assistant. You must only choose from the provided candidates.\n"
            "Hard constraints must be honored (dietary restrictions, exclusions, time limits, meal type).\n"
            "Avoid repetition using the provided history when possible.\n\n"
            f"INPUT_JSON:{payload_json}\n\n"
            "Return ONLY a JSON object with this exact schema:\n"
            "{\n"
            '  "selected_id": "<string>",\n'
            '  "backup_id": "<string|null>",\n'
            '  "reasons": ["<short bullet>", "..."],\n'
            '  "confidence": 0.0\n'
            "}\n"
            "Rules:\n"
            "- selected_id MUST be one of the candidate ids.\n"
            "- backup_id MUST be one of the candidate ids or null.\n"
            "- reasons: max 4 items, each <= 15 words.\n"
            "- No additional keys. No prose outside JSON."
        )

    def _call_llm(self, prompt: str) -> Optional[Dict[str, Any]]:
        try:
            response = ai_service.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You strictly output valid JSON for the requested schema."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as exc:
            logger.error(f"Reranker LLM call failed: {exc}")
            return None

    def _choose_valid_id(self, result: Dict[str, Any], candidate_ids: set) -> Optional[str]:
        if not isinstance(result, dict):
            return None
        selected_id = result.get("selected_id")
        backup_id = result.get("backup_id")
        if selected_id in candidate_ids:
            return selected_id
        if backup_id in candidate_ids:
            return backup_id
        return None

    def _extract_reasons(self, result: Dict[str, Any]) -> Optional[List[str]]:
        reasons = result.get("reasons")
        if not isinstance(reasons, list):
            return None
        cleaned = [r for r in reasons if isinstance(r, str) and r.strip()]
        return cleaned or None

    def _extract_key_ingredients(self, ingredients: List[str], limit: int = 6) -> List[str]:
        if not ingredients:
            return []
        cleaned = []
        for item in ingredients:
            base = item.split("(")[0].strip()
            if base:
                cleaned.append(base)
        return cleaned[:limit]

    def _cache_key(
        self,
        query: str,
        meal_slot: str,
        candidate_ids: List[str],
        constraints: Dict[str, Any],
        history: Dict[str, Any]
    ) -> str:
        payload = {
            "query": query,
            "meal_slot": meal_slot,
            "candidate_ids": sorted(candidate_ids),
            "constraints": constraints,
            "history": history
        }
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def _cache_get(self, key: str) -> Optional[Dict[str, Any]]:
        item = self.cache.get(key)
        if not item:
            return None
        if item["expires_at"] < time.time():
            self.cache.pop(key, None)
            return None
        return item["value"]

    def _cache_set(self, key: str, value: Dict[str, Any]) -> None:
        self.cache[key] = {
            "value": value,
            "expires_at": time.time() + self.cache_ttl_seconds
        }


reranker_service = RerankerService()
