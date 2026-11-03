"""
Builds a single-file self-contained HTML artifact for the generative UI side pane.
Embeds the dashboard data directly into the HTML to ensure zero network/CORS dependencies.
"""

import os
import json

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_path = os.path.join(base_dir, "frontend", "index.html")
data_path = os.path.join(base_dir, "frontend", "dashboard_data.json")

with open(html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

with open(data_path, "r", encoding="utf-8") as f:
    data_content = f.read()

# Inline the dataset
inline_data_script = f"<script>window.DASHBOARD_DATA = {data_content};</script>"
standalone_html = html_content.replace('<script src="dashboard_data.js"></script>', inline_data_script)

artifact_dir = r"C:\Users\tejas\.gemini\antigravity\brain\185aea72-7ca7-4b17-839e-26a06545b3be"
os.makedirs(artifact_dir, exist_ok=True)
artifact_file = os.path.join(artifact_dir, "interactive_dashboard.html")

with open(artifact_file, "w", encoding="utf-8") as f:
    f.write(standalone_html)

print(f"Successfully generated standalone artifact: {artifact_file} ({len(standalone_html)} bytes)")
