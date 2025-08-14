import requests
import re
import difflib
from datetime import datetime
import dateparser

# 🔐 Replace with your actual Notion credentials
DATABASE_ID = "your_notion_database_id"
headers = {
    "Authorization": "Bearer your_notion_token",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# 🧭 Aliases for natural language course names
COURSE_ALIASES = {
    "precalc": "Precalculus",
    "math": "Precalculus",
    "comp sci": "AP Computer Science",
    "cs": "AP Computer Science",
    "bio": "Biology",
    "hist": "US History",
    "history": "US History",
    "english": "English Literature",
    "lit": "English Literature",
    "gov": "Government",
    "econ": "Economics"
}

# 🧼 Strip leading phrases from course names
def clean_course_name(raw):
    return re.sub(r"^(the\s)?(class|course)\s+", "", raw.strip(), flags=re.IGNORECASE)

# 📅 Parse fuzzy due dates
def parse_due_date(raw):
    parsed = dateparser.parse(raw)
    return parsed.strftime("%Y-%m-%d") if parsed else None

# 🗓️ Stub for calendar integration
def create_calendar_event(name, due_date):
    return "calendar-event-id"

# 🆕 Create a new assignment in Notion
def create_assignment(name, course_id, due_date=None, type_name=None):
    calendar_event_id = create_calendar_event(name, due_date) if due_date else None

    url = "https://api.notion.com/v1/pages"
    properties = {
        "Name": {
            "title": [{
                "type": "text",
                "text": { "content": name }
            }]
        },
        "Course": {
            "relation": [{ "id": course_id }]
        },
        "Status": {
            "status": { "name": "Not started" }
        }
    }

    if calendar_event_id:
        properties["Calendar events"] = {
            "relation": [{ "id": calendar_event_id }]
        }

    if type_name:
        properties["Type"] = {
            "select": { "name": type_name }
        }

    if due_date:
        properties["Due date"] = {
            "date": { "start": due_date }
        }

    payload = {
        "parent": { "database_id": DATABASE_ID },
        "properties": properties
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print(f"✅ Created assignment '{name}' successfully.")
    else:
        print(f"❌ Failed to create assignment: {response.text}")

# ✍️ Update assignment properties
def update_assignment(page_id, updates):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    properties = {}

    for key, value in updates.items():
        if key == "Status":
            properties[key] = { "status": { "name": value } }
        elif key == "Pin":
            properties[key] = { "checkbox": bool(value) }
        elif key == "Due date":
            properties[key] = { "date": { "start": value } }
        else:
            properties[key] = { "rich_text": [{ "text": { "content": str(value) } }] }

    payload = { "properties": properties }
    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code == 200:
        print(f"✅ Updated assignment '{page_id}' successfully.")
    else:
        print(f"❌ Failed to update assignment: {response.text}")

# 🧠 Parse natural language "add" command (fuzzy)
def parse_add_command(command):
    match = re.search(r"(?:add|create|make).*?(?:assignment|quiz|test|project|hw|lab)?(?: called)? (.+?) (?:under|for|in|from|in the class|in course)? (.+?) (?:due|on|by) (.+)", command, re.IGNORECASE)
    if match:
        raw_type = re.search(r"(assignment|quiz|test|project|hw|lab)", command, re.IGNORECASE)
        type_guess = raw_type.group(1).capitalize() if raw_type else "Assignment"
        return {
            "Name": match.group(1).strip(),
            "Course": clean_course_name(match.group(2).strip()),
            "Due date": parse_due_date(match.group(3).strip()),
            "Type": type_guess
        }

    # Fallback loose parser
    fallback = re.search(r"(?:create|make|add)?\s*(?:an|a)?\s*(assignment|quiz|test|project|hw|lab)?\s*(?:called)?\s*(.+?)\s*(?:for|in|under)\s*(.+?)\s*(?:due|on|by)\s*(.+)", command, re.IGNORECASE)
    if fallback:
        type_guess = fallback.group(1) or "Assignment"
        name = fallback.group(2)
        course = clean_course_name(fallback.group(3))
        due = parse_due_date(fallback.group(4))
        return {
            "Name": name.strip(),
            "Course": course.strip(),
            "Due date": due,
            "Type": type_guess.capitalize()
        }

    return {}

# 🧠 Parse status update command (fuzzy)
def parse_status_command(command):
    name_match = re.search(r"(?:mark|set|change|update)\s+(.+?)\s+(?:as|to)\s+(.+)", command, re.IGNORECASE)
    if name_match:
        return {
            "Name": name_match.group(1).strip(),
            "Status": name_match.group(2).strip().capitalize()
        }
    return { "Name": None, "Status": None }

# 🔎 Fuzzy match course name to Notion ID
def find_course_id(course_name):
    normalized = COURSE_ALIASES.get(course_name.lower(), course_name)

    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    response = requests.post(url, headers=headers)
    data = response.json()

    titles = {}
    for result in data.get("results", []):
        props = result["properties"]
        title_prop = props.get("Name", {}).get("title", [])
        if title_prop:
            title = title_prop[0]["text"]["content"].strip()
            titles[title] = result["id"]

    closest = difflib.get_close_matches(normalized, titles.keys(), n=1, cutoff=0.4)
    if closest:
        matched_title = closest[0]
        return titles[matched_title], matched_title

    return None, None

# 🔎 Fuzzy match assignment name to Notion ID
def find_assignment_id_by_name(name):
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    response = requests.post(url, headers=headers)
    data = response.json()

    titles = {}
    for result in data.get("results", []):
        props = result["properties"]
        title = props["Name"]["title"][0]["text"]["content"].strip() if props["Name"]["title"] else ""
        titles[title] = result["id"]

    closest = difflib.get_close_matches(name, titles.keys(), n=1, cutoff=0.4)
    if closest:
        matched_title = closest[0]
        return titles[matched_title], matched_title
    return None, None

# 🔍 Retrieve assignments with optional filters
def get_assignments(filter_by=None, filter_value=None):
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = { "filter": {} }

    if filter_by == "due-today":
        today = datetime.today().strftime("%Y-%m-%d")
        payload["filter"] = {
            "property": "Due date",
            "date": { "equals": today }
        }

    response = requests.post(url, headers=headers, json=payload)
    return response.json()

# 🧪 Debug utility
def print_assignments():
    data = get_assignments()
    for result in data.get("results", []):
        props = result["properties"]
        name = props["Name"]["title"][0]["text"]["content"]
        status = props["Status"]["status"]["name"]
        due = props["Due date"]["date"]["start"] if props.get("Due date") else "No due date"
        print(f"- {name} | {status} | Due: {due}")
