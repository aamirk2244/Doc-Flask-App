# Data Verifier (Flask)

Small Flask app that allows uploading an initial Excel/CSV file as a reference and uploading another file to compare against it. The app finds mismatches per-user (by Account ID or CNIC) and lists errored columns.

Quick start

1. Create a virtualenv and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Run the app:

```bash
python app.py
```

3. Open http://127.0.0.1:5000 in your browser.

Usage notes

- Upload the initial reference file via the left form. It will be saved to `data/initial.xlsx` or `data/initial.csv` depending on file type.
- Upload the file to verify via the right form; the app will automatically compare and show mismatches.
- The app matches rows by the first column that contains `Account` or `CNIC` in its header; adjust code `find_key_column` in `app.py` if needed.

Design notes

- Simple, modular structure to make adding future calculations or additional buttons easy. Templates live under `templates/`, static assets under `static/`.
- Comparison logic is in `compare_data()` in `app.py` and returns a list of result objects with status and mismatch details.
