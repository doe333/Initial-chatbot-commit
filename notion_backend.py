import re
from difflib import get_close_matches
from datetime import datetime, timedelta

# Simulated Notion database (replace with actual API calls)
notion_courses = ["Biology", "US History", "Precalculus", "AP Computer Science", "Government"]
notion_assignments = {
    "Essay 1": {"course": "US History", "status": "Not Started"},
    "Math Review": {"course": "Precalculus", "status": "Not Started"},
    "Cell Structure": {"course": "Biology", "status": "Not Started"},
    "Chapter 3": {"course": "AP Computer Science", "status": "Not Started"},
    "Midterm": {"course": "Government", "status": "Not Started"},
}

# 🔧 Normalize course names
def normalize_course_name(name):
    name = name.lower().strip()
    mapping = {
        "bio": "Biology",
        "us history": "US History",
        "precalc": "Precalculus",
        "comp sci": "AP Computer Science",
        "gov": "Government",
    }
    return mapping.get(name, name.title())

# 🔧 Fuzzy match course names
def fuzzy_match_course(input_name, course_list):
    normalized = normalize_course_name(input_name)
    matches = get_close_matches(normalized.lower(), [c.lower() for c in course_list], n=1, cutoff=0.6)
    return matches[0].title() if matches else None

# 🔧 Clean assignment name
def clean_name(raw):
    return re.sub(r"^(an?|the)?\s*(assignment|quiz|test|project|hw|lab)?\s*(called)?\s*", "", raw.strip(), flags=re.IGNORECASE)

# 🔧 Parse due date
def parse_due_date(text):
    today = datetime.today()
    text = text.lower().strip()

    if "tomorrow" in text:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    if "next monday" in text:
        days_ahead = (7 - today.weekday() + 0) % 7 or 7
        return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    if "friday" in text:
        days_ahead = (4 - today.weekday()) % 7 or 7
        return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    if "in" in text and "days" in text:
        match = re.search(r"in (\d+) days", text)
        if match:
            return (today + timedelta(days=int(match.group(1)))).strftime("%Y-%m-%d")
    try:
        return datetime.strptime(text, "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        return None

# 🧠 Parse add command
def parse_add_command(command):
    pattern = r"(?:add|create|make)\s+(?:an?|the)?\s*(assignment|quiz|test|project|hw|lab)?\s*(?:called)?\s*(.*?)\s+(?:for|in|on)?\s*(.*?)\s*(?:due\s+(.*))?"
    match = re.search(pattern, command, re.IGNORECASE)

    if match:
        raw_type = match.group(1) or "Assignment"
        raw_name = match.group(2)
        raw_course = match.group(3)
        raw_due = match.group(4)

        parsed = {
            "Type": raw_type.title(),
            "Name": clean_name(raw_name),
            "Course": fuzzy_match_course(raw_course, notion_courses),
            "Due date": parse_due_date(raw_due) if raw_due else None,
        }

        print("🧠 Parsed Add Command:")
        print(parsed)
        print("Normalized course:", normalize_course_name(raw_course))
        if not parsed["Course"]:
            print(f"❌ Could not find course named '{raw_course}'")
        return parsed

    print("🤔 Sorry, I didn't understand that command. Try something like:")
    print("- 'Add a quiz called Chapter 3 for bio due next Friday'")
    print("- 'Make a test called Midterm for gov due in 3 days'")
    return None

# 🧠 Parse status command
def parse_status_command(command):
    pattern = r"(?:mark|set)\s+(.*?)\s+(?:as|to)\s+(done|completed|finished)"
    match = re.search(pattern, command, re.IGNORECASE)

    if match:
        raw_name = match.group(1)
        status = match.group(2).title()

        cleaned_name = clean_name(raw_name)
        matched = get_close_matches(cleaned_name.lower(), [k.lower() for k in notion_assignments.keys()], n=1, cutoff=0.6)
        matched_name = matched[0] if matched else None

        parsed = {
            "Name": matched_name,
            "Status": status,
        }

        print("🧠 Parsed Status Command:")
        print(parsed)
        if not matched_name:
            print(f"❌ Could not find assignment named '{raw_name}'")
        return parsed

    print("🤔 Sorry, I didn't understand that command. Try something like:")
    print("- 'Mark Essay 1 as completed'")
    print("- 'Set Math Review to done'")
    return None

# ✅ Simulated update function
def update_assignment_status(name, status):
    if name in notion_assignments:
        notion_assignments[name]["status"] = status
        print(f"✅ Updated '{name}' to status '{status}'")
    else:
        print(f"❌ Assignment '{name}' not found")

# ✅ Simulated add function
def add_assignment(parsed):
    if parsed["Course"] and parsed["Name"]:
        print(f"✅ Added {parsed['Type']} '{parsed['Name']}' for course '{parsed['Course']}' due {parsed['Due date']}")
    else:
        print(f"❌ Failed to add assignment. Missing course or name.")

