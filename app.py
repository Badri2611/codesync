import streamlit as st
import os
import json
import random
import smtplib
import uuid
import subprocess
from datetime import datetime
from email_validator import validate_email, EmailNotValidError
import difflib

# File Paths
USER_FILE = './data/users.json'
ROOM_FILE = './data/rooms.json'
FLASHCARDS_FILE = './data/flashcards.json'
SNIPPETS_FILE = './data/snippets.json'
LEADERBOARD_FILE = './data/leaderboard.json'
PROJECTS_FILE = "data/projects.json"

# Streamlit Configuration
st.set_page_config(page_title="Collaborative Coding Platform", layout="wide")

# Utility Functions
def load_json(file_path, default_data=None):
    if not os.path.exists(file_path):
        return default_data if default_data is not None else {}
    with open(file_path, 'r') as file:
        return json.load(file)

def save_json(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def track_changes(old_code, new_code):
    diff = difflib.ndiff(old_code.splitlines(), new_code.splitlines())
    return [line for line in diff if line.startswith("+ ") or line.startswith("- ")]

def load_projects():
    return load_json(PROJECTS_FILE, default_data={})

def save_projects(projects):
    save_json(PROJECTS_FILE, projects)

# OTP Email Sender
def send_otp(email):
    otp = random.randint(100000, 999999)
    try:
        sender_email = "Codesync2611@gmail.com"
        sender_password = "gmbf vtwl wehr pauw"  # Application-specific password
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            subject = "Your OTP for Registration"
            body = f"Your OTP is: {otp}\nThis OTP is valid for 5 minutes."
            message = f"Subject: {subject}\n\n{body}"
            server.sendmail(sender_email, email, message)

        return otp
    except Exception as e:
        st.error(f"Error sending OTP: {e}")
        return None

# Authentication Functions
def register_user():
    users = load_json(USER_FILE)

    username = st.text_input("Choose a Username")
    email = st.text_input("Email Address")
    college_id = st.text_input("College ID (10 characters, alphanumeric)")
    date_of_birth = st.date_input(
        "Date of Birth",
        min_value=datetime(1990, 1, 1),
        max_value=datetime(2030, 12, 31)
    )
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    if username in users:
        st.error("Username already exists.")
        return False

    if any(user["college_id"] == college_id for user in users.values()):
        st.error("This College ID is already registered.")
        return False

    if not college_id.isalnum() or len(college_id) != 10:
        st.error("College ID must be 10 alphanumeric characters.")
        return False

    if password != confirm_password:
        st.error("Passwords do not match.")
        return False

    try:
        valid = validate_email(email)
        email = valid.email
    except EmailNotValidError as e:
        st.error(f"Invalid email: {e}")
        return False

    if "otp_sent" not in st.session_state:
        st.session_state.otp_sent = False
        st.session_state.otp_verified = False

    if not st.session_state.otp_sent:
        if st.button("Send OTP"):
            otp = send_otp(email)
            if otp:
                st.session_state.otp_sent = True
                st.session_state.generated_otp = otp
                st.success("OTP sent to your email.")
    elif not st.session_state.otp_verified:
        entered_otp = st.text_input("Enter OTP", type="password")
        if st.button("Verify OTP"):
            if entered_otp == str(st.session_state.generated_otp):
                st.session_state.otp_verified = True
                st.success("OTP verified successfully!")
            else:
                st.error("Invalid OTP. Please try again.")
    elif st.session_state.otp_verified:
        if st.button("Register"):
            users[username] = {
                "username": username,
                "email": email,
                "college_id": college_id,
                "date_of_birth": str(date_of_birth),
                "password": password,
                "badges": []
            }
            save_json(USER_FILE, users)
            st.success("Registration successful! You can now log in.")
            st.session_state.otp_sent = False
            st.session_state.otp_verified = False
            st.session_state.generated_otp = None
            return True
    return False

def login_user():
    users = load_json(USER_FILE)
    college_id = st.text_input("College ID (10 characters, alphanumeric)")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        for user in users.values():
            if user["college_id"] == college_id and user["password"] == password:
                st.session_state.user = user
                st.session_state.user['is_logged_in'] = True
                st.success(f"Welcome back, {user['username']}!")
                return True
        st.error("Invalid College ID or password.")
    return False

def logout_user():
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.sidebar.success("Logged out successfully!")

# Profile Management
def view_profile():
    st.title("Your Profile")
    user = st.session_state.user

    st.write(f"**Username:** {user['username']}")
    st.write(f"**College ID:** {user['college_id']}")
    st.write(f"**Email:** {user['email']}")
    st.write(f"**Date of Birth:** {user['date_of_birth']}")
    st.write(f"**Badges Earned:** {', '.join(map(str, user.get('badges', []))) or 'None'}")

# Room Management
def workspace():
    st.title("Room Workspace")
    room_id = st.text_input("Enter Room ID (or create a new one)")
    if not room_id:
        st.warning("Enter or create a room to proceed.")
        return

    rooms = load_json(ROOM_FILE)
    if room_id not in rooms:
        if st.button("Create Room"):
            room_description = st.text_input("Room Description (optional)")
            rooms[room_id] = {"code": "", "chat": [], "participants": [], "description": room_description}
            save_json(ROOM_FILE, rooms)
            st.success(f"Room {room_id} created!")
    else:
        st.info(f"Joined Room: {room_id}")

    room_data = rooms.get(room_id, {"code": "", "chat": [], "participants": []})
    if st.session_state.user['username'] not in room_data["participants"]:
        room_data["participants"].append(st.session_state.user['username'])
        save_json(ROOM_FILE, rooms)

    st.write(f"**Room Description:** {room_data.get('description', 'No description')}")

    # Display participants
    st.write("**Participants:**")
    for participant in room_data["participants"]:
        st.write(f"- {participant}")

    # Code Editor Section
    st.subheader("Code Editor")
    code = st.text_area("Write your code here:", value=room_data["code"], height=300)
    if st.button("Save Code"):
        room_data["code"] = code
        rooms[room_id] = room_data
        save_json(ROOM_FILE, rooms)
        st.success("Code saved successfully!")

    if st.button("Run Code"):
        try:
            temp_file = "temp_code.py"
            with open(temp_file, "w") as f:
                f.write(code)
            output = subprocess.check_output(["python3", temp_file], stderr=subprocess.STDOUT, text=True)
            st.text_area("Execution Output", value=output, height=200, disabled=True)
        except subprocess.CalledProcessError as e:
            st.error("Error in code execution!")
            st.text_area("Error", value=e.output, height=200, disabled=True)
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    # Enhanced Chat Section
    st.subheader("Chat Box")
    chat_input = st.text_input("Type a message")
    emoji_picker = st.selectbox("React with Emoji", ["😊", "👍", "🚀", "🔥", "❓", "👎", "🤔", "😀", "💩", "😎", "🫥", "👽", "☠️", "🤡", "🤯", "🤬"], index=0)

    if st.button("Send Message"):
        message = {
            "user": st.session_state.user["username"],
            "message": f"{chat_input} {emoji_picker}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        room_data["chat"].append(message)
        rooms[room_id] = room_data
        save_json(ROOM_FILE, rooms)
        st.success("Message sent!")

    # Chat History with Edit/Delete
    st.write("**Chat History:**")
    for idx, chat in enumerate(room_data["chat"]):
        st.write(f"[{chat['timestamp']}] {chat['user']}: {chat['message']}")
        if chat["user"] == st.session_state.user["username"]:
            if st.button(f"Edit Message #{idx + 1}", key=f"edit_{idx}"):
                edit_msg = st.text_input("Edit Message", value=chat["message"])
                if st.button(f"Save Edit #{idx + 1}"):
                    room_data["chat"][idx]["message"] = edit_msg
                    save_json(ROOM_FILE, rooms)
                    st.success("Message edited successfully!")

            if st.button(f"Delete Message #{idx + 1}", key=f"delete_{idx}"):
                room_data["chat"].pop(idx)
                save_json(ROOM_FILE, rooms)
                st.success("Message deleted successfully!")
                break

# Gamification
def gamification():
    st.title("Achievements & Leaderboard")
    leaderboard = load_json(LEADERBOARD_FILE)
    user = st.session_state.user

    # Add an achievement
    if st.button("Complete a Session"):
        badge = "Active Coder"
        if badge not in user.get("badges", []):
            user["badges"].append(badge)
            save_json(USER_FILE, load_json(USER_FILE))
            leaderboard[user["username"]] = leaderboard.get(user["username"], 0) + 1
            save_json(LEADERBOARD_FILE, leaderboard)
            st.success(f"You earned the badge: {badge}!")

    # Display leaderboard
    st.subheader("Leaderboard")
    sorted_leaderboard = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)
    for rank, (username, points) in enumerate(sorted_leaderboard, 1):
        st.write(f"{rank}. {username}: {points} points")

# Code Snippet Library
def snippet_library():
    st.title("Code Snippet Library")
    snippets = load_json(SNIPPETS_FILE, default_data=[])

    # Save snippet
    snippet_title = st.text_input("Snippet Title")
    snippet_code = st.text_area("Snippet Code")
    snippet_tags = st.text_input("Tags (comma-separated)")
    
    if st.button("Save Snippet"):
        if not snippet_title or not snippet_code:
            st.error("Both title and code are required!")
        else:
            snippet = {
                "title": snippet_title,
                "code": snippet_code,
                "tags": snippet_tags.split(",") if snippet_tags else []
            }
            snippets.append(snippet)
            save_json(SNIPPETS_FILE, snippets)
            st.success("Snippet saved successfully!")

    # Search Snippets
    st.subheader("Search Snippets")
    search_query = st.text_input("Search by Title or Tags")
    
    filtered_snippets = [
        s for s in snippets
        if search_query.lower() in s["title"].lower() or any(search_query.lower() in tag.lower() for tag in s["tags"])
    ]

    if filtered_snippets:
        for snippet in filtered_snippets:
            with st.expander(snippet["title"]):
                st.code(snippet["code"])
                st.write(f"**Tags:** {', '.join(snippet['tags'])}")
    else:
        st.write("No snippets found matching your query.")

# Project Management
def project_management():
    st.title("Project Management")
    projects = load_projects()
    project_option = st.sidebar.selectbox(
        "Project Actions",
        ["Create Project", "View Projects"],
        key="project_actions"
    )

    if project_option == "Create Project":
        if not st.session_state.user.get("is_logged_in"):
            st.warning("Please login to create projects")
            return

        project_name = st.text_input("Enter project name")
        if st.button("Create Project"):
            project_id = str(uuid.uuid4())
            projects[project_id] = {
                "name": project_name,
                "main_branch": "",
                "forks": {},
                "owner": st.session_state.user["username"]
            }
            save_projects(projects)
            st.success(f"Project '{project_name}' created successfully!")

    elif project_option == "View Projects":
        project_list = {pid: proj["name"] for pid, proj in projects.items()}
        selected_project = st.selectbox("Select a project", list(project_list.values()))

        # Fork Project
        if st.session_state.user.get("is_logged_in"):
            if st.button("Fork Project"):
                user = st.session_state.user["username"]
                for pid, proj in projects.items():
                    if proj["name"] == selected_project:
                        fork_id = str(uuid.uuid4())
                        projects[pid]["forks"][fork_id] = {
                            "user": user,
                            "code": proj["main_branch"],
                            "pull_request": False,
                            "changes": []
                        }
                        save_projects(projects)
                        st.success(f"Project '{selected_project}' forked successfully!")

        # Display forks and edits
        st.subheader("Your Forks")
        user_forks = [
            (pid, fork_id, fork) 
            for pid, proj in projects.items()
            for fork_id, fork in proj["forks"].items()
            if fork["user"] == st.session_state.get("user", {}).get("username")
        ]

        if user_forks:
            selected_fork = st.selectbox(
                "Select your fork",
                [f"{proj['name']} - {fork_id[:8]}" for pid, fork_id, proj in user_forks]
            )
            fork_id_full = user_forks[[f[1] for f in user_forks].index(selected_fork.split(" - ")[1])]
            selected_fork_data = user_forks[fork_id_full][2]

            # Code Editor
            new_code = st.text_area(
                "Edit your fork",
                value=selected_fork_data["code"],
                height=300,
                key=f"editor_{selected_fork}"
            )

            if st.button("Save Changes"):
                # Track changes
                old_code = selected_fork_data["code"]
                changes = track_changes(old_code, new_code)
                
                # Update fork
                projects[user_forks[fork_id_full][0]]["forks"][user_forks[fork_id_full][1]]["code"] = new_code
                projects[user_forks[fork_id_full][0]]["forks"][user_forks[fork_id_full][1]]["changes"] = changes
                save_projects(projects)
                st.success("Changes saved successfully!")

            if st.button("Submit Pull Request"):
                projects[user_forks[fork_id_full][0]]["forks"][user_forks[fork_id_full][1]]["pull_request"] = True
                save_projects(projects)
                st.success("Pull request submitted!")

        # Display and manage pull requests
        st.subheader("Active Pull Requests")
        for pid, proj in projects.items():
            if proj.get("owner") == st.session_state.get("user", {}).get("username"):
                for fork_id, fork in proj["forks"].items():
                    if fork.get("pull_request"):
                        st.write(f"PR from {fork['user']}:")
                        st.code(fork["code"], language='python')
                        
                        if st.button(f"Merge {fork['user']}'s PR", key=f"merge_{fork_id}"):
                            proj["main_branch"] = fork["code"]
                            del proj["forks"][fork_id]
                            save_projects(projects)
                            st.success("Changes merged successfully!")

# Main Application Logic
menu = st.sidebar.selectbox(
    "Menu",
    ["Home", "Login", "Register", "Profile", "Workspace", "Gamification", "Code Snippets", "Projects"]
)

if "user" not in st.session_state:
    st.session_state.user = {"is_logged_in": False}

if st.session_state.user.get("is_logged_in"):
    logout_user()

if menu == "Home":
    st.title("Welcome to Collaborative Coding Platform 🚀")
    st.write('''Your ultimate space for seamless teamwork and innovation!

Key Features:
- 🛠 Real-Time Collaborative Coding
- 💬 Integrated Chat System
- 🎨 Syntax Highlighting
- 🖥 Code Execution
- 👤 Personalized Profiles
- 🔒 Secure Authentication
- 📚 Flashcards for Learning
(!!Important announcement:The project section is under development.Will be out soon..)
Get Started:
Login or register to start collaborating!''')

elif menu == "Login":
    if not st.session_state.user.get("is_logged_in"):
        if login_user():
            st.sidebar.success("Login successful!")
    else:
        st.info(f"Already logged in as {st.session_state.user['username']}.")

elif menu == "Register":
    register_user()

elif menu == "Profile":
    if st.session_state.user.get("is_logged_in"):
        view_profile()
    else:
        st.warning("You need to log in to view and edit your profile.")

elif menu == "Workspace":
    workspace()

elif menu == "Gamification":
    gamification()

elif menu == "Code Snippets":
    snippet_library()

elif menu == "Projects":
    project_management()

# Ensure the data folder exists
if not os.path.exists("data"):
    os.makedirs("data")
