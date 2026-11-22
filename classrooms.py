from datetime import datetime
import pandas as pd
from backend.db import get_client

def _db():
    return get_client()

def list_rooms():
    return _db().table("classrooms").select("*").order("block").order("room_number").execute().data or []

def get_room(room_id):
    return _db().table("classrooms").select("*").eq("id", room_id).maybe_single().execute().data

def add_room(data):
    return _db().table("classrooms").insert(data).execute().data

def update_room(room_id, data):
    return _db().table("classrooms").update(data).eq("id", room_id).execute().data

def delete_room(room_id):
    return _db().table("classrooms").delete().eq("id", room_id).execute().data

def _to_time_string(value):
    if pd.isna(value):
        raise ValueError("A timetable row has a missing time.")
    if hasattr(value, "strftime"):
        return value.strftime("%H:%M:%S")
    return str(value).strip()[:8]

def search_available_rooms(selected_date, start_time, end_time, block=None, min_capacity=0):
    rooms_query = _db().table("classrooms").select("*")
    if block:
        rooms_query = rooms_query.ilike("block", f"%{block}%")
    if min_capacity:
        rooms_query = rooms_query.gte("capacity", min_capacity)
    rooms = rooms_query.order("block").order("room_number").execute().data or []
    schedules = (
        _db().table("timetable")
        .select("room_id,start_time,end_time")
        .eq("class_date", selected_date.isoformat())
        .execute().data or []
    )
    requested_start = start_time.strftime("%H:%M:%S")
    requested_end = end_time.strftime("%H:%M:%S")
    busy_room_ids = set()
    for item in schedules:
        existing_start = str(item["start_time"])[:8]
        existing_end = str(item["end_time"])[:8]
        # Two periods overlap when each starts before the other ends.
        if requested_start < existing_end and existing_start < requested_end:
            busy_room_ids.add(item["room_id"])
    return [room for room in rooms if room["id"] not in busy_room_ids]

def import_excel_timetable(uploaded_file):
    workbook = pd.ExcelFile(uploaded_file)
    sheet_map = {name.strip().lower(): name for name in workbook.sheet_names}
    if "timetable" not in sheet_map:
        raise ValueError("Workbook must contain a sheet named 'Timetable'.")
    timetable = pd.read_excel(workbook, sheet_name=sheet_map["timetable"])
    timetable.columns = [str(c).strip().lower() for c in timetable.columns]
    required = {"room_number", "block", "date", "start_time", "end_time"}
    missing = required - set(timetable.columns)
    if missing:
        raise ValueError("Timetable sheet is missing columns: " + ", ".join(sorted(missing)))

    room_sheet = None
    if "classrooms" in sheet_map:
        room_sheet = pd.read_excel(workbook, sheet_name=sheet_map["classrooms"])
        room_sheet.columns = [str(c).strip().lower() for c in room_sheet.columns]

    warnings = []
    rooms_processed = 0
    if room_sheet is not None:
        for _, row in room_sheet.iterrows():
            if pd.isna(row.get("room_number")) or pd.isna(row.get("block")):
                continue
            room_data = {
                "room_number": str(row["room_number"]).strip(),
                "block": str(row["block"]).strip(),
                "floor": None if pd.isna(row.get("floor")) else str(row.get("floor")).strip(),
                "capacity": 40 if pd.isna(row.get("capacity")) else int(row["capacity"]),
                "projector": False if pd.isna(row.get("projector")) else bool(row["projector"]),
                "smartboard": False if pd.isna(row.get("smartboard")) else bool(row["smartboard"]),
                "ac": False if pd.isna(row.get("ac")) else bool(row["ac"]),
                "notes": None if pd.isna(row.get("notes")) else str(row["notes"])
            }
            existing = (_db().table("classrooms").select("id")
                        .eq("room_number", room_data["room_number"])
                        .eq("block", room_data["block"]).maybe_single().execute().data)
            if existing:
                _db().table("classrooms").update(room_data).eq("id", existing["id"]).execute()
            else:
                _db().table("classrooms").insert(room_data).execute()
            rooms_processed += 1

    room_cache = {}
    for _, row in timetable.iterrows():
        if pd.isna(row.get("room_number")) or pd.isna(row.get("block")):
            warnings.append("Skipped a timetable row with missing room number or block.")
            continue
        room_number = str(row["room_number"]).strip()
        block = str(row["block"]).strip()
        key = (room_number, block)
        if key not in room_cache:
            room = (_db().table("classrooms").select("id")
                    .eq("room_number", room_number).eq("block", block)
                    .maybe_single().execute().data)
            if not room:
                room_data = {"room_number": room_number, "block": block, "capacity": 40}
                room = _db().table("classrooms").insert(room_data).execute().data[0]
                rooms_processed += 1
            room_cache[key] = room["id"]

        parsed_date = pd.to_datetime(row["date"], errors="coerce")
        if pd.isna(parsed_date):
            warnings.append(f"Skipped invalid date for room {room_number}.")
            continue
        start = _to_time_string(row["start_time"])
        end = _to_time_string(row["end_time"])
        if start >= end:
            warnings.append(f"Skipped invalid time range for room {room_number}.")
            continue
        record = {
            "room_id": room_cache[key],
            "class_date": parsed_date.date().isoformat(),
            "start_time": start,
            "end_time": end,
            "subject": None if pd.isna(row.get("subject")) else str(row.get("subject")),
            "faculty_name": None if pd.isna(row.get("faculty_name")) else str(row.get("faculty_name"))
        }
        # Upsert avoids duplicate entries when the same Excel file is uploaded again.
        _db().table("timetable").upsert(
            record, on_conflict="room_id,class_date,start_time,end_time"
        ).execute()

    return {"rooms": rooms_processed, "entries": len(timetable) - len(warnings), "warnings": warnings}

def get_dashboard_counts():
    rooms = _db().table("classrooms").select("id", count="exact").execute()
    timetable = _db().table("timetable").select("id", count="exact").execute()
    return {"rooms": rooms.count or 0, "entries": timetable.count or 0}
