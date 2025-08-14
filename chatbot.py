from notion_backend import (
    create_assignment,
    update_assignment,
    parse_add_command,
    parse_status_command,
    find_course_id,
    find_assignment_id_by_name,
    COURSE_ALIASES
)

def handle_add_command(command):
    parsed = parse_add_command(command)
    print("\n🧠 Parsed Add Command:")
    print(parsed)

    course_name = parsed.get("Course")
    if not course_name:
        return "❌ No course name found in command."

    normalized_course = COURSE_ALIASES.get(course_name.lower(), course_name)
    print("Normalized course:", normalized_course)

    course_id, matched_course = find_course_id(normalized_course)

    if not course_id or not isinstance(course_id, str):
        return f"❌ Could not find course named '{parsed['Course']}'"

    print("Using course ID:", course_id)
    print("Type of course_id:", type(course_id))

    create_assignment(
        parsed["Name"],
        course_id,
        parsed.get("Due date"),
        parsed.get("Type")
    )

    response = f"✅ Created assignment '{parsed['Name']}' for course '{matched_course}' due {parsed['Due date']}"
    if parsed.get("Type"):
        response += f" as a '{parsed['Type']}'"
    return response


def handle_status_command(command):
    parsed = parse_status_command(command)
    print("\n🧠 Parsed Status Command:")
    print(parsed)

    assignment_name = parsed.get("Name")
    new_status = parsed.get("Status")

    if not assignment_name or not new_status:
        return "❌ Could not parse assignment name or status."

    assignment_id, matched_title = find_assignment_id_by_name(assignment_name)
    if not assignment_id:
        return f"❌ Could not find assignment named '{assignment_name}'"

    update_assignment(assignment_id, { "Status": new_status })
    return f"✅ Marked '{matched_title}' as '{new_status}'"


def handle_command(command):
    command_lower = command.lower()

    if any(kw in command_lower for kw in ["add", "create", "make"]) and "assignment" in command_lower:
        return handle_add_command(command)
    elif any(kw in command_lower for kw in ["mark", "set", "change", "update"]) and "as" in command_lower:
        return handle_status_command(command)
    elif any(kw in command_lower for kw in ["essay", "project", "hw", "lab"]) and "due" in command_lower:
        return handle_add_command(command)
    else:
        return "🤔 Sorry, I didn't understand that command. Try something like:\n- 'Add an assignment called Essay 1 for History due Friday'\n- 'Mark Essay 1 as completed'"


# 🧪 Example usage
if __name__ == "__main__":
    test_commands = [
        "Add an assignment called Essay 1 under the class US History due August 20",
        "Make a project called Bio Lab for bio due next Monday",
        "Mark essay one as done",
        "Set Essay 1 to completed",
        "Create hw called Math Review for precalc due tomorrow",
        "Add a lab called Cell Structure for the course Biology due Friday"
    ]

    for cmd in test_commands:
        print(f"\n💬 Command: {cmd}")
        result = handle_command(cmd)
        print(result)
