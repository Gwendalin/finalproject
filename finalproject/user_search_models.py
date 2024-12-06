from django.db import models

class UserSearch(models.Model): 
    user_id = models.CharField(max_length=255) 
    search_keyword = models.CharField(max_length=255) 
    timestamp = models.DateTimeField(auto_now_add=True)
