from django.contrib import messages
from django.shortcuts import render, redirect
from .firebase import logout as log_user_logout

def logout_views(request):
    session_id = request.session.get('session_id')  
    if session_id:
        log_user_logout(session_id)  # Log logout time
        print(f"Logout time recorded for session {session_id}")
    
    # Clear session data
    request.session.flush()
    print("User session cleared")
    return redirect('guest_home')