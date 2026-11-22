from backend.db import get_client

def sign_in(email, password):
    response = get_client().auth.sign_in_with_password({"email": email, "password": password})
    return response.user

def sign_up_student(full_name, email, password):
    response = get_client().auth.sign_up({
        "email": email,
        "password": password,
        "options": {"data": {"full_name": full_name}}
    })
    return response.user

def get_profile(user_id):
    response = get_client().table("profiles").select("*").eq("id", user_id).maybe_single().execute()
    return response.data

def sign_out():
    get_client().auth.sign_out()
