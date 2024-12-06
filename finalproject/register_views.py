import re
from django.shortcuts import render, redirect
from django.contrib import messages
from .firebase import register as firebase_register
from firebase_admin import db

def register(request):    
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm-password')

        errors = []
        
        # Check required fields
        if not name or not email or not phone or not password or not confirm_password:
            messages.error(request, "Please fill out all fields.")
            return redirect('register')

        # Password validation
        if len(password) < 8:
            messages.error(request, 'Password must be more than 8 characters.')
            return redirect('register')
        if not re.search(r'[A-Z]', password):
            messages.error(request, 'Password must contain at least one uppercase letter.')
            return redirect('register')
        if not re.search(r'[a-z]', password):
            messages.error(request, 'Password must contain at least one lowercase letter.')
            return redirect('register')
        if not re.search(r'[0-9]', password):
            messages.error(request, 'Password must contain at least one number.')
            return redirect('register')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            messages.error(request, 'Password must contain at least one special character.')
            return redirect('register')

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('register')
        
        try:
            # Attempt to register the user
            user = firebase_register(email, password)

            if not user:
                messages.error(request, 'Registration failed. Please try again.')
                return redirect('register')
            
            user_id = user["localId"]
            
            # If registration was successful, store user details
            data = {
                "name": name,
                "phone": phone,
                "email": email,
            }
            # Save user details in Firebase
            firebase_db = db.reference(f"users/{user_id}")
            firebase_db.set(data)

            messages.success(request, 'Account created successfully!')
            return redirect('login')
        except Exception as e:
            print(f"Error during registration: {e}")  # Print for debugging
            messages.error(request, 'Registration failed. Please try again.')
            return redirect('register')

    return render(request, 'register.html')
