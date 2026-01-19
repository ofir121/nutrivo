# AI-Powered Personalized Meal Planner

A production-ready REST API that generates personalized, multi-day meal plans based on natural language user queries.

## Problem Understanding
The goal is to simplify meal planning by converting natural language requests (e.g., "5-day vegetarian plan") into structured, nutritional meal plans. This solves the "what's for dinner?" problem while catering to specific dietary needs and constraints.

## Architecture Overview
- **Framework**: FastAPI (Python) for high-performance async API capabilities.
- **Service Layer**:
  - `LLMService`: Uses GPT-4o-mini for robust intent extraction and recipe instruction formatting.
  - `RecipeService`: Aggregates recipes from TheMealDB API and a local mock database.
  - `MealPlanner`: Orchestrates the logic to assemble daily plans, ensuring dietary compliance and variety.
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

## Running the Application

This application consists of two parts: the Backend API and the Frontend UI.

### 1. Start the Backend
Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

### 2. Start the Frontend
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

## Design Decisions & Trade-offs
- **FastAPI**: Chosen for speed and built-in validation (Pydantic).
- **Hybrid Recipe Sourcing**: Combines a local mock database for speed/reliability with TheMealDB for variety.
- **Hybrid Parsing**: Uses a lightweight regex parser for speed, enriched by an LLM (GPT-4o-mini) for deep understanding of complex intents and instruction formatting.

## Future Improvements
- **LLM Integration**: Replace regex logic with OpenAI/Anthropic for robust intent understanding.
- **Real Recipe API**: Integrate Spoonacular or Edamam for a vast recipe value.
- **Optimization**: Add constraint satisfaction algorithms (CSP) to better optimize nutrition and variety.
- **User Profiles**: Store user preferences to improve personalization over time.
