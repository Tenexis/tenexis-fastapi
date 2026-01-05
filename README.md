```
/my-project-root
  ├── /my-next-app         # Your existing Next.js frontend
  └── /backend             # Your new Python Backend
       ├── .env            # Store DATABASE_URL, GOOGLE_CLIENT_ID here
       ├── .gitignore      # Ignore venv and .env
       ├── requirements.txt
       ├── main.py         # The code I gave you earlier goes here
       └── /venv           # (Auto-generated) Python virtual environment
```

python -m venv venv
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000