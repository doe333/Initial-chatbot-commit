from flask import Flask, request, jsonify, render_template_string
from notion_backend import (
    parse_add_command,
    parse_status_command,
    find_course_id,
    find_assignment_id_by_name,
    create_assignment,
    update_assignment
)

app = Flask(__name__)

HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
  <title>Assignment Chatbot</title>
  <style>
    body { font-family: sans-serif; padding: 20px; }
    #chatbox { width: 100%; max-width: 600px; margin: auto; }
    .message { margin: 10px 0; }
    .user { color: blue; }
    .bot { color: green; }
  </style>
</head>
<body>
  <div id="chatbox">
    <h2>🧠 Assignment Chatbot</h2>
    <div id="messages"></div>
    <form id="chatForm">
      <input type="text" id="messageInput" placeholder="Type your command..." style="width: 80%;">
      <button type="submit">Send</button>
    </form>
  </div>
  <script>
    const form = document.getElementById("chatForm");
    const input = document.getElementById("messageInput");
    const messages = document.getElementById("messages");

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const userMsg = input.value;
      messages.innerHTML += `<div class='message user'>🧑‍💻 ${userMsg}</div>`;
      input.value = "";

      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg })
      });
      const data = await res.json();
      messages.innerHTML += `<div class='message bot'>🤖 ${data.response}</div>`;
    });
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "").lower()

    STATUS_MAP = {
        "done": "Completed",
        "in progress": "In progress",
        "not started": "Not started"
    }

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

    if any(kw in message for kw in ["status", "mark", "set", "change"]):
        parsed = parse_status_command(message)
        parsed_status = STATUS_MAP.get(parsed["Status"].lower(), parsed["Status"].capitalize())
        page_id, matched_name = find_assignment_id_by_name(parsed["Name"])
        if page_id:
            update_assignment(page_id, {"Status": parsed_status})
            response = f"✅ Updated status of '{matched_name}' to '{parsed_status}'"
        else:
            response = f"❌ Could not find assignment similar to '{parsed['Name']}'"

    elif any(kw in message for kw in ["add", "assignment", "quiz", "test", "project", "essay", "homework"]):
        parsed = parse_add_command(message)
        course_name = parsed.get("Course")
        normalized_course = COURSE_ALIASES.get(course_name.lower(), course_name) if course_name else None

        if normalized_course:
            course_id, matched_course = find_course_id(normalized_course)
            if course_id:
                create_assignment(
                    parsed["Name"],
                    course_id,
                    parsed.get("Due date"),
                    parsed.get("Type")
                )
                response = f"✅ Created assignment '{parsed['Name']}' for course '{matched_course}' due {parsed['Due date']}"
                if parsed.get("Type"):
                    response += f" as a '{parsed['Type']}'"
            else:
                valid_courses = sorted(set(COURSE_ALIASES.values()))
                response = f"❌ Could not find a course similar to '{course_name}'. Try one of: {', '.join(valid_courses)}"
        else:
            valid_courses = sorted(set(COURSE_ALIASES.values()))
            response = f"❌ Could not find course name in your command. Try one of: {', '.join(valid_courses)}"

    else:
        response = "🤖 Sorry, I didn’t understand that command."

    return jsonify({"response": response})

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
