import streamlit as st
from datetime import date, time
from backend.auth import sign_in, sign_out, sign_up_student, get_profile
from backend.db import get_client
from backend.classrooms import (
    search_available_rooms, get_room, list_rooms, add_room,
    update_room, delete_room, import_excel_timetable, get_dashboard_counts
)

st.set_page_config(page_title="Empty Classroom Finder", page_icon="🏫", layout="wide")

def init_state():
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("profile", None)

init_state()

def login_screen():
    st.title("🏫 Empty Classroom Finder")
    st.caption("Find an available classroom on your campus.")
    login_tab, signup_tab = st.tabs(["Login", "Student registration"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("College email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
        if submitted:
            try:
                user = sign_in(email.strip(), password)
                profile = get_profile(user.id)
                if not profile:
                    st.error("Your profile is not set up. Please contact the administrator.")
                else:
                    st.session_state.user = user
                    st.session_state.profile = profile
                    st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")

    with signup_tab:
        st.info("Student self-registration is enabled. Faculty accounts must be created/promoted by the administrator.")
        with st.form("signup_form"):
            name = st.text_input("Full name")
            email = st.text_input("College email address", key="signup_email")
            password = st.text_input("Create password", type="password", key="signup_password")
            confirm = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create student account", use_container_width=True)
        if submitted:
            if not name.strip() or not email.strip() or not password:
                st.error("Please complete all fields.")
            elif password != confirm:
                st.error("Passwords do not match.")
            elif len(password) < 8:
                st.error("Use a password with at least 8 characters.")
            else:
                try:
                    sign_up_student(name.strip(), email.strip(), password)
                    st.success("Account created. If email confirmation is enabled in Supabase, verify your email before logging in.")
                except Exception as e:
                    st.error(f"Registration failed: {e}")

def room_card(room, selected_date, start, end):
    with st.container(border=True):
        st.subheader(f"Room {room['room_number']}")
        st.write(f"**{room.get('block') or 'Block not specified'}** · Floor {room.get('floor') or '—'}")
        st.write(f"Capacity: **{room.get('capacity') or 'Not specified'}**")
        facilities = []
        for field, label in [("projector", "Projector"), ("smartboard", "Smartboard"), ("ac", "AC")]:
            if room.get(field):
                facilities.append(label)
        st.caption("Facilities: " + (", ".join(facilities) if facilities else "Not specified"))
        if st.button("View room details", key=f"detail_{room['id']}", use_container_width=True):
            st.session_state["selected_room_id"] = room["id"]
            st.rerun()

def search_page():
    st.title("Find an empty classroom")
    st.write("Choose the date and the complete time period you need.")
    with st.form("search_form"):
        c1, c2, c3 = st.columns(3)
        selected_date = c1.date_input("Date", value=date.today(), min_value=date.today())
        start = c2.time_input("Start time", value=time(10, 0), step=300)
        end = c3.time_input("End time", value=time(11, 0), step=300)
        c4, c5 = st.columns(2)
        block = c4.text_input("Block (optional)")
        min_capacity = c5.number_input("Minimum capacity", min_value=0, value=0, step=5)
        submitted = st.form_submit_button("Search available classrooms", type="primary", use_container_width=True)
    if submitted:
        if end <= start:
            st.error("End time must be later than start time.")
            return
        try:
            rooms = search_available_rooms(selected_date, start, end, block.strip() or None, int(min_capacity))
            st.session_state["search_results"] = rooms
            st.session_state["search_params"] = (selected_date, start, end)
        except Exception as e:
            st.error(f"Could not search classrooms: {e}")
            return

    if "search_results" in st.session_state:
        rooms = st.session_state["search_results"]
        params = st.session_state["search_params"]
        st.divider()
        st.subheader(f"{len(rooms)} available classroom(s)")
        st.caption(f"{params[0].strftime('%d %b %Y')} · {params[1].strftime('%I:%M %p')}–{params[2].strftime('%I:%M %p')}")
        if not rooms:
            st.warning("No classrooms match this time slot. Try another time, block or capacity.")
        else:
            cols = st.columns(2)
            for i, room in enumerate(rooms):
                with cols[i % 2]:
                    room_card(room, *params)
            selected_id = st.session_state.get("selected_room_id")
            if selected_id:
                selected_room = get_room(selected_id)
                if selected_room:
                    st.divider()
                    st.subheader(f"Room details: {selected_room['room_number']}")
                    st.write(f"**Block:** {selected_room.get('block') or '—'}  ·  **Floor:** {selected_room.get('floor') or '—'}")
                    st.write(f"**Capacity:** {selected_room.get('capacity') or '—'}")
                    st.write(f"**Projector:** {'Yes' if selected_room.get('projector') else 'No'}  ·  **Smartboard:** {'Yes' if selected_room.get('smartboard') else 'No'}  ·  **AC:** {'Yes' if selected_room.get('ac') else 'No'}")
                    st.write(selected_room.get("notes") or "No additional details.")

def details_page():
    st.title("Classroom details")
    room_id = st.session_state.get("selected_room_id")
    if not room_id:
        st.info("Select a classroom from the search results first.")
        return
    try:
        room = get_room(room_id)
        if not room:
            st.error("Classroom not found.")
            return
        st.header(f"Room {room['room_number']}")
        a, b = st.columns(2)
        with a:
            st.metric("Seating capacity", room.get("capacity") or "—")
            st.write(f"**Block:** {room.get('block') or '—'}")
            st.write(f"**Floor:** {room.get('floor') or '—'}")
        with b:
            st.write("**Facilities**")
            st.write(f"Projector: {'Yes' if room.get('projector') else 'No'}")
            st.write(f"Smartboard: {'Yes' if room.get('smartboard') else 'No'}")
            st.write(f"Air conditioning: {'Yes' if room.get('ac') else 'No'}")
        st.write(f"**Other details:** {room.get('notes') or 'No additional information.'}")
        if st.button("Back to search results"):
            st.session_state["page"] = "Find classrooms"
            st.rerun()
    except Exception as e:
        st.error(f"Could not load room: {e}")

def faculty_page():
    st.title("Faculty management")
    st.caption("Only accounts with the faculty role can access this section.")
    tab1, tab2, tab3 = st.tabs(["Register classroom", "Upload Excel timetable", "Manage classrooms"])

    with tab1:
        with st.form("add_room_form"):
            c1, c2 = st.columns(2)
            room_number = c1.text_input("Room number *")
            block = c2.text_input("Block / building *")
            c3, c4 = st.columns(2)
            floor = c3.text_input("Floor")
            capacity = c4.number_input("Seating capacity", min_value=1, value=40)
            c5, c6, c7 = st.columns(3)
            projector = c5.checkbox("Projector")
            smartboard = c6.checkbox("Smartboard")
            ac = c7.checkbox("Air conditioning")
            notes = st.text_area("Additional details")
            submitted = st.form_submit_button("Register classroom", type="primary")
        if submitted:
            if not room_number.strip() or not block.strip():
                st.error("Room number and block are required.")
            else:
                try:
                    add_room({
                        "room_number": room_number.strip(), "block": block.strip(),
                        "floor": floor.strip() or None, "capacity": int(capacity),
                        "projector": projector, "smartboard": smartboard, "ac": ac,
                        "notes": notes.strip() or None
                    })
                    st.success("Classroom registered successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not register classroom: {e}")

    with tab2:
        st.write("Upload an `.xlsx` workbook containing **Classrooms** and **Timetable** sheets. The Timetable sheet is required.")
        st.download_button("Download Excel template", data=Path("database/timetable_template.xlsx").read_bytes(),
                           file_name="classroom_timetable_template.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        uploaded = st.file_uploader("Choose Excel workbook", type=["xlsx"])
        if uploaded and st.button("Import timetable", type="primary"):
            try:
                result = import_excel_timetable(uploaded)
                st.success(f"Import completed: {result['rooms']} classroom(s) processed and {result['entries']} timetable entry/entries processed.")
                if result.get("warnings"):
                    for warning in result["warnings"]:
                        st.warning(warning)
            except Exception as e:
                st.error(f"Import failed: {e}")

    with tab3:
        try:
            rooms = list_rooms()
            if not rooms:
                st.info("No classrooms registered yet.")
            for room in rooms:
                with st.expander(f"{room['room_number']} — {room.get('block') or 'No block'}"):
                    with st.form(f"edit_{room['id']}"):
                        c1, c2 = st.columns(2)
                        new_block = c1.text_input("Block", value=room.get("block") or "")
                        new_floor = c2.text_input("Floor", value=room.get("floor") or "")
                        new_capacity = st.number_input("Capacity", min_value=1, value=int(room.get("capacity") or 1), key=f"cap_{room['id']}")
                        p = st.checkbox("Projector", value=bool(room.get("projector")), key=f"p_{room['id']}")
                        sb = st.checkbox("Smartboard", value=bool(room.get("smartboard")), key=f"sb_{room['id']}")
                        air = st.checkbox("Air conditioning", value=bool(room.get("ac")), key=f"ac_{room['id']}")
                        new_notes = st.text_area("Notes", value=room.get("notes") or "", key=f"notes_{room['id']}")
                        save = st.form_submit_button("Save changes")
                    if save:
                        try:
                            update_room(room["id"], {
                                "block": new_block, "floor": new_floor or None,
                                "capacity": int(new_capacity), "projector": p,
                                "smartboard": sb, "ac": air, "notes": new_notes or None
                            })
                            st.success("Updated.")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                    if st.button("Delete classroom", key=f"delete_{room['id']}"):
                        try:
                            delete_room(room["id"])
                            st.success("Classroom deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Could not delete classroom. Remove its timetable entries first if necessary. Details: {e}")
        except Exception as e:
            st.error(f"Could not load classrooms: {e}")

def main():
    if st.session_state.user is None:
        login_screen()
        return

    profile = st.session_state.profile or {}
    role = profile.get("role", "student")
    name = profile.get("full_name") or st.session_state.user.email
    with st.sidebar:
        st.title("🏫 Classroom Finder")
        st.write(f"Signed in as **{name}**")
        st.caption(f"Role: {role.title()}")
        choices = ["Find classrooms", "Room details"]
        if role == "faculty":
            choices.append("Faculty management")
        page = st.radio("Navigation", choices, key="page")
        st.divider()
        if st.button("Logout", use_container_width=True):
            sign_out()
            st.session_state.user = None
            st.session_state.profile = None
            for key in ["search_results", "search_params", "selected_room_id"]:
                st.session_state.pop(key, None)
            st.rerun()

    if page == "Find classrooms":
        search_page()
    elif page == "Room details":
        details_page()
    elif page == "Faculty management" and role == "faculty":
        faculty_page()
    else:
        search_page()

if __name__ == "__main__":
    main()
