import json
import os

FILE = "submissions.json"

def load_submissions():
    if not os.path.exists(FILE):
        return []
    with open(FILE, "r") as f:
        return json.load(f)

def save_submission(submission):
    submissions = load_submissions()
    submissions.append(submission)
    with open(FILE, "w") as f:
        json.dump(submissions, f, indent=4)
