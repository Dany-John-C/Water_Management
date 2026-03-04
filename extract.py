import os
import re

html_path = 'templates/index.html'
with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract CSS
style_match = re.search(r'<style>(.*?)</style>', content, re.DOTALL)
if style_match:
    css_content = style_match.group(1).strip()
    os.makedirs('static/css', exist_ok=True)
    with open('static/css/style.css', 'w', encoding='utf-8') as f:
        f.write(css_content)

# Extract JS
script_match = re.search(r'<script>\s*// Global variables(.*?)</script>', content, re.DOTALL)
if script_match:
    js_content = "// Global variables\n" + script_match.group(1).strip()
    os.makedirs('static/js', exist_ok=True)
    with open('static/js/main.js', 'w', encoding='utf-8') as f:
        f.write(js_content)

# Replace in HTML
if style_match and script_match:
    new_content = re.sub(r'<style>.*?</style>', '<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/style.css\') }}">', content, flags=re.DOTALL)
    new_content = re.sub(r'<script>\s*// Global variables.*?</script>', '<script src="{{ url_for(\'static\', filename=\'js/main.js\') }}"></script>', new_content, flags=re.DOTALL)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Extraction successful.")
else:
    print("Could not find style or script tags.")
