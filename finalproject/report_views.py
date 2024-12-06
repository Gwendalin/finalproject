from django.shortcuts import render
import matplotlib.pyplot as plt
import io
import urllib, base64
from datetime import datetime, timedelta
#from .firebase import get_login_data

def report_main(request):
    return render(request, 'report.html')

