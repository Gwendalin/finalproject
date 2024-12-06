from django.shortcuts import render

def user_guidance(request):
    return render(request, 'user_guidance.html')

def guest_guidance(request):
    return render(request, 'guest_guidance.html')