from django.shortcuts import render, redirect
from django.http import HttpResponse
from .firebase import get_user_profile

def profile_view(request):

    print(f"Current session data: {request.session.items()}")
    
    # Retrieve user ID from session
    user_id = request.session.get('user_id')
    print(f"User  ID from session: {user_id}")

    if not user_id:
        return redirect('login')

    # Always fetch the latest user profile information
    user_profile = get_user_profile(user_id)
    
    if not user_profile:
        return HttpResponse("User  profile not found", status=404)

    # Store user profile in session for potential future use
    request.session['user_profile'] = user_profile
    print(f"User  profile stored in session after retrieval: {request.session['user_profile']}")

    name = user_profile.get('name')
    email = user_profile.get('email')

    return render(request, 'profile.html', {'name': name, 'email': email})