# Patient Charting App

Simple local Flask app for patient chart entries with in-page review, search, and delete.

## First-time setup (Windows PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
.\venv\Scripts\Activate.ps1
python app.py
```

Or run:

```powershell
.\run_app.ps1
```

The app opens at `http://127.0.0.1:5000/`.

## Data

Entries are stored locally in `data/charting.db`.
