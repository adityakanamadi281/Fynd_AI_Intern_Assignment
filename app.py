import streamlit as st
import pandas as pd
from huggingface_hub import InferenceClient, CommitScheduler
from pathlib import Path
import os
import uuid
from datetime import datetime

# --- Configuration ---
# Set up the folder where data will be stored locally before syncing
DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "feedback_log.csv"

# Get configuration from Secrets
HF_TOKEN = os.getenv("HF_API_TOKEN")
REPO_ID = os.getenv("yelp.csv") # Expected format: username/dataset-name

# Initialize the AI Client (using a free, high-quality model)
client = InferenceClient(
    model="mistralai/Mistral-7B-Instruct-v0.3",
    token=HF_TOKEN
)

# Initialize the Scheduler to sync data to Hugging Face Dataset
# This runs in the background and uploads the 'data' folder every 5 minutes
scheduler = CommitScheduler(
    repo_id=REPO_ID,
    repo_type="dataset",
    folder_path=DATA_DIR,
    path_in_repo="data",
    every=5  # Sync every 5 minutes (or immediately on manual trigger if implemented)
)

# --- Helper Functions ---

def load_data():
    """Loads feedback data from the local CSV file."""
    if DATA_FILE.exists():
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=["id", "timestamp", "rating", "review", "ai_response"])

def save_feedback(rating, review, ai_response):
    """Appends new feedback to the CSV file."""
    new_data = pd.DataFrame([{
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rating": rating,
        "review": review,
        "ai_response": ai_response
    }])
    
    # Append to local file
    if DATA_FILE.exists():
        new_data.to_csv(DATA_FILE, mode='a', header=False, index=False)
    else:
        new_data.to_csv(DATA_FILE, mode='w', header=True, index=False)

def get_ai_response(user_review, rating):
    """Generates a polite response to the user."""
    prompt = f"""
    You are a helpful customer service AI. 
    A user just left a {rating}-star review: "{user_review}"
    Write a short, polite, and personalized response to them.
    """
    response = client.text_generation(prompt, max_new_tokens=100, temperature=0.7)
    return response.strip()

def analyze_feedback(df):
    """Generates a summary and recommended actions based on all reviews."""
    if df.empty:
        return "No data to analyze.", "No actions needed."
    
    # Combine recent reviews for context (limit to last 20 to fit context window)
    recent_reviews = "\n".join([f"- {row['rating']} stars: {row['review']}" for index, row in df.tail(20).iterrows()])
    
    prompt = f"""
    Analyze the following customer reviews:
    {recent_reviews}

    Output Format:
    1. SUMMARY: (A brief summary of the main sentiment and issues)
    2. ACTIONS: (3 bullet points of recommended next actions for the admin)
    """
    
    analysis = client.text_generation(prompt, max_new_tokens=500, temperature=0.5)
    
    # Simple parsing (assuming the model follows instructions reasonably well)
    parts = analysis.split("ACTIONS:")
    summary = parts[0].replace("SUMMARY:", "").strip()
    actions = parts[1].strip() if len(parts) > 1 else "Could not parse actions."
    
    return summary, actions

# --- UI Layout ---

st.set_page_config(page_title="AI Feedback System", layout="wide")

# Sidebar for Navigation
dashboard_choice = st.sidebar.radio("Select Dashboard", ["User Dashboard", "Admin Dashboard"])

# --- DASHBOARD A: USER (Public) ---
if dashboard_choice == "User Dashboard":
    st.title("🌟 We Value Your Feedback")
    st.markdown("Please rate your experience and let us know what you think.")

    with st.form("feedback_form"):
        stars = st.slider("Rating", 1, 5, 5)
        review_text = st.text_area("Your Review", placeholder="Tell us what you liked or how we can improve...")
        submitted = st.form_submit_button("Submit Feedback")

        if submitted and review_text:
            with st.spinner("Generating AI Response..."):
                # 1. Generate AI Response
                ai_reply = get_ai_response(review_text, stars)
                
                # 2. Store Data
                save_feedback(stars, review_text, ai_reply)
                
                # 3. Show Success
                st.success("Thank you! Your feedback has been recorded.")
                st.info(f"**AI Agent says:** {ai_reply}")

# --- DASHBOARD B: ADMIN (Internal) ---
elif dashboard_choice == "Admin Dashboard":
    st.title("📊 Feedback Admin Panel")
    
    # Load Data
    df = load_data()
    
    # Key Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Reviews", len(df))
    col2.metric("Average Rating", f"{df['rating'].mean():.2f}" if not df.empty else "N/A")
    col3.metric("Latest Submission", df['timestamp'].iloc[-1] if not df.empty else "N/A")

    st.divider()

    # Live Data Table
    st.subheader("Recent Submissions")
    st.dataframe(df.sort_values(by="timestamp", ascending=False), use_container_width=True)

    st.divider()

    # AI Analysis Section
    st.subheader("🤖 AI Insights")
    if st.button("Generate Summary & Recommendations"):
        if not df.empty:
            with st.spinner("Analyzing all feedback..."):
                summary, actions = analyze_feedback(df)
                
                st.markdown("### 📝 Review Summary")
                st.write(summary)
                
                st.markdown("### 🚀 Recommended Actions")
                st.write(actions)
        else:
            st.warning("No data available to analyze.")