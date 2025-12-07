import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime

# --- CONFIGURATION ---
DATA_FILE = "user_reviews.csv"

# --- BACKEND FUNCTIONS ---

def generate_ai_response(rating, review_text):
    """
    Simulates an AI response based on the sentiment of the rating.
    Replace this logic with an actual API call (e.g., OpenAI, Gemini) later.
    """
    time.sleep(1.5) # Simulate processing delay
    
    if not review_text:
        return "Thank you for the rating!"

    if rating >= 4:
        return f"We are thrilled to hear that! Thank you for the {rating}-star feedback. We're glad you enjoyed: '{review_text[:30]}...'"
    elif rating == 3:
        return "Thank you for your balanced feedback. We are constantly trying to improve to turn that 3 stars into 5."
    else:
        return "We apologize that your experience wasn't up to standard. Your feedback regarding this issue has been logged for our support team."

def save_to_csv(rating, review_text, ai_response):
    """Saves the data to a local CSV file."""
    new_data = {
        "timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "rating": [rating],
        "review": [review_text],
        "ai_response": [ai_response]
    }
    df = pd.DataFrame(new_data)
    
    # If file doesn't exist, create it with headers. If it does, append without headers.
    if not os.path.exists(DATA_FILE):
        df.to_csv(DATA_FILE, index=False)
    else:
        df.to_csv(DATA_FILE, mode='a', header=False, index=False)

# --- FRONTEND (USER DASHBOARD) ---

st.set_page_config(page_title="Customer Feedback", page_icon="⭐")

st.markdown("## ⭐ Rate Your Experience")
st.write("Please let us know how we did today.")

with st.container(border=True):
    # 1. Star Rating Input (Streamlit's native feedback component)
    sentiment_mapping = ["one", "two", "three", "four", "five"]
    selected_stars = st.feedback("stars")
    
    # Convert index (0-4) to star count (1-5)
    if selected_stars is not None:
        rating_value = selected_stars + 1
        st.caption(f"You selected {rating_value} star(s).")
    else:
        rating_value = 0

    # 2. Text Input
    review_text = st.text_area("Write a short review (optional):", placeholder="Tell us what you liked or disliked...")

    # 3. Submit Button
    submit_btn = st.button("Submit Feedback", type="primary", use_container_width=True)

    if submit_btn:
        if rating_value == 0:
            st.warning("Please select a star rating before submitting.")
        else:
            with st.spinner("Generating AI Response..."):
                # A. Generate AI Response
                ai_reply = generate_ai_response(rating_value, review_text)
                
                # B. Store Data
                save_to_csv(rating_value, review_text, ai_reply)
            
            # C. Display Result
            st.success("Feedback submitted successfully!")
            
            st.markdown("### 🤖 AI Response:")
            st.info(ai_reply)