@echo off

if exist ".env\" goto run

echo Preparing virtual environment to run Minesweeper in Python...
python -m venv .env
.env\Scripts\pip install -r requirements.txt
echo Done!

:run
echo Starting Minesweeper in Python!
start .env\Scripts\pythonw main.py
