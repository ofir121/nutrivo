import streamlit as st
import requests
import json
import os

# Configuration
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/generate-meal-plan")
API_DOCS_URL = os.getenv("API_DOCS_URL", "http://127.0.0.1:8000/docs")

st.set_page_config(page_title="AI Meal Planner", layout="wide")

col1, col2, col3 = st.columns([1, 4, 1])
with col1:
    st.image("app/static/assets/nutrivo_logo.png", width=150)
with col2:
    st.title("AI-Powered Personal Meal Planner")
with col3:
    st.link_button("API Docs", API_DOCS_URL, type="secondary", use_container_width=True)
st.markdown("""
Welcome! Describe your ideal meal plan, and I'll generate a schedule for you.

**Examples:**
- *3-day vegetarian plan with high protein*
- *7-day gluten-free menu, no nuts*
""")

# Input Section
query = st.text_area("Enter your request:", height=100, placeholder="E.g. Create a 3-day meal plan for a vegan athlete...")
sources = st.multiselect(
    "Select Recipe Sources",
    ["Local", "TheMealDB"],
    default=["Local"]
)

if st.button("Generate Plan", type="primary"):
    if not query:
        st.warning("Please enter a query first.")
    else:
        with st.spinner("Generating your delicious plan..."):
            try:
                response = requests.post(API_URL, json={
                    "query": query,
                    "sources": sources
                })
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # summary section
                    st.success("Plan generated successfully!")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Meals", data["summary"]["total_meals"])
                    with col2:
                        st.metric("Est. Cost", data["summary"]["estimated_cost"])
                    with col3:
                        st.metric("Avg Prep Time", data["summary"]["avg_prep_time"])
                    
                    # Display Dietary Compliance
                    if data["summary"].get("dietary_compliance"):
                        compliance_html = " ".join([
                            f'<span style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); '
                            f'color: white; padding: 4px 12px; border-radius: 20px; margin-right: 8px; '
                            f'font-size: 0.9em; font-weight: 500;">{item}</span>'
                            for item in data["summary"]["dietary_compliance"]
                        ])
                        st.markdown(f"**🥗 Dietary Compliance:** {compliance_html}", unsafe_allow_html=True)

                    # Detailed Plan
                    st.divider()
                    for day in data["meal_plan"]:
                        with st.expander(f"Day {day['day']} - {day['date']}", expanded=True):
                            for meal in day["meals"]:
                                st.markdown(f"### {meal['meal_type'].title()}: {meal['recipe_name']}")
                                nutrition = meal.get("nutritional_info", {})
                                protein = nutrition.get("protein", 0)
                                carbs = nutrition.get("carbs", 0)
                                fat = nutrition.get("fat", 0)
                                macro_total = protein + carbs + fat
                                if macro_total > 0:
                                    protein_pct = round((protein / macro_total) * 100)
                                    carbs_pct = round((carbs / macro_total) * 100)
                                    fat_pct = round((fat / macro_total) * 100)
                                else:
                                    protein_pct = carbs_pct = fat_pct = 0
                                st.caption(
                                    f"{nutrition.get('calories', 0)} kcal | Prep: {meal['preparation_time']} | "
                                    f"Protein {protein}g ({protein_pct}%), "
                                    f"Carbs {carbs}g ({carbs_pct}%), "
                                    f"Fat {fat}g ({fat_pct}%)"
                                )
                                st.write(meal['description'])
                                
                                c1, c2 = st.columns(2)
                                with c1:
                                    st.markdown("**Ingredients**")
                                    for ing in meal['ingredients']:
                                        st.markdown(f"- {ing}")
                                with c2:
                                    st.markdown("**Instructions**")
                                    instructions = meal.get("instructions", "")
                                    if isinstance(instructions, list):
                                        steps = instructions
                                    else:
                                        steps = [s for s in instructions.split("\n") if s]
                                    for i, step in enumerate(steps, 1):
                                        st.markdown(f"{i}. {step}")
                                st.divider()

                    # Collapsible JSON Response Viewer
                    st.divider()
                    with st.expander("📋 Raw JSON Response", expanded=False):
                        st.json(data)
                        
                else:
                    st.error(f"Error {response.status_code}: {response.text}")
                    
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the API. Is the backend running? (`uvicorn app.main:app`)")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
