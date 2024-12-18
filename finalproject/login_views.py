from django.contrib import messages
from django.shortcuts import render, redirect
from .firebase import login as firebase_login, get_user_profile, log_user_login

def login_view(request): 
    print("View accessed")
    if request.method == 'POST':
        print("POST method")
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not email or not password:
            messages.error(request, "Email and password are required.")
            print("Missing email or password")
            return redirect('login')  # Redirecting if fields are missing
        
        # Authenticate user using Firebase
        try:
            user, session_id = firebase_login(email, password)  # Unpack tuple
            print(f"Firebase login response: User - {user}, Session ID - {session_id}")
        except Exception as e:
            print(f"Error during Firebase login: {e}")
            messages.error(request, "Something went wrong. Please try again.")
            return redirect('login')

        if user and 'localId' in user:
            user_id = user['localId']  # Extract user ID
            print("User logged in successfully")

            # Store session data
            request.session['session_id'] = session_id
            request.session['user_id'] = user_id
            print(f"Session ID stored: {session_id}")
            print(f"User ID stored: {user_id}")

            # Fetch and store user profile
            user_profile = get_user_profile(user_id)
            if user_profile:
                request.session['user_profile'] = user_profile
                print(f"User profile stored: {user_profile}")
            else:
                print("No user profile found.")

            # Redirect to user home page
            return render(request, 'user_home.html', {'show_modal': True})
        else:
            print("Invalid credentials or missing user data.")
            messages.error(request, 'Invalid email or password. Please try again!')

        # Render login page on failure
        return render(request, 'login.html', {'show_modal': False})

    # Handle GET requests
    print("GET method")
    return render(request, 'login.html', {'show_modal': False})

def user_home(request):
    return render(request, 'user_home.html')