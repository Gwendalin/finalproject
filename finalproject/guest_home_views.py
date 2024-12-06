from django.shortcuts import render

def guest_home(request):
    return render(request, 'guest_home.html')