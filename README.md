# Ben's Breads

A Django site: blog, recipes, Ramsey (bio, gallery, profile with vaccines/boarding/diet), games (Connect 4, Word Find), and reviews.

## Setup

1. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. Optional: copy `.env.example` to `.env` and set:
   - `DEBUG=true` for local dev
   - `DJANGO_SECRET_KEY` (required in production)
   - `DATABASE_URL` for PostgreSQL (omit for SQLite)
   - `GOOGLE_PLACES_API_KEY` for review place search
   - `AWS_*` and `MEDIA_ROOT` for production media

3. Run migrations and start the server:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

4. Create a superuser: `python manage.py createsuperuser`

## Project layout

- **bensbreads/** — Django project (settings, root URLs, WSGI/ASGI)
- **main/** — App: models, views, forms, URLs, templates, static, Connect4 engine
- **static/main/** — CSS and JS
- **main/templates/** — Base and page templates

All features from the original site are implemented with new code; nothing is reused from `old/`.
