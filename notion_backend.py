import requests
import os
import re
import dateparser
from dotenv import load_dotenv
import parsedatetime
import difflib
import os
NOTION_TOKEN = os.getenv("NOTION_TOKEN")

# Database IDs
DATABASE_ID = "24a4b8e1c69181ff97d3ec2aa0d205b3"  # Assignments
COURSES_DB_ID = "24a4b8e1-c691-81ae-bbb3-d4449d8dc0df"  # Courses
CALENDAR_DB_ID = "24a4b8e1-c691-81d9-9c50-f73d5a52a8cb"  # Calendar events

# Headers for Notion API
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28"
}

# Retrieve database schema
schema_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}"
schema_response = requests.get(schema_url, headers=headers)
print("Loaded token:", NOTION_TOKEN)
print(schema_response.json())

# Schema map for Assignments database
assignments_schema = {
    "Name": {"type": "title", "editable": True},
    "Pin": {"type": "checkbox", "editable": True},
    "Type": {"type": "select", "editable": True},
    "Status": {"type": "status", "editable": True},
    "Course": {"type": "relation", "editable": True, "related_db_id": COURSES_DB_ID},
    "Tasks": {"type": "relation", "editable": True, "related_db_id": "24a4b8e1-c691-8119-a762-f39799e480cb"},
    "Class notes": {"type": "relation", "editable": True, "related_db_id": "24a4b8e1-c691-8168-af23-e1e3def16224"},
    "Calendar events": {"type": "relation", "editable": True, "related_db_id": CALENDAR_DB_ID},
    "Due date": {"type": "rollup", "editable": False},
    "Due date/time": {"type": "formula", "editable": False},
    "Countdown": {"type": "formula", "editable": False},
    "due-today": {"type": "formula", "editable": False},
    "due-this-week": {"type": "formula", "editable": False},
    "overdue": {"type": "formula", "editable": False},
    "Attachments": {"type": "files", "editable": True}
}

print("\nSchema Map:")
for key, value in assignments_schema.items():
    print(f"- {key}: {value}")

# Function to query and filter assignments
def get_assignments(filter_by=None, filter_value=None):
    query_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {}

    if filter_by and filter_value is not None:
        prop_type = assignments_schema[filter_by]["type"]
        if prop_type == "checkbox":
            payload["filter"] = {
                "property": filter_by,
                "checkbox": {"equals": filter_value}
            }
        elif prop_type == "select":
            payload["filter"] = {
                "property": filter_by,
                "select": {"equals": filter_value}
            }
        elif prop_type == "status":
            payload["filter"] = {
                "property": filter_by,
                "status": {"equals": filter_value}
            }

    response = requests.post(query_url, headers=headers, json=payload)
    data = response.json()

    print(f"\n📋 Assignments matching {filter_by} = {filter_value}:\n")

    for result in data.get("results", []):
        props = result["properties"]
        title = props["Name"]["title"][0]["text"]["content"] if props["Name"]["title"] else "Untitled"
        status = props["Status"]["status"]["name"] if props.get("Status") and props["Status"].get("status") else "Unknown"
        type_ = props["Type"]["select"]["name"] if props.get("Type") and props["Type"].get("select") else "Unspecified"
        page_id = result["id"]
        print(f"- {title} | Type: {type_} | Status: {status} | Page ID: {page_id}")

# Function to update an assignment
def update_assignment(page_id, updates):
    url = f"https://api.notion.com/v1/pages/{page_id}"

    properties = {}
    for key, value in updates.items():
        prop_type = assignments_schema[key]["type"]

        if prop_type == "status":
            properties[key] = {"status": {"name": value}}
        elif prop_type == "select":
            properties[key] = {"select": {"name": value}}
        elif prop_type == "checkbox":
            properties[key] = {"checkbox": value}
        elif prop_type == "title":
            properties[key] = {
                "title": [{"type": "text", "text": {"content": value}}]
            }

    payload = {"properties": properties}
    response = requests.patch(url, headers=headers, json=payload)

    if response.status_code == 200:
        print(f"✅ Updated assignment {page_id} successfully.")
    else:
        print(f"❌ Failed to update {page_id}: {response.text}")

# Function to parse natural language add command
def parse_add_command(message):
    import re
    from datetime import datetime, timedelta

    COURSE_ALIASES = {
        "precalc": "Precalculus",
        "math": "Precalculus",
        "comp sci": "AP Computer Science",
        "cs": "AP Computer Science",
        "bio": "Biology",
        "chem": "Chemistry",
        "spanish": "Spanish",
        "history": "US History",
        "us history": "US History"
    }

    TYPE_KEYWORDS = ["quiz", "test", "project", "essay", "homework", "assignment"]
    parsed = {"Name": None, "Course": None, "Due date": None, "Type": None}

    tokens = message.lower().split()

    # Type detection
    for word in tokens:
        if word in TYPE_KEYWORDS:
            parsed["Type"] = word.capitalize()
            break

    # Course detection
    for word in tokens:
        if word in COURSE_ALIASES:
            parsed["Course"] = COURSE_ALIASES[word]
            break

    # Due date detection
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    today = datetime.today()
    for i, word in enumerate(tokens):
        if word in weekdays:
            days_ahead = (weekdays.index(word) - today.weekday()) % 7
            due_date = today + timedelta(days=days_ahead)
            parsed["Due date"] = due_date.strftime("%Y-%m-%d")
            break

    # Name fallback
    parsed["Name"] = f"{parsed['Course']} {parsed['Type']}" if parsed["Course"] and parsed["Type"] else "Untitled Assignment"

    return parsed

# Find course ID by name
def find_course_id(course_name):
    import difflib

    url = f"https://api.notion.com/v1/databases/{COURSES_DB_ID}/query"
    response = requests.post(url, headers=headers)
    data = response.json()

    titles = {}
    for result in data.get("results", []):
        props = result["properties"]
        for key, value in props.items():
            if value["type"] == "title":
                title_text = value["title"][0]["text"]["content"].strip() if value["title"] else ""
                titles[title_text] = result["id"]

    closest = difflib.get_close_matches(course_name, titles.keys(), n=1, cutoff=0.4)
    if closest:
        matched_title = closest[0]
        return titles[matched_title], matched_title
    return None, None


def create_calendar_event(name, date_string):
    import datetime
    cal = parsedatetime.Calendar()
    time_struct, parse_status = cal.parse(date_string)

    if parse_status == 0:
        print(f"❌ Could not parse date: {date_string}")
        return None

    parsed_date = datetime.datetime(*time_struct[:6])
    iso_date = parsed_date.date().isoformat()

    url = "https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": CALENDAR_DB_ID},
        "properties": {
            "Name": {
                "title": [{"type": "text", "text": {"content": name}}]
            },
            "Due date": {
                "date": {"start": iso_date}
            }
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        event_id = response.json()["id"]
        print(f"✅ Created calendar event for '{name}' on {iso_date}")
        return event_id
    else:
        print(f"❌ Failed to create calendar event: {response.text}")
        return None
# Create assignment and link to course + calendar event
def create_assignment(name, course_id, due_date=None, type_name=None):
    calendar_event_id = create_calendar_event(name, due_date) if due_date else None

    url = "https://api.notion.com/v1/pages"
    properties = {
        "Name": {
            "title": [{"type": "text", "text": {"content": name}}]
        },
        "Course": {
            "relation": [{"id": course_id}]
        },
        "Status": {
            "status": {"name": "Not started"}
        }
    }

    if calendar_event_id:
        properties["Calendar events"] = {
            "relation": [{"id": calendar_event_id}]
        }
    if type_name:
        properties["Type"] = {
            "select": {"name": type_name}
        }
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": properties
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print(f"✅ Created assignment '{name}' successfully.")
    else:
        print(f"❌ Failed to create assignment: {response.text}")

# 🔍 Query assignments due today
get_assignments(filter_by="due-today", filter_value=True)

# ✍️ Update one assignment manually
update_assignment("24d4b8e1-c691-8081-aad9-f08913013c50", {"Status": "Completed", "Pin": True})

# 🧠 Add assignment via natural language
command = "Add an assignment called Essay 1 under the class US History due August 20"
parsed = parse_add_command(command)
print("\n🧠 Parsed Command:")
print(parsed)

course_id = find_course_id(parsed["Course"])
if course_id:
    create_assignment(parsed["Name"], course_id, parsed["Due date"])
else:
    print(f"❌ Could not find course named '{parsed['Course']}'")
def parse_status_command(command):
    name_match = re.search(r"(?:mark|set|change) (.+?) (?:as|to)", command)
    status_match = re.search(r"(?:as|to) (.+)", command)

    return {
        "Name": name_match.group(1).strip() if name_match else None,
        "Status": status_match.group(1).strip().capitalize() if status_match else None
    }
def find_assignment_id_by_name(name):
    import difflib

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
COURSE_ALIASES = {
    "precalc": "Precalculus",
    "math": "Precalculus",
    "comp sci": "AP Computer Science",
    "bio": "Biology",
    "hist": "US History"
}

