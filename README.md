# Clothing Rental Manager

Internal Django software for managing clothing rentals, outfit availability, staff bookings, payments, printable bills, and upcoming pickup preparation.

This is an internal company tool. Customers do not log in or book directly.

## Main features

- Category-based visual outfit catalogue
- Outfit photos stored permanently in Cloudinary
- One outfit model can have multiple sizes
- Size-level inventory and availability tracking
- Date-and-time overlap prevention for each outfit size
- One rental period shared by every outfit in a bill
- Multiple outfits in one rental/bill
- Customer primary and additional phone numbers
- Deposit, advance, discount, payment status, and outstanding balance tracking
- Admin-only billing details and printable bills
- Revenue overview for monthly and yearly sales
- Upcoming pickups board for preparing outfits before pickup
- Mark pickup as ready
- Staff catalogue and booking workflow
- Admin account automatically created during Render deployment

## Project structure

```text
clothing-rental/
├── config/
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── rentals/
│   ├── migrations/
│   ├── management/
│   │   └── commands/
│   │       └── ensure_admin.py
│   ├── templates/
│   │   ├── rentals/
│   │   │   ├── base.html
│   │   │   ├── cart.html
│   │   │   ├── category_list.html
│   │   │   ├── outfit_catalogue.html
│   │   │   └── outfit_detail.html
│   │   └── admin/
│   │       └── rentals/
│   │           ├── rental/
│   │           │   ├── change_form.html
│   │           │   ├── change_list.html
│   │           │   └── print_bill.html
│   │           ├── revenue_overview.html
│   │           └── upcoming_pickups.html
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── .env
├── .gitignore
├── .python-version
├── README.md
├── build.sh
├── manage.py
└── requirements.txt
```

## Main data structure

```text
Category
  └── Outfit
       ├── model code
       ├── rental price
       ├── photo
       └── Outfit sizes
            ├── Size 38
            ├── Size 40
            ├── Size 42
            └── Size 44

Rental / Bill
  ├── bill number
  ├── customer name
  ├── primary phone number
  ├── additional phone number
  ├── pickup date and time
  ├── return date and time
  ├── deposit amount
  ├── advance amount
  ├── discount amount
  ├── payment status
  ├── pickup ready status
  └── Booking items
       ├── Outfit model
       ├── Selected size
       └── Rental price
```

A `Booking` belongs to a `Rental` bill. It does not keep separate pickup and return dates. Every booking uses the common rental period from its linked bill, preventing inconsistent dates across one bill.

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

Create `.env` beside `manage.py`:

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

### 4. Create migration files and database tables

For a new local database:

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

Catalogue: `http://127.0.0.1:8000/`

Admin: `http://127.0.0.1:8000/admin/`

## Everyday local commands

```bash
source .venv/bin/activate
python manage.py runserver
```

After changing `models.py`:

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

### Superuser / Admin

Admins can manage categories, outfits, sizes, and photos; view bills and payment information; print bills; view revenue; access upcoming pickups; mark pickups ready; and manage staff users.

### Staff user

Staff can use the internal catalogue, select rental dates, check size availability, add several outfits to a cart, and create bookings. Set `is_staff` for each staff account in Django Admin.

## Booking workflow

```text
Choose rental dates and times
        ↓
Open category
        ↓
Choose outfit model
        ↓
Choose available size
        ↓
Add one or more outfits to cart
        ↓
Enter customer and payment details
        ↓
Create rental bill and booking items
```

The system blocks a specific outfit size when it already has an overlapping booking. A booking starting after another booking's return time is allowed.

## Billing calculation

```text
Outfit total
- Discount amount
= Net rental amount

Net rental amount
- Advance amount
= Remaining outstanding amount
```

Deposit is tracked separately because it may be refundable.

## Upcoming pickups

Django Admin includes an Upcoming Pickups page that shows pickups today, tomorrow, and in the following seven days. It includes customer details, selected outfits and sizes, and a **Mark ready** action after the required outfits have been prepared.

This is intentionally a manual preparation board rather than an automatic notification system, keeping it simple and reliable on Render Free.

## Neon database

Neon provides the PostgreSQL database. Its connection details are supplied using:

```text
PGHOST
PGDATABASE
PGUSER
PGPASSWORD
PGPORT
```

For a brand-new Neon database, Django migrations create the required tables:

```bash
python manage.py migrate
```

Important:

- Do not delete migration files after deployment.
- Do not reset the production Neon database unless you intentionally want to remove all data.
- Do not run migrations locally if your `.env` points to production Neon unless you intend to change the production database.

## Cloudinary images

Cloudinary stores outfit photos permanently outside Render's temporary filesystem.

Required environment variable:

```text
CLOUDINARY_URL
```

Photos uploaded through Django Admin are stored directly in Cloudinary.

## Render deployment

Render commands:

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

Example:

```text
ALLOWED_HOSTS=clothing-rental.onrender.com
CSRF_TRUSTED_ORIGINS=https://clothing-rental.onrender.com
```

## Automatic admin account

`ensure_admin` runs on every Render deployment and creates the first admin user from:

```text
DJANGO_SUPERUSER_USERNAME
DJANGO_SUPERUSER_EMAIL
DJANGO_SUPERUSER_PASSWORD
```

It does not overwrite an existing admin user or reset its password. This avoids needing Render Shell access.

## Deploying model changes

When you change Django models:

```bash
python manage.py makemigrations
```

Commit and push the resulting migration file:

```bash
git add .
git commit -m "Add rental feature"
git push
```

Render redeploys automatically and runs `python manage.py migrate` through `build.sh`.

Do not delete old migration files from Git after production deployment.

## Important notes

- Render Free services can sleep after inactivity, so the first request may take time.
- Render does not permanently store local uploads; use Cloudinary for photos.
- Keep Neon, Cloudinary, Django secret keys, and admin passwords private.
- Never commit `.env`.
- Keep periodic backups of important rental and customer data.
- Use strong passwords for admin accounts.
- Take a Neon backup or branch before major database changes.
