from django.shortcuts import render, redirect
from .firebase import get_user_profile, update_user_profile, delete_user_account

def edit_profile_view(request):
    # Retrieve user ID from session
    user_id = request.session.get('user_id')
    
    if not user_id:
        return redirect('login') 
    
    # Retrieve user profile information
    user_profile = get_user_profile(user_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')

        print(f"Received POST request with data: name={name}, email={email}, phone={phone}")

        updated_successfully = update_user_profile(user_id, name=name, email=email, phone=phone)

        # Update the user profile
        if updated_successfully:
            print("Profile updated successfully.")
            # Refresh user profile data after update
            return redirect('profile')
        else:
            print("Failed to update profile.")
    
    return render(request, 'edit_profile.html', {
        'user_profile': user_profile
    })

def delete_account_view(request):
    user_id = request.session.get('user_id')

    if not user_id:
        print("No user ID found in session. Redirecting to login.")
        return redirect('login') 
    
    if delete_user_account(user_id):
        print("Account deleted successfully.")
        return redirect('guest_home') 
    else:
        print("Failed to delete account.")
        return redirect('profile') 
