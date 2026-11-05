# Ben's Breads

One Django codebase that serves two sites from the same database and login:

| Site | `SITE_ROLE` | Contents |
|------|-------------|----------|
| bensbreads.com | `main` (default) | Home, recipes, ordering, login/signup, user management, Django admin |
| playground.bensbreads.com | `playground` | Blog, games (Connect 4, Word Find, Starhold), Ramsey |

Login only happens on the main site. The playground sends users to the main
site's `/login/` and they come back afterward. The session cookie is scoped to
`.bensbreads.com`, so both subdomains see the same login.

## Setup

1. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. Create `.env` with:
   - `debug_bool=true` for local dev (uses SQLite and local media)
   - `django_secret` — Django secret key
   - `db_url` — PostgreSQL URL (used when `debug_bool` is false)
   - `media_root`, `AWS_*` for production media

3. Run migrations and start both sites (cookies on `localhost` are shared across
   ports, so logging in on one logs you in on the other):
   ```bash
   python manage.py migrate
   python manage.py runserver 8000                        # main site
   SITE_ROLE=playground python manage.py runserver 8001   # playground
   ```

4. Create a superuser: `python manage.py createsuperuser`

## Deploying on Render

Both services deploy from this repo with the same build and start commands
(`gunicorn bensbreads.wsgi`). They must share these env vars:
`django_secret`, `db_url`, `media_root` and the `AWS_*` values.

| Env var | Main service | Playground service |
|---------|--------------|--------------------|
| `SITE_ROLE` | `main` | `playground` |
| `MAIN_SITE_URL` | optional, defaults to `https://bensbreads.com` | same |
| `PLAYGROUND_SITE_URL` | optional, defaults to `https://playground.bensbreads.com` | same |
| `SESSION_COOKIE_DOMAIN` | optional, defaults to `.bensbreads.com` | same |

Run `python manage.py migrate` from the main service only.

## Project layout

- **bensbreads/** — Django project: settings, `urls.py` (main site), `urls_playground.py` (playground)
- **main/** — Models and migrations shared by both sites (recipes, blog, games, Ramsey), plus the main site's views, forms, URLs and templates (home, recipes, auth, user management). `templatetags/site_urls.py` provides `{% main_url %}` / `{% playground_url %}` for links between the sites.
- **orders/** — Order page on the main site (`/order/`): products with photos and categories, a session cart, checkout (login required, no payment), order history, and staff order management. Superusers manage products; staff and superusers manage orders.
- **playground/** — The playground's views, forms, URLs and templates (blog, games, Ramsey), plus the Connect 4 engine
- **static/main/** — CSS, JS and images used by both sites
