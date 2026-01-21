import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging_config import get_logger
from app.core.llm_config import load_llm_config
from app.models import Recipe
from app.services.ai_service import ai_service

logger = get_logger(__name__)


class RerankerService:
    def __init__(self) -> None:
        """
        Initialize the reranker with an in-memory cache and TTL settings.
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl_seconds = load_llm_config().rerank_cache_ttl_seconds

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
        """
        Return the chosen candidate id and optional reasons from the LLM.
        Falls back to deterministic selection when reranking is unavailable.

        Args:
            query: Original user query string.
            meal_slot: Slot identifier (e.g., "day_1_breakfast").
            meal_type: Meal category (breakfast/lunch/dinner/snack).
            candidates: Candidate recipes to choose from.
            scores_by_id: Deterministic scores keyed by recipe id.
            constraints: Hard constraints from parsing (diets, exclusions, time).
            history: Prior selections for repetition avoidance.
            fallback_id: Deterministic fallback recipe id.

        Returns:
            Tuple of (selected recipe id, optional list of LLM reasons).
        """
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

    def rerank_batch(
        self,
        entries: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Batch rerank multiple meal slots in a single LLM call.
        Returns a mapping of meal_slot to the LLM selection payload.

        Args:
            entries: List of rerank payloads containing candidates and context.

        Returns:
            Mapping of meal_slot to selection payloads from the LLM.
        """
        if not entries or not ai_service.client:
            return {}

        payload = []
        for entry in entries:
            candidates = entry.get("candidates") or []
            if not candidates:
                continue
            scores = entry.get("scores_by_id", {})
            raw_scores = [scores.get(recipe.id, 0.0) for recipe in candidates]
            min_score = min(raw_scores) if raw_scores else 0.0
            max_score = max(raw_scores) if raw_scores else 0.0

            def score_to_100(raw: float) -> float:
                if max_score == min_score:
                    return 50.0
                return round((raw - min_score) / (max_score - min_score) * 100.0, 2)

            payload.append({
                "meal_slot": entry["meal_slot"],
                "meal_type": entry["meal_type"],
                "constraints": entry.get("constraints", {}),
                "history": entry.get("history", {}),
                "candidates": [
                    {
                        "id": recipe.id,
                        "title": recipe.title,
                        "key_ingredients": self._extract_key_ingredients(recipe.ingredients),
                        "meal_type": entry["meal_type"],
                        "cuisine_or_tags": recipe.dish_types or recipe.diets,
                        "prep_time_minutes": recipe.ready_in_minutes,
                        "macros": {
                            "calories": recipe.nutrition.calories,
                            "protein_g": recipe.nutrition.protein,
                            "carbs_g": recipe.nutrition.carbs,
                            "fat_g": recipe.nutrition.fat
                        },
                        "your_score": score_to_100(scores.get(recipe.id, 0.0)),
                        "short_notes": None
                    }
                    for recipe in candidates
                ]
            })

        if not payload:
            return {}

        prompt = self._build_batch_prompt(payload)
        result = self._call_llm_batch(prompt)
        if not result:
            return {}

        selections = result.get("selections")
        if not isinstance(selections, list):
            return {}

        output = {}
        for item in selections:
            if not isinstance(item, dict):
                continue
            meal_slot = item.get("meal_slot")
            if isinstance(meal_slot, str) and meal_slot:
                output[meal_slot] = item
        return output

    def _build_payload(
        self,
        meal_type: str,
        candidates: List[Recipe],
        scores_by_id: Dict[str, float],
        constraints: Dict[str, Any],
        history: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build a single-slot payload for LLM reranking.
        Includes normalized scores and prompt-friendly fields.

        Args:
            meal_type: Meal category for the slot.
            candidates: Candidate recipes to include.
            scores_by_id: Deterministic scores keyed by recipe id.
            constraints: Hard constraints to enforce in reranking.
            history: Prior selections for repetition avoidance.

        Returns:
            Payload dictionary for the LLM prompt.
        """
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
        """
        Format the single-slot rerank prompt with a strict JSON-only schema.

        Args:
            payload: Structured payload for a single meal slot.

        Returns:
            Prompt string to send to the LLM.
        """
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

    def _build_batch_prompt(self, payload: List[Dict[str, Any]]) -> str:
        """
        Format the batch rerank prompt with one selection required per entry.

        Args:
            payload: List of structured payloads, one per meal slot.

        Returns:
            Prompt string to send to the LLM.
        """
        payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
        return (
            "You are a meal-plan reranking assistant. You must only choose from the provided candidates.\n"
            "Hard constraints must be honored (dietary restrictions, exclusions, time limits, meal type).\n"
            "Avoid repetition using the provided history when possible.\n\n"
            f"INPUT_JSON:{payload_json}\n\n"
            "Return ONLY a JSON object with this exact schema:\n"
            "{\n"
            '  "selections": [\n'
            "    {\n"
            '      "meal_slot": "<string>",\n'
            '      "selected_id": "<string>",\n'
            '      "backup_id": "<string|null>",\n'
            '      "reasons": ["<short bullet>", "..."],\n'
            '      "confidence": 0.0\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "Rules:\n"
            "- Return one selection per input entry.\n"
            "- selected_id MUST be one of the candidate ids for that entry.\n"
            "- backup_id MUST be one of the candidate ids or null.\n"
            "- reasons: max 4 items, each <= 15 words.\n"
            "- No additional keys. No prose outside JSON."
        )

    def _call_llm(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Call the LLM for a single-slot rerank and parse its JSON response.

        Args:
            prompt: Prompt string formatted for the reranker schema.

        Returns:
            Parsed JSON response or None on failure.
        """
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

    def _call_llm_batch(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Call the LLM for batch reranking and parse its JSON response.

        Args:
            prompt: Prompt string formatted for the batch schema.

        Returns:
            Parsed JSON response or None on failure.
        """
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
            logger.error(f"Reranker batch LLM call failed: {exc}")
            return None

    def _choose_valid_id(self, result: Dict[str, Any], candidate_ids: set) -> Optional[str]:
        """
        Return a valid selected/backup id from the LLM result if present.

        Args:
            result: Parsed LLM response payload.
            candidate_ids: Allowed candidate ids.

        Returns:
            Selected or backup id if valid, otherwise None.
        """
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
        """
        Extract non-empty reason strings from the LLM result.

        Args:
            result: Parsed LLM response payload.

        Returns:
            List of reason strings or None if absent.
        """
        reasons = result.get("reasons")
        if not isinstance(reasons, list):
            return None
        cleaned = [r for r in reasons if isinstance(r, str) and r.strip()]
        return cleaned or None

    def _extract_key_ingredients(self, ingredients: List[str], limit: int = 6) -> List[str]:
        """
        Normalize ingredient names and return a capped list for prompts.

        Args:
            ingredients: Raw ingredient strings.
            limit: Maximum number of ingredients to return.

        Returns:
            Cleaned ingredient names capped by the limit.
        """
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
        """
        Create a stable cache key from the rerank inputs.

        Args:
            query: Original user query string.
            meal_slot: Slot identifier.
            candidate_ids: Candidate recipe ids.
            constraints: Hard constraints applied to reranking.
            history: Prior selections for repetition avoidance.

        Returns:
            Deterministic cache key for the rerank request.
        """
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
        """
        Return a cached result if present and not expired.

        Args:
            key: Cache key to lookup.

        Returns:
            Cached value or None if missing/expired.
        """
        item = self.cache.get(key)
        if not item:
            return None
        if item["expires_at"] < time.time():
            self.cache.pop(key, None)
            return None
        return item["value"]

    def _cache_set(self, key: str, value: Dict[str, Any]) -> None:
        """
        Store a rerank result with an expiration timestamp.

        Args:
            key: Cache key to store.
            value: Parsed LLM response to cache.
        """
        self.cache[key] = {
            "value": value,
            "expires_at": time.time() + self.cache_ttl_seconds
        }


reranker_service = RerankerService()
