"""
URL configuration for finalproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from . import login_views
from . import register_views
from . import forgot_password_views
from . import guest_home_views
from . import sketching_views
from . import guidance_views
from . import profile_views
from . import edit_profile_views
from . import generate_model_views
from . import color_guidance_views
from . import report_views
from . import logout_views
from . import save_color_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', guest_home_views.guest_home, name='guest_home'),
    path('login/', login_views.login_view, name='login'),
    path('logout/', logout_views.logout_views, name='logout'),
    path('register/', register_views.register, name='register'),
    path('forgot_password/', forgot_password_views.forgot_password, name='forgot_password'),
    path('user_home/', login_views.user_home, name='user_home'),
    path('3d_model/', generate_model_views.generate_model, name='3d_model'),
    path('2d_sketch/', sketching_views.sketching, name='2d_sketch'),
    path('user_guidance/', guidance_views.user_guidance, name='user_guidance'),
    path('guest_guidance/', guidance_views.guest_guidance, name='guest_guidance'),
    path('profile/', profile_views.profile_view, name='profile'),
    path('edit_profile/', edit_profile_views.edit_profile_view, name='edit_profile'),
    path('report/', report_views.report_main, name='report'),
    path('user_usage_report/', report_views.generate_report, name='user_usage_report'),
    path('color_guidance/', color_guidance_views.get_color_palette, name='color_guidance'),
    path('saved_color/', save_color_views.saved_colors, name= 'saved_color'),
    path('delete_user/', edit_profile_views.delete_account_view, name='delete_user')
    
]
