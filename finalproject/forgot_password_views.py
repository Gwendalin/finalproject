from django.shortcuts import render, redirect
from django.contrib import messages
from .firebase import forgot_password as send_password_reset

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        # Use the renamed function here
        if send_password_reset(email):
            messages.success(request, 'Password reset email sent!')
            return redirect('login')
        else:
            messages.error(request, 'Failed to send password reset email.')

    return render(request, 'forgot_password.html')
