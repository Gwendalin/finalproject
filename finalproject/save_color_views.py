from django.shortcuts import render

def saved_colors(request):
    return render(request, "saved_color.html")
