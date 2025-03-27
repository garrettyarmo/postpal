# PostPal

A Flask application with user authentication using Supabase.

## Features

- User registration and login using Supabase Authentication
- Protected routes that require authentication
- Dashboard page accessible only to logged-in users

## Prerequisites

- Python 3.7+
- Supabase account (for database and authentication)

## Setup

1. Clone the repository:
   ```
   git clone <repository-url>
   cd postpal
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows:
     ```
     venv\Scripts\activate
     ```
   - macOS/Linux:
     ```
     source venv/bin/activate
     ```

4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Copy `.env.example` to `.env` and fill in your Supabase credentials:
   ```
   cp .env.example .env
   ```
   
   Update the `.env` file with your Supabase URL and API key, which you can find in your Supabase project settings.

6. Run the application:
   ```
   flask run
   ```

## Supabase Setup

1. Create a new project in [Supabase](https://supabase.com/)
2. Go to the Authentication section and enable Email authentication
3. Copy your project URL and API key from Project Settings > API
4. Paste these values in your `.env` file

## Project Structure

```
postpal/
├── app/
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── script.js
│   └── templates/
│       ├── base.html
│       ├── dashboard.html
│       ├── index.html
│       ├── login.html
│       └── signup.html
├── .env
├── .env.example
├── .gitignore
├── app.py
├── README.md
└── requirements.txt
```

## License

This project is open source and available under the [MIT License](LICENSE). 