# Empty Classroom Finder

A Streamlit + Supabase application for finding vacant college classrooms using an Excel timetable.

## Features
- Student and faculty login
- Student self-registration
- Search by date, start/end time, block and minimum capacity
- Classroom details and facilities
- Faculty-only classroom registration, editing and deletion
- Faculty Excel timetable import
- Supabase PostgreSQL database with role-based Row Level Security

## 1. Create the Supabase project
1. Create a project at https://supabase.com/.
2. Open **SQL Editor**.
3. Run the complete contents of `database/schema.sql`.
4. Open **Project Settings → API** and copy the Project URL and anon/public key.
5. In Authentication settings, decide whether to require email confirmation. For easier college-project testing, you can disable email confirmation temporarily.

## 2. Configure the app
Create `.streamlit/secrets.toml` (copy `.streamlit/secrets.toml.example`) and enter your Supabase URL and anon key.

Never upload `secrets.toml` or a service-role key to GitHub.

## 3. Install and run locally
Python 3.10 or newer is recommended.

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Install dependencies and run:
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 4. Create a faculty account
1. Register the person through the app's Student registration tab (or create the account in Supabase Authentication).
2. In Supabase, open **SQL Editor**.
3. Run the following command, replacing the email:

```sql
update public.profiles
set role = 'faculty'
where id = (
  select id from auth.users
  where email = 'faculty@college.edu'
);
```

Only faculty profiles can register, edit or delete classrooms and import timetables. Do not give students the faculty role.

## 5. Excel workbook format

The workbook should be `.xlsx` and may contain two sheets.

### Sheet: Classrooms (optional but recommended)
Use these column names:

| room_number | block | floor | capacity | projector | smartboard | ac | notes |
|---|---|---|---:|---|---|---|---|
| C-204 | Block C | 2 | 60 | TRUE | TRUE | TRUE | Near lab |

### Sheet: Timetable (required)
Use these column names:

| room_number | block | date | start_time | end_time | subject | faculty_name |
|---|---|---|---|---|---|---|
| C-204 | Block C | 2026-11-23 | 09:00 | 10:00 | Mathematics | Dr Rao |
| C-204 | Block C | 2026-11-23 | 10:00 | 11:00 | Physics | Dr Shah |

- `date` should be an Excel date or `YYYY-MM-DD`.
- Times should be Excel time values or `HH:MM`.
- Room number and block must match between sheets.
- If a timetable references a room not yet registered, the app creates it with a default capacity of 40.
- Uploading the same exact timetable period again updates that period instead of creating an identical duplicate.
- Importing is an upsert, not a full replacement. Old entries are not automatically deleted. Remove obsolete timetable entries in Supabase before importing a replacement timetable.

## 6. Push to GitHub
Create a GitHub repository and upload the project files. Do not commit `.streamlit/secrets.toml`.

## 7. Deploy on Streamlit Community Cloud
1. Sign in at https://share.streamlit.io/.
2. Choose **New app** and select your GitHub repository.
3. Set the main file path to `app.py`.
4. Open the app's **Advanced settings → Secrets**.
5. Paste the two entries from your local `secrets.toml`.
6. Deploy.

## Availability logic
A room is considered busy when an existing class overlaps the requested period:
`requested_start < existing_end AND existing_start < requested_end`.

Therefore, back-to-back periods such as 09:00–10:00 and 10:00–11:00 do not overlap.

## Important limitations for a real college rollout
- The Excel timetable must be kept current. The app cannot detect an unrecorded class or a room occupied for an informal event.
- This starter app treats the timetable as the source of truth; it does not reserve or lock rooms.
- Before production use, have the college IT administrator review account onboarding, email-domain restrictions, timetable imports and database policies.
