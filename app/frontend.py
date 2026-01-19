import streamlit as st
import requests
import json
import os

# Configuration
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/generate-meal-plan")

st.set_page_config(page_title="AI Meal Planner", layout="wide")

col1, col2 = st.columns([1, 4])
with col1:
    st.image("app/static/assets/nutrivo_logo.png", width=150)
with col2:
    st.title("AI-Powered Personal Meal Planner")
st.markdown("""
Welcome! Describe your ideal meal plan, and I'll generate a schedule for you.

**Examples:**
- *3-day vegetarian plan with high protein*
- *7-day gluten-free menu, no nuts*
""")

# Input Section
query = st.text_area("Enter your request:", height=100, placeholder="E.g. Create a 3-day meal plan for a vegan athlete...")

if st.button("Generate Plan", type="primary"):
    if not query:
        st.warning("Please enter a query first.")
    else:
        with st.spinner("Generating your delicious plan..."):
            try:
                response = requests.post(API_URL, json={"query": query})
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # summary section
                    st.success("Plan generated successfully!")
                    
                    # Display AI's interpretation
                    if data.get("clarified_intent"):
                        st.info(f"🤖 **AI Interpretation:** {data['clarified_intent']}")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Meals", data["summary"]["total_meals"])
                    with col2:
                        st.metric("Est. Cost", data["summary"]["estimated_cost"])
                    with col3:
                        st.metric("Avg Prep Time", data["summary"]["avg_prep_time"])
                    
                    if data["summary"]["dietary_compliance"]:
                        st.info(f"**Compliance:** {', '.join(data['summary']['dietary_compliance'])}")

                    # Detailed Plan
                    st.divider()
                    for day in data["meal_plan"]:
                        with st.expander(f"Day {day['day']} - {day['date']}", expanded=True):
                            for meal in day["meals"]:
                                st.markdown(f"### {meal['meal_type'].title()}: {meal['recipe_name']}")
                                st.caption(f"{meal['nutritional_info']['calories']} kcal | Prep: {meal['preparation_time']}")
                                st.write(meal['description'])
                                
                                c1, c2 = st.columns(2)
                                with c1:
                                    st.markdown("**Ingredients**")
                                    for ing in meal['ingredients']:
                                        st.markdown(f"- {ing}")
                                with c2:
                                    st.markdown("**Instructions**")
                                    st.write(meal['instructions'])
                                st.divider()

                    # Raw JSON (for debugging/verification)
                    with st.expander("View Raw JSON Response"):
                        st.json(data)
                        
                else:
                    st.error(f"Error {response.status_code}: {response.text}")
                    
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the API. Is the backend running? (`uvicorn app.main:app`)")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
