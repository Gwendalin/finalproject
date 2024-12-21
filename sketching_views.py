from django.shortcuts import render

def sketching(request):
    user_id = request.session.get('user_id')
    return render(request, '2d_sketch.html', {'user_id': user_id})
