# This is the beginning of the Streamlit admin dashboard code

import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime

# --- CONFIGURATION ---
DEFAULT_API = "http://localhost:5000"
DATA_FILE = "user_reviews.csv"


def fetch_via_api(base_url: str):
	try:
		resp = requests.get(f"{base_url.rstrip('/')}/reviews", timeout=5)
		resp.raise_for_status()
		return resp.json()
	except Exception:
		return None


def call_api_add(base_url: str, payload: dict):
	resp = requests.post(f"{base_url.rstrip('/')}/reviews", json=payload, timeout=5)
	resp.raise_for_status()
	return resp.json()


def call_api_update(base_url: str, idx: int, payload: dict):
	resp = requests.put(f"{base_url.rstrip('/')}/reviews/{idx}", json=payload, timeout=5)
	resp.raise_for_status()
	return resp.json()


def call_api_delete(base_url: str, idx: int):
	resp = requests.delete(f"{base_url.rstrip('/')}/reviews/{idx}", timeout=5)
	resp.raise_for_status()
	return resp.json()


def read_local():
	if not os.path.exists(DATA_FILE):
		return pd.DataFrame(columns=["timestamp", "rating", "review", "ai_response"]).to_dict(orient="records")
	df = pd.read_csv(DATA_FILE)
	records = df.to_dict(orient="records")
	for i, r in enumerate(records):
		r["id"] = i
	return records


def write_local(df: pd.DataFrame):
	tmp = DATA_FILE + ".tmp"
	df.to_csv(tmp, index=False)
	os.replace(tmp, DATA_FILE)


st.set_page_config(page_title="Admin Dashboard", page_icon="🔧")

st.title("🔧 Admin Dashboard")

st.markdown("Use this dashboard to view and manage user reviews stored in `user_reviews.csv`.\n\nYou can run the optional API server with `python app.py` and set the API base URL below.")

api_base = st.text_input("API base URL (optional)", value=DEFAULT_API)

col1, col2 = st.columns([1, 3])
with col1:
	if st.button("Load Reviews"):
		st.session_state["loaded"] = True

with col2:
	st.write("Current data source:")
	st.caption("API fallback to local file if API unreachable")

if "loaded" not in st.session_state:
	st.session_state["loaded"] = False

if st.session_state["loaded"]:
	records = fetch_via_api(api_base) or read_local()
	df = pd.DataFrame(records)
	if df.empty:
		st.info("No reviews found yet.")
	else:
		# display table with id column first
		display_df = df.copy()
		if "id" in display_df.columns:
			display_df = display_df.set_index("id")
		st.dataframe(display_df)

		st.markdown("---")
		st.subheader("Edit / Delete a review")
		idx_options = list(map(int, df["id"].tolist()))
		selected_id = st.selectbox("Select review id to manage", options=idx_options)

		selected_row = df[df["id"] == selected_id].iloc[0].to_dict()

		edit_rating = st.number_input("Rating (1-5)", min_value=0, max_value=5, value=int(selected_row.get("rating") or 0))
		edit_review = st.text_area("Review text", value=str(selected_row.get("review") or ""))
		edit_ai = st.text_area("AI Response", value=str(selected_row.get("ai_response") or ""))

		c1, c2 = st.columns(2)
		with c1:
			if st.button("Update Review"):
				payload = {"rating": int(edit_rating), "review": edit_review, "ai_response": edit_ai}
				try:
					result = None
					try:
						result = call_api_update(api_base, int(selected_id), payload)
						st.success(f"Updated via API (id={selected_id})")
					except Exception:
						# fallback local
						local_df = pd.DataFrame(records).drop(columns=["id"]) if "id" in df.columns else pd.DataFrame(records)
						for k in ["rating", "review", "ai_response"]:
							local_df.at[int(selected_id), k] = payload.get(k)
						write_local(local_df)
						st.success(f"Updated local CSV (id={selected_id})")
				except Exception as e:
					st.error(f"Failed to update: {e}")

		with c2:
			if st.button("Delete Review"):
				try:
					try:
						call_api_delete(api_base, int(selected_id))
						st.success(f"Deleted via API (id={selected_id})")
					except Exception:
						local_df = pd.DataFrame(records).drop(columns=["id"]) if "id" in df.columns else pd.DataFrame(records)
						local_df = local_df.drop(local_df.index[int(selected_id)]).reset_index(drop=True)
						write_local(local_df)
						st.success(f"Deleted locally (id={selected_id})")
				except Exception as e:
					st.error(f"Failed to delete: {e}")

		st.markdown("---")

	st.subheader("Add a new review")
	new_rating = st.number_input("Rating (1-5)", min_value=0, max_value=5, value=5, key="new_rating")
	new_review = st.text_area("Review text", key="new_review")
	new_ai = st.text_area("AI response (optional)", key="new_ai")

	if st.button("Add Review"):
		payload = {
			"rating": int(new_rating),
			"review": new_review,
			"ai_response": new_ai,
			"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
		}
		try:
			try:
				call_api_add(api_base, payload)
				st.success("Added review via API")
			except Exception:
				# local append
				local = read_local()
				local_df = pd.DataFrame(local).drop(columns=["id"]) if local and "id" in local[0] else pd.DataFrame(local)
				local_df = pd.concat([local_df, pd.DataFrame([payload])], ignore_index=True)
				write_local(local_df)
				st.success("Added review to local CSV")
		except Exception as e:
			st.error(f"Failed to add review: {e}")

	st.caption("Tip: Start the API server with `python app.py` to use the API instead of direct file edits.")

