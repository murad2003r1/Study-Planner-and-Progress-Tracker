#!/usr/bin/env python3
"""
Study Planner and Progress Tracker
====================================
A command-line application to plan subjects/topics, log study sessions,
track completion progress, and view stats/deadlines.

Data is stored locally in a JSON file (study_data.json) in the same
directory as this script, so your progress persists between runs.

Run:
    python study_planner.py
"""

import json
import os
import sys
from datetime import datetime, date

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "study_data.json")
DATE_FMT = "%Y-%m-%d"


# --------------------------------------------------------------------------- #
# Data layer
# --------------------------------------------------------------------------- #

def load_data():
    """Load study data from disk, or return a fresh structure if none exists."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            print("⚠  Could not read existing data file. Starting fresh.")
    return {"subjects": {}}


def save_data(data):
    """Persist study data to disk."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def next_id(items):
    """Return the next integer id for a dict of items keyed by string ids."""
    if not items:
        return "1"
    return str(max(int(k) for k in items.keys()) + 1)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def prompt(text, allow_empty=False):
    while True:
        val = input(text).strip()
        if val or allow_empty:
            return val
        print("This field can't be empty. Try again.")


def prompt_date(text):
    while True:
        val = input(text).strip()
        if not val:
            return None
        try:
            datetime.strptime(val, DATE_FMT)
            return val
        except ValueError:
            print(f"Please use the format YYYY-MM-DD (e.g. 2026-08-15).")


def prompt_float(text, default=None):
    while True:
        val = input(text).strip()
        if not val and default is not None:
            return default
        try:
            return float(val)
        except ValueError:
            print("Please enter a number.")


def choose_subject(data):
    subjects = data["subjects"]
    if not subjects:
        print("No subjects yet. Add one first (option 1).")
        return None
    print("\nSubjects:")
    for sid, s in subjects.items():
        print(f"  [{sid}] {s['name']}")
    sid = prompt("Choose subject id: ")
    if sid not in subjects:
        print("Invalid subject id.")
        return None
    return sid


def choose_topic(data, sid):
    topics = data["subjects"][sid]["topics"]
    if not topics:
        print("This subject has no topics yet. Add one first.")
        return None
    print(f"\nTopics in '{data['subjects'][sid]['name']}':")
    for tid, t in topics.items():
        status = "✔ done" if t["done"] else "… pending"
        deadline = f" (due {t['deadline']})" if t.get("deadline") else ""
        print(f"  [{tid}] {t['name']} - {status}{deadline}")
    tid = prompt("Choose topic id: ")
    if tid not in topics:
        print("Invalid topic id.")
        return None
    return tid


def progress_bar(pct, width=24):
    filled = int(width * pct / 100)
    return "[" + "#" * filled + "-" * (width - filled) + f"] {pct:5.1f}%"


# --------------------------------------------------------------------------- #
# Core actions
# --------------------------------------------------------------------------- #

def add_subject(data):
    name = prompt("Subject name: ")
    sid = next_id(data["subjects"])
    data["subjects"][sid] = {"name": name, "topics": {}}
    save_data(data)
    print(f"✔ Added subject '{name}' (id {sid}).")


def add_topic(data):
    sid = choose_subject(data)
    if not sid:
        return
    name = prompt("Topic name: ")
    deadline = prompt_date("Deadline (YYYY-MM-DD, optional, press Enter to skip): ")
    tid = next_id(data["subjects"][sid]["topics"])
    data["subjects"][sid]["topics"][tid] = {
        "name": name,
        "done": False,
        "deadline": deadline,
        "hours_logged": 0.0,
        "sessions": [],
    }
    save_data(data)
    print(f"✔ Added topic '{name}' to '{data['subjects'][sid]['name']}'.")


def log_session(data):
    sid = choose_subject(data)
    if not sid:
        return
    tid = choose_topic(data, sid)
    if not tid:
        return
    hours = prompt_float("Hours studied (e.g. 1.5): ")
    note = prompt("Session note (optional): ", allow_empty=True)
    topic = data["subjects"][sid]["topics"][tid]
    topic["hours_logged"] += hours
    topic["sessions"].append(
        {"date": date.today().strftime(DATE_FMT), "hours": hours, "note": note}
    )
    save_data(data)
    print(f"✔ Logged {hours}h on '{topic['name']}'. Total: {topic['hours_logged']:.1f}h")


def mark_topic_done(data):
    sid = choose_subject(data)
    if not sid:
        return
    tid = choose_topic(data, sid)
    if not tid:
        return
    topic = data["subjects"][sid]["topics"][tid]
    topic["done"] = not topic["done"]
    save_data(data)
    state = "complete" if topic["done"] else "pending"
    print(f"✔ '{topic['name']}' marked as {state}.")


def view_progress(data):
    subjects = data["subjects"]
    if not subjects:
        print("No subjects yet.")
        return
    print("\n===== PROGRESS REPORT =====")
    total_topics = 0
    total_done = 0
    total_hours = 0.0
    for s in subjects.values():
        topics = s["topics"]
        n = len(topics)
        done = sum(1 for t in topics.values() if t["done"])
        hours = sum(t["hours_logged"] for t in topics.values())
        pct = (done / n * 100) if n else 0.0
        total_topics += n
        total_done += done
        total_hours += hours
        print(f"\n{s['name']}  ({done}/{n} topics complete, {hours:.1f}h logged)")
        print("  " + progress_bar(pct))
        for t in topics.values():
            mark = "✔" if t["done"] else " "
            deadline = f"  due {t['deadline']}" if t.get("deadline") else ""
            print(f"    [{mark}] {t['name']} - {t['hours_logged']:.1f}h{deadline}")
    overall = (total_done / total_topics * 100) if total_topics else 0.0
    print("\n----------------------------")
    print(f"Overall: {total_done}/{total_topics} topics complete, {total_hours:.1f}h total")
    print("  " + progress_bar(overall))


def view_upcoming_deadlines(data):
    entries = []
    for s in data["subjects"].values():
        for t in s["topics"].values():
            if t.get("deadline") and not t["done"]:
                entries.append((t["deadline"], s["name"], t["name"]))
    if not entries:
        print("No upcoming deadlines for pending topics.")
        return
    entries.sort(key=lambda e: e[0])
    today = date.today()
    print("\n===== UPCOMING DEADLINES =====")
    for deadline, subj, topic in entries:
        due = datetime.strptime(deadline, DATE_FMT).date()
        days_left = (due - today).days
        flag = " ⚠ OVERDUE" if days_left < 0 else (" ⏰ due today" if days_left == 0 else "")
        print(f"  {deadline} ({days_left:+d}d) - {subj} / {topic}{flag}")


def delete_subject(data):
    sid = choose_subject(data)
    if not sid:
        return
    name = data["subjects"][sid]["name"]
    confirm = prompt(f"Type 'yes' to delete subject '{name}' and all its topics: ")
    if confirm.lower() == "yes":
        del data["subjects"][sid]
        save_data(data)
        print(f"✔ Deleted subject '{name}'.")
    else:
        print("Cancelled.")


# --------------------------------------------------------------------------- #
# Menu
# --------------------------------------------------------------------------- #

MENU = """
========== STUDY PLANNER & PROGRESS TRACKER ==========
 1. Add subject
 2. Add topic to a subject
 3. Log a study session
 4. Mark topic done / not done
 5. View progress report
 6. View upcoming deadlines
 7. Delete a subject
 0. Exit
========================================================
"""


def main():
    data = load_data()
    print("Welcome to your Study Planner! Data file:", DATA_FILE)
    while True:
        print(MENU)
        choice = input("Choose an option: ").strip()
        try:
            if choice == "1":
                add_subject(data)
            elif choice == "2":
                add_topic(data)
            elif choice == "3":
                log_session(data)
            elif choice == "4":
                mark_topic_done(data)
            elif choice == "5":
                view_progress(data)
            elif choice == "6":
                view_upcoming_deadlines(data)
            elif choice == "7":
                delete_subject(data)
            elif choice == "0":
                print("Happy studying! 👋")
                sys.exit(0)
            else:
                print("Invalid option, please choose again.")
        except KeyboardInterrupt:
            print("\nInterrupted. Exiting.")
            sys.exit(0)


if __name__ == "__main__":
    main()
