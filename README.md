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

## macOS executable (no terminal window)

Run the build script:

```bash
./build_mac.sh
```

Or manually use PyInstaller `--windowed` mode so the packaged app launches without Terminal:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt pyinstaller
pyinstaller --windowed --onedir --name "PatientCharting" --add-data "templates:templates" app.py
```

The app bundle will be created at `dist/PatientCharting.app`.

Packaged mac behavior:

- If the app is opened while an instance is already running on port `5000`, it will open the existing session.
- The packaged app auto-quits after about 45 seconds without page heartbeat activity (for example after closing the browser tab/window).

## Legacy Data Import

Import old CSV entries into the current database:

```bash
python3 import_legacy_data.py --db data/charting.db
```

Import into the packaged app database:

```bash
python3 import_legacy_data.py --db "$HOME/Library/Application Support/PatientCharting/data/charting.db"
```

## Data

Entries are stored locally in:

- `data/charting.db` while running from source
- `~/Library/Application Support/PatientCharting/data/charting.db` in packaged macOS builds
