# Clothing Rental Manager

A simple internal clothing-rental management system built with Django.

It is designed for company staff—not customers. Staff can browse the outfit catalogue, check availability, select multiple outfits for one rental period, and create a booking. Admin can view complete rental bills and print them.

## Main features

- Category-based outfit catalogue
- Outfit photos
- Model and size tracking
- Each model-size combination is one physical outfit
- Date and time availability checks
- Prevention of overlapping bookings
- One rental period for all outfits in a booking
- Multiple outfits in one rental/bill
- Customer name and phone number
- Deposit amount, advance amount, payment status, and remaining dues
- Admin-only rental/billing records
- Printable bill page
- Staff login support through Django Admin

## Technology used

- Python
- Django
- SQLite database for development
- Django Templates
- Bootstrap 5
- Pillow for outfit photo uploads

## Project structure

```text
clothing-rental/
├── config/                 # Django project settings and URLs
├── rentals/                # Main rental-management app
│   ├── migrations/
│   ├── templates/
│   │   ├── rentals/        # Staff catalogue and booking pages
│   │   └── admin/          # Custom rental bill and print templates
│   ├── admin.py
│   ├── models.py
│   ├── urls.py
│   └── views.py
├── media/                  # Uploaded outfit photos
├── manage.py
└── requirements.txt
```

## Data structure

```text
Category
  └── Outfit
        ├── Model code: KT-1, IW-2, etc.
        ├── Size: 38, 40, 42, 44
        ├── Rental price
        └── Photo

Rental / Bill
  ├── Bill number
  ├── Customer details
  ├── Booking and return date/time
  ├── Deposit and advance
  ├── Payment status
  └── Booking items
        └── Each selected outfit
```

A `Rental` is the main bill. Each `Booking` connects one outfit to that rental.

## Setup

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Install required packages:

```bash
pip install django Pillow
```

Apply database changes:

```bash
python manage.py makemigrations
python manage.py migrate
```

Create the admin account:

```bash
python manage.py createsuperuser
```

Start the project:

```bash
python manage.py runserver
```

Open the staff catalogue:

```text
http://127.0.0.1:8000/
```

Open Django Admin:

```text
http://127.0.0.1:8000/admin/
```

## Admin setup

Before creating bookings, add:

1. Categories, such as Koti Kurta, Indo Western, Jodhpuri, and Blazers.
2. Outfits under each category.
3. A model code and size for each physical outfit.
4. A rental price and photo for each outfit.

Example:

```text
Category: Koti Kurta
Model: KT-1
Size: 40
Rental price: ₹1500
```

## Staff booking workflow

1. Log in through Django Admin.
2. Open the catalogue home page.
3. Select one booking start time and return time.
4. Open a category.
5. Open an outfit model.
6. Check available sizes.
7. Add one or more outfits to the current booking.
8. Enter customer and payment information.
9. Create the booking.

The system blocks an outfit from being booked when its rental period overlaps with an existing rental.

## Roles

### Staff

Staff users can:

- Browse the catalogue
- Check outfit availability
- Create bookings
- Manage permitted inventory records through Django Admin

### Admin

The Django superuser/admin can also:

- View complete rental/bill records
- See all outfits attached to a rental
- View payment information and remaining dues
- Print or save bills as PDF

## Photo uploads

Outfit images are stored in:

```text
media/outfit_photos/
```

For development, Django serves uploaded photos automatically while `DEBUG = True`.

## Future improvements

- PostgreSQL database for production
- Multiple photos for each outfit design
- Search and filters in the catalogue
- Booking edit and cancellation flow
- Return confirmation and deposit return tracking
- Better payment history
- Reports for daily rentals, pending dues, and popular outfits
- Professional company logo and branding on printed bills
- Production deployment with secure settings