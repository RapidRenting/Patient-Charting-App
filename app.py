import sys
import os  # Added os import at the top
# Use base_dir based on whether the app is frozen (packaged) or not.
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.getcwd()

from flask import Flask, render_template, request, redirect, url_for
from jinja2 import Environment, FileSystemLoader
import csv
import datetime
import re

app = Flask(__name__)

# Define directories for entry data and output data using base_dir.
ENTRY_FOLDER = os.path.join(base_dir, "entry_data")
OUTPUT_FOLDER = os.path.join(base_dir, "output_data")
if not os.path.exists(ENTRY_FOLDER):
    os.makedirs(ENTRY_FOLDER)
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

@app.route('/', methods=['GET', 'POST'])
def index():
    today_str = datetime.date.today().strftime('%Y%m%d')
    selected_date = request.args.get('date', today_str)
    try:
        display_date = datetime.datetime.strptime(selected_date, "%Y%m%d").strftime('%b %d %Y')
    except ValueError:
        display_date = selected_date

    form_enabled = (selected_date == today_str)
    filename = os.path.join(ENTRY_FOLDER, f'charts_{selected_date}.csv')

    if request.method == 'POST' and form_enabled:
        treatment_details = request.form.get('treatment_details')
        clinical_impression = request.form.get('clinical_impression')
        client_feedback = request.form.get('client_feedback')
        home_care = request.form.get('home_care')
        recommended_treatment_plan = request.form.get('recommended_treatment_plan')
        timestamp = datetime.datetime.now().isoformat()
        file_exists = os.path.isfile(filename)
        with open(filename, mode='a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['treatment_details', 'clinical_impression', 'client_feedback', 'home_care', 'recommended_treatment_plan', 'timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                'treatment_details': treatment_details,
                'clinical_impression': clinical_impression,
                'client_feedback': client_feedback,
                'home_care': home_care,
                'recommended_treatment_plan': recommended_treatment_plan,
                'timestamp': timestamp
            })
        return redirect(url_for('index', date=selected_date))

    entries = []
    if os.path.exists(filename):
        with open(filename, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if 'timestamp' in row and row['timestamp']:
                    try:
                        ts = datetime.datetime.fromisoformat(row['timestamp'])
                        row['formatted_timestamp'] = ts.strftime('%b %d %Y - %I:%M:%S %p')
                    except Exception:
                        row['formatted_timestamp'] = row['timestamp']
                else:
                    row['formatted_timestamp'] = "No timestamp available"
                entries.append(row)

    available_dates = []
    pattern = re.compile(r'charts_(\d{8})\.csv')
    for f in os.listdir(ENTRY_FOLDER):
        m = pattern.match(f)
        if m:
            date_str = m.group(1)
            try:
                display = datetime.datetime.strptime(date_str, "%Y%m%d").strftime('%b %d %Y')
            except ValueError:
                display = date_str
            available_dates.append({'value': date_str, 'display': display})
    available_dates.sort(key=lambda x: x['value'], reverse=True)

    charts_generated = request.args.get('charts_generated')  # new line
    return render_template('form.html',
                           entries=entries,
                           display_date=display_date,
                           selected_date=selected_date,
                           available_dates=available_dates,
                           form_enabled=form_enabled,
                           charts_generated=charts_generated)  # updated

@app.route('/generate_charts', methods=['POST'])
def generate_charts():
    # Use selected date from query parameter or default to today's date
    selected_date = request.args.get('date', datetime.date.today().strftime('%Y%m%d'))
    csv_filename = os.path.join(ENTRY_FOLDER, f'charts_{selected_date}.csv')
    output_filename = os.path.join(OUTPUT_FOLDER, f'final_charts_{selected_date}.txt')
    generate_charts_from_csv(csv_filename, output_filename)
    return redirect(url_for('index', date=selected_date, charts_generated='true'))  # updated

def generate_charts_from_csv(csv_filename, output_filename):
    # Use an absolute path to the templates folder
    template_path = os.path.join(app.root_path, 'templates')
    env = Environment(loader=FileSystemLoader(template_path))
    template = env.get_template('chart_template.txt')
    charts_output = ""
    with open(csv_filename, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader, start=1):
            if 'timestamp' in row and row['timestamp']:
                try:
                    ts = datetime.datetime.fromisoformat(row['timestamp'])
                    formatted_timestamp = ts.strftime('%b %d %Y - %I:%M:%S %p')
                except Exception:
                    formatted_timestamp = row['timestamp']
            else:
                formatted_timestamp = "No timestamp available"
            data = {
                'patient_id': f"Patient {i:02d}",
                'session_date': datetime.date.today().strftime('%Y-%m-%d'),
                'treatment_details': row.get('treatment_details', ''),
                'clinical_impression': row.get('clinical_impression', ''),
                'client_feedback': row.get('client_feedback', ''),
                'home_care': row.get('home_care', ''),
                'recommended_treatment_plan': row.get('recommended_treatment_plan', ''),
                'formatted_timestamp': formatted_timestamp,
                'summary': f"Session notes for Patient {i:02d} reviewed and formatted."
            }
            charts_output += template.render(data) + "\n\n"
    with open(output_filename, mode='w', encoding='utf-8') as outfile:
        outfile.write(charts_output)
    print(f"Charts generated and saved to {output_filename}")

@app.route('/shutdown', methods=['POST'])
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        import sys
        sys.exit(0)  # Force exit if Werkzeug shutdown not available
    else:
        func()
    return 'Server shutting down...'

if __name__ == '__main__':
    import webbrowser
    port = 5000
    webbrowser.open(f'http://127.0.0.1:{port}/')
    app.run(debug=True, port=port)
