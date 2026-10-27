# Clothing Rental Manager

Internal Django software for tracking rental outfits, staff bookings, payments, and printable rental bills.


## Main features

- Category-based outfit catalogue
- Outfit photos stored in Cloudinary
- Size-level inventory tracking
- Date-and-time conflict prevention
- One rental period shared across all outfits in a bill
- Multiple outfits in one rental/bill
- Deposit, advance, payment status, and remaining balance tracking
- Admin-only billing records and printable bills
- Staff access for catalogue and booking work

## Project structure

```text
clothing-rental/
├── config/
│   ├── settings.py       # Django settings
│   ├── urls.py           # Main URLs
│   └── wsgi.py           # Production web-server entry point
├── rentals/
│   ├── models.py         # Category, Outfit, Rental, Booking
│   ├── views.py          # Catalogue and booking workflow
│   ├── admin.py          # Admin billing and printable bill setup
│   ├── urls.py           # Rental application URLs
│   ├── templates/        # Catalogue, booking, admin, and bill templates
│   └── management/
│       └── commands/
│           └── ensure_admin.py
├── manage.py
├── requirements.txt
├── build.sh
├── .python-version
└── .env                 # Private local secrets — never commit this file
```

## Main data structure

```text
Category
  └─ Outfit
       ├─ model code
       ├─ size
       ├─ rental price
       └─ Cloudinary photo

Rental / Bill
  ├─ bill number
  ├─ customer information
  ├─ one booking and return date/time
  ├─ deposit and advance
  ├─ payment status
  └─ Booking items
       ├─ Outfit 1
       ├─ Outfit 2
       └─ Outfit 3
```

A `Booking` does not separately store booking dates. It gets the rental period from its linked `Rental`, which avoids inconsistent dates across outfits in the same bill.

## Local setup

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create `.env`

Create a `.env` file beside `manage.py`:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

PGHOST=your-neon-hostname
PGDATABASE=neondb
PGUSER=your-neon-username
PGPASSWORD=your-neon-password
PGPORT=5432

CLOUDINARY_URL=cloudinary://your-api-key:your-api-secret@your-cloud-name
```

Never commit `.env` to GitHub.

### 4. Create database tables

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create a local admin account

```bash
python manage.py createsuperuser
```

### 6. Start the project

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

Admin panel:

```text
http://127.0.0.1:8000/admin/
```

## Everyday commands

```bash
source .venv/bin/activate
python manage.py runserver
```

Create migrations after changing models:

```bash
python manage.py makemigrations
python manage.py migrate
```

Check deployment readiness:

```bash
python manage.py check --deploy
python manage.py collectstatic --noinput
```

## User access

- **Superuser/Admin:** Can view rental bills, payment information, balances, and printable bills.
- **Staff user:** Can use the internal catalogue and create bookings. Staff status must be enabled for the account.

## Neon database

Neon provides the PostgreSQL database.

The connection details are stored as these environment variables:

```text
PGHOST
PGDATABASE
PGUSER
PGPASSWORD
PGPORT
```

After creating a new Neon database, run:

```bash
python manage.py migrate
```

This creates all Django tables in Neon.

## Cloudinary images

Cloudinary stores outfit photos permanently outside Render’s temporary filesystem.

The required environment variable is:

```text
CLOUDINARY_URL
```

New photos uploaded through Django Admin are sent directly to Cloudinary.

## Render deployment

Render uses:

```text
Build command: ./build.sh
Start command: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

`build.sh`:

```bash
#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py ensure_admin
```

Make the script executable once:

```bash
chmod +x build.sh
```

### Render environment variables

Add these in the Render dashboard:

```text
SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=your-service-name.onrender.com
CSRF_TRUSTED_ORIGINS=https://your-service-name.onrender.com

PGHOST
PGDATABASE
PGUSER
PGPASSWORD
PGPORT

CLOUDINARY_URL

DJANGO_SUPERUSER_USERNAME
DJANGO_SUPERUSER_EMAIL
DJANGO_SUPERUSER_PASSWORD
```

`ensure_admin` creates the first admin account during deployment, because Render Free does not provide Shell access. It does not overwrite the password on later deployments.

## Important notes

- Render Free can sleep after inactivity, so the first request may take time.
- Render does not store local uploads permanently. Always use Cloudinary for photos.
- Neon and Cloudinary credentials must remain private.
- Keep a regular backup/export of important rental data.
- Do not delete existing migrations after deployment.