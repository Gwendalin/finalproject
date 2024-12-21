import requests
from django.shortcuts import render
from datetime import datetime
import random

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])

def generate_time_based_color():
    # Use the current time to seed the random number generator for repeatability within a session
    now = datetime.now()
    random.seed(now.hour * 3600 + now.minute * 60 + now.second)

    # Generate a random color
    return "#{:02x}{:02x}{:02x}".format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

def get_color_palette(request):
    # Check if the user has submitted a color or hex code
    if request.method == 'POST':
        # Retrieve the color from the form submission (color picker or HEX code)
        hex_color = request.POST.get('color') or request.POST.get('hex_code')  # Use whichever is available
        rgb_color = hex_to_rgb(hex_color)
        
        # Pass the selected color to the Colormind API, with "N" placeholders for random suggestions
        input_colors = [rgb_color, "N", "N", "N", "N"]
        response = requests.post('http://colormind.io/api/', json={"input": input_colors, "model": "default"})
    else:
        # Default palette generation with a time-based random color when no color is selected by the user
        hex_color = generate_time_based_color()
        rgb_color = hex_to_rgb(hex_color)
        
        # Generate a random palette based on the default color
        input_colors = [rgb_color, "N", "N", "N", "N"]
        response = requests.post('http://colormind.io/api/', json={"input": input_colors, "model": "default"})

    # Generate the palette if the response is successful
    if response.status_code == 200:
        palette = response.json().get('result', [])
        hex_palette = [rgb_to_hex(color) for color in palette]
        combined_palette = list(zip(palette, hex_palette))  # Paired RGB and HEX codes together
    else:
        combined_palette = []

    # Render the template with the generated palette and the selected or time-based default color
    return render(request, 'color_guidance.html', {
        'combined_palette': combined_palette,
        'default_color': hex_color  # Pass the time-based or user-selected color to the template
    })

