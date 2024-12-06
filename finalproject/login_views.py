from django.contrib import messages
from django.shortcuts import render, redirect
from .firebase import login as firebase_login, get_user_profile

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

        user = firebase_login(email, password)
        
        if user:
            user_id = user.get('localId') 
            print("User logged in")
            # Store profile data in session
            request.session['user_id'] = user_id
            print(f"User ID stored in session: {request.session['user_id']}")

            user_profile = get_user_profile(user_id)
            if user_profile:
                request.session['user_profile'] = user_profile
                print(f"User profile stored in session: {request.session['user_profile']}")
            # Render the user home page with modal for successful login
            return render(request, 'user_home.html', {'show_modal': True})
        else:
            messages.error(request, 'Invalid email or password. Please try again!')
            print("Invalid credentials")
            # Render the login page with error message
            return render(request, 'login.html', {'show_modal': False})

    print("GET method")
    # Handle GET requests
    return render(request, 'login.html', {'show_modal': False})

def user_home(request):
    return render(request, 'user_home.html')