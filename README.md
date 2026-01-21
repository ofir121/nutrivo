# AI-Powered Personalized Meal Planner

A production-ready REST API that generates personalized, multi-day meal plans based on natural language user queries.

## Problem Understanding
The goal is to simplify meal planning by converting natural language requests (e.g., "5-day vegetarian plan") into structured, nutritional meal plans. This solves the "what's for dinner?" problem while catering to specific dietary needs and constraints.

## Architecture Overview
- **Framework**: FastAPI (Python) for high-performance async API capabilities.
- **Service Layer**:
  - `LLMService`: Optional LLM enhancement for ambiguous queries and batch time estimation.
  - `RecipeService`: Aggregates recipes from TheMealDB API and a local mock database.
  - `MealPlanner`: Orchestrates the logic to assemble daily plans with deterministic scoring and greedy selection.
- **Data**: Hybrid approach using external API (MealDB) and local JSON.

## Setup & Installation

### Prerequisites
- Python 3.9+
- pip

### Steps
1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd nutrivo
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure Environment:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```
   Optional:
   - Add `USDA_API_KEY` to enable nutrition enrichment from USDA FoodData Central.

## Running the Application

### Quick Start (Recommended)
Run both the backend and frontend simultaneously with a single command:
```bash
python run.py
```
This script will start the FastAPI backend (port 8000) and the Streamlit frontend (port 8501).

### Manual Setup
If you prefer to run services separately:

#### 1. Start the Backend
Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

#### 2. Start the Frontend
In a new terminal window, start the Streamlit app:
```bash
streamlit run app/frontend.py
```
The UI will open in your browser at `http://localhost:8501`.
## API Documentation
Interactive documentation (Swagger UI) is available at:
`http://127.0.0.1:8000/docs`

### Sample Request
**POST** `/api/generate-meal-plan`
```json
{
  "query": "Create a 3-day vegetarian meal plan"
}
```

### Optional Extensions
The API supports a few optional extensions for demos:
- `sources`: array of recipe sources to use (e.g., `["Local", "TheMealDB"]`)


### Duration Limits
Meal plans are limited to 1-7 days. Requests for more than 7 days return a 400 error with guidance to request 7 days or fewer.

## Design Decisions & Trade-offs
- **FastAPI**: Chosen for speed and built-in validation (Pydantic).
- **Hybrid Recipe Sourcing**: Combines a local mock database for speed/reliability with TheMealDB for variety.
- **Hybrid Parsing**: Uses a lightweight regex parser for speed and rule-based preferences, with conditional LLM enrichment only for ambiguous queries.
- **Planner Flow**: Parser (rules + conditional LLM) -> conflict resolver -> retrieve -> score -> greedy plan -> response.
- **LLM Usage Policy**: Default is 0 calls for typical queries; the parser only calls the LLM when the query is ambiguous.
- **Nutrition Enrichment**: When `USDA_API_KEY` is set, local recipes are enriched using USDA FoodData Central.

## Limitations
- **Nutrition accuracy**: TheMealDB does not provide nutrition; values are placeholders for demo purposes.
- **External filtering**: TheMealDB has limited filtering, so diet compliance is best-effort for that source.
- **LLM optionality**: If `OPENAI_API_KEY` is missing, parsing falls back to rules-only extraction.
- **In-memory safeguards**: Rate limiting and caching are in-memory only; they reset on restart and are per-process.
- **USDA matching**: Ingredient matching is heuristic and may be approximate.

## Cost/Usage Notes
- LLM usage is optional and only triggered for ambiguous queries.
- Local recipes are preferred by default; external calls are limited and cached.
- USDA lookups are cached locally in `data/usda_cache.json`.

## Future Improvements
- **LLM Integration**: Further enhance LLM usage for more complex reasoning.
- **Optimization**: Add constraint satisfaction algorithms (CSP) to better optimize nutrition and variety.
- **User Profiles**: Store user preferences to improve personalization over time.
