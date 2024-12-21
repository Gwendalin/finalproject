from django.http import HttpResponse
from django.shortcuts import render
from .firebase import get_daily_usage_data, generate_usage_graph
from datetime import datetime

def report_main(request):
    return render(request, 'report.html')

def generate_report(request):
    """Processes the date input and generates the user usage report."""
    if request.method == "POST":
        # Get user-selected date range
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')

        # Convert to datetime objects
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        except ValueError:
            return HttpResponse("<h3 style='color: red; text-align: center;'>Invalid date format. Please try again!</h3>")

        # Fetch usage data (from Firebase)
        daily_usage = get_daily_usage_data()

        # Filter usage data based on date range
        filtered_usage = {date: hours for date, hours in daily_usage.items() 
                  if start_date <= datetime.strptime(date, "%Y-%m-%d") <= end_date}

         # If no data is found
        if not filtered_usage:
            return render(request, 'user_usage_report.html', {
                'no_data': True,
                'start_date': start_date,
                'end_date': end_date
            })

        # Generate graph
        image_base64 = generate_usage_graph(filtered_usage)
        total_hours = sum(filtered_usage.values())

        return render(request, 'user_usage_report.html', {
            'image_base64': image_base64,
            'total_hours': round(total_hours, 2),
            'start_date': start_date,
            'end_date': end_date
        })
    else:
        return HttpResponse("<h3 style='color: red; text-align: center;'>Invalid request method. Use POST to submit data.</h3>")
