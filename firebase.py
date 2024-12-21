import pyrebase
from django.shortcuts import render
import firebase_admin 
from firebase_admin import credentials, db
from firebase_admin import auth
import base64
import matplotlib.pyplot as plt
import datetime
import os
from django.conf import settings
import io

config = {
    "apiKey": "AIzaSyDyvnnQlWsTlO4Qfdj6EqBbHhcC-LNBLu4",
    "authDomain": "final-project-8018a.firebaseapp.com",
    "databaseURL": "https://final-project-8018a-default-rtdb.firebaseio.com",
    "projectId": "final-project-8018a",
    "storageBucket": "final-project-8018a.appspot.com",
    "messagingSenderId": "951767625787",
    "appId": "1:951767625787:web:ba80c0ad4ac3310e60ac1e"
}
firebase = pyrebase.initialize_app(config)
authentication = firebase.auth()
database = firebase.database()
storage = firebase.storage()

cred = credentials.Certificate("C:/Users/User/OneDrive/Documents/Final_Year_Project/final-project-8018a-firebase-adminsdk-7lrpf-6036b2a3c5.json")
firebase_admin.initialize_app(cred, { 'databaseURL': 'https://final-project-8018a-default-rtdb.firebaseio.com' })

def login(email, password):
    try:
        user = authentication.sign_in_with_email_and_password(email, password)
        # Check if the 'user' object is valid
        if 'idToken' in user:
            session_id = log_user_login(user['localId'])
            return user, session_id
        else:
            return None
    except Exception as e:
        print(f"Login failed: {e}")
        return None 

def log_user_login(user_id):
    """Log user login time in Firebase."""
    try:
        login_time = datetime.datetime.now().isoformat()  # Current time
        session_data = {
            "user_id": user_id,
            "login_time": login_time,
            "logout_time": None,  # To be updated later
        }
        print("Session data to be pushed:", session_data)  
        session_ref = database.child("user_sessions").push(session_data)
        print(f"Login time logged for user {user_id} at {login_time}")
        print("Firebase session reference:", session_ref)
        return session_ref['name']  # Return session ID (key)
    except Exception as e:
        print(f"Error logging login time: {e}")
        return None

def logout(session_id):
    try:
        # Log the logout time for this session
        if session_id:
            log_user_logout(session_id)
            print(f"User session {session_id} logged out successfully.")
        
        # Clear session ID or other session-related data
        return "User logged out successfully."
    except Exception as e:
        print(f"Logout failed: {e}")
        return "Logout failed."

def log_user_logout(session_id):
    """Update user logout time in Firebase."""
    try:
        logout_time = datetime.datetime.now().isoformat()  # Current time
        print(f"Updating logout time for session {session_id}: {logout_time}")
        database.child("user_sessions").child(session_id).update({
            "logout_time": logout_time
        })
        print(f"Logout time logged for session {session_id} at {logout_time}")
        return True
    except Exception as e:
        print(f"Error logging logout time: {e}")
        return False
    
def register(email, password):
    try:
        user = authentication.create_user_with_email_and_password(email, password)
        return user
    except Exception as e:
        print(f"Registration error: {e}")
        return None
    
def forgot_password(email):
    try:
        authentication.send_password_reset_email(email)
        return True 
    except Exception as e:
        return False 

def guest_home():
    return "Welcome to the guest home!" 

def user_home(request):
    return render(request, 'user_home.html')

def get_user_profile(user_id):
    print(f"Attempting to retrieve profile for user ID: {user_id}")
    try:
        # Replace this with your actual Firebase call
        user_data = database.child("users").child(user_id).get().val()
        if user_data:
            print(f"Retrieved user data for {user_id}: {user_data}") 
            return user_data
        else:
            print(f"No user data found for {user_id}") 
            return None
    except Exception as e:
        print(f"Error retrieving profile: {e}")
        return None  

def update_user_profile(user_id, name, email, phone):
    try:
        user_ref = db.reference(f'users/{user_id}')
        updates = {}
        
        if name:
            updates['name'] = name
        if email:
            updates['email'] = email
        if phone:
            updates['phone'] = phone

        if updates:
            user_ref.update(updates)
            print(f"User profile updated in Realtime Database for {user_id}")

        # Update in Firebase Authentication
        if email: 
            # Correct usage of the auth.update_user method 
            auth.update_user( uid=user_id, email=email ) 
            print(f"User profile updated in Firebase Authentication for {user_id} with email: {email}")

        updated_user_data = get_user_profile(user_id)
        return updated_user_data
    
    except Exception as e:
        print(f"Error updating profile for user {user_id}: {e}")
        return None
    
def delete_user_account(user_id):
    try:
        # Delete user from Realtime Database
        user_ref = db.reference(f'users/{user_id}')
        user_ref.delete()
        
        # Delete user from Firebase Authentication
        auth.delete_user(user_id)
        print(f"User account {user_id} deleted.")
        return True
    except Exception as e:
        print(f"Error deleting account for user {user_id}: {e}")
        return False  

def get_daily_usage_data():
    try:
        sessions = database.child("user_sessions").get().val()
        daily_usage = {}

        for session_id, session in sessions.items():
            login_time_str = session.get("login_time")
            logout_time_str = session.get("logout_time")

            if not login_time_str:
                print(f"Skipping session {session_id}: Missing 'login_time'")
            continue

        login_time = datetime.datetime.fromisoformat(login_time_str)
        logout_time = datetime.datetime.fromisoformat(logout_time_str) if logout_time_str else login_time

        # Calculate duration in hours
        duration = (logout_time - login_time).total_seconds() / 3600
        date = login_time.date().strftime('%Y-%m-%d')

        if date in daily_usage:
            daily_usage[date] += duration
        else:
            daily_usage[date] = duration

        return daily_usage
    except Exception as e:
        print(f"Error calculating daily usage: {e}")
    return {}
    
def generate_usage_graph(daily_usage):
    """Generate usage graph and return it as a base64-encoded image."""
    try:
        dates = list(daily_usage.keys())
        hours = list(daily_usage.values())

        plt.figure(figsize=(10, 6))
        plt.bar(dates, hours)
        plt.title('Daily System Usage')
        plt.xlabel('Date')
        plt.ylabel('Hours')
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Save the plot to a buffer and encode it to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()

        return image_base64
    except Exception as e:
        print(f"Error generating graph: {e}")
        return None
    


    







