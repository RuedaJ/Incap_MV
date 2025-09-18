# CLM MVP – Spatial Screening Backend (Python)

## Quickstart
```bash
# Python 3.10+
python -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e .
pip install -r requirements.txt

# Run tests
pytest

# Example: load portfolio CSV, geocode, and run screening (pseudo)
# (wire into your FastAPI worker)
