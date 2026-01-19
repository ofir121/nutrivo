# AI-Powered Personalized Meal Planner

A production-ready REST API that generates personalized, multi-day meal plans based on natural language user queries.

## Problem Understanding
The goal is to simplify meal planning by converting natural language requests (e.g., "5-day vegetarian plan") into structured, nutritional meal plans. This solves the "what's for dinner?" problem while catering to specific dietary needs and constraints.

## Architecture Overview
- **Framework**: FastAPI (Python) for high-performance async API capabilities.
- **Service Layer**:
  - `LLMService`: Handles intent extraction from natural language (Note: Currently uses a regex-based POC parser for "days", "calories", and "diet type").
  - `RecipeService`: Manages recipe data retrieval (Currently uses a mockup JSON database).
  - `MealPlanner`: Orchestrates the logic to assemble daily plans ensuring dietary compliance.
- **Data**: Mock recipe database for the POC.

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
   # Edit .env and add API keys if implementing full LLM integration
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
- **Mock Data**: Used for the POC to ensure speed and reliability without external dependencies.
- **Regex Parser**: Implemented a simple parser for the POC to demonstrate functionality without incurring LLM costs immediately. It extracts duration (1-7 days), diet type (vegetarian, vegan, etc.), and exclusions.

## Future Improvements
- **LLM Integration**: Replace regex logic with OpenAI/Anthropic for robust intent understanding.
- **Real Recipe API**: Integrate Spoonacular or Edamam for a vast recipe value.
- **Optimization**: Add constraint satisfaction algorithms (CSP) to better optimize nutrition and variety.
- **User Profiles**: Store user preferences to improve personalization over time.
