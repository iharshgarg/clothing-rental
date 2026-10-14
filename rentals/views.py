from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from .models import Booking, Category, Outfit, Rental


def is_staff_user(user):
    return user.is_active and user.is_staff


staff_required = user_passes_test(is_staff_user, login_url="/admin/login/")


def get_selected_period(request):
    start = parse_datetime(request.GET.get("start", ""))
    end = parse_datetime(request.GET.get("end", ""))

    if start and timezone.is_naive(start):
        start = timezone.make_aware(start)

    if end and timezone.is_naive(end):
        end = timezone.make_aware(end)

    return start, end


def get_cart_items(request):
    cart = request.session.get("rental_cart", [])
    outfit_ids = [item["outfit_id"] for item in cart]
    outfits = Outfit.objects.in_bulk(outfit_ids)

    items = []
    for item in cart:
        outfit = outfits.get(item["outfit_id"])
        start = parse_datetime(item["start"])
        end = parse_datetime(item["end"])

        if outfit and start and end:
            items.append(
                {
                    "outfit": outfit,
                    "start": start,
                    "end": end,
                }
            )

    return items


@staff_required
def category_list(request):
    categories = Category.objects.all().order_by("name")
    return render(request, "rentals/category_list.html", {"categories": categories})


@staff_required
def outfit_catalogue(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    outfits = Outfit.objects.filter(category=category, active=True).order_by(
        "model_code", "size"
    )

    model_cards = {}
    for outfit in outfits:
        model_cards.setdefault(outfit.model_code, outfit)

    return render(
        request,
        "rentals/outfit_catalogue.html",
        {"category": category, "model_cards": model_cards.values()},
    )


@staff_required
def outfit_detail(request, category_id, model_code):
    category = get_object_or_404(Category, pk=category_id)
    outfits = Outfit.objects.filter(
        category=category,
        model_code=model_code,
        active=True,
    ).order_by("size")

    start, end = get_selected_period(request)
    booked_outfit_ids = set()

    if start and end and end >= start:
        booked_outfit_ids = set(
            Booking.objects.filter(
                start_date__lte=end,
                end_date__gte=start,
            ).values_list("outfit_id", flat=True)
        )

    for outfit in outfits:
        outfit.is_available = outfit.id not in booked_outfit_ids

    return render(
        request,
        "rentals/outfit_detail.html",
        {
            "category": category,
            "model_code": model_code,
            "outfits": outfits,
            "selected_start": start,
            "selected_end": end,
        },
    )


@staff_required
@require_POST
def add_to_cart(request, outfit_id):
    outfit = get_object_or_404(Outfit, pk=outfit_id, active=True)
    start = parse_datetime(request.POST.get("start", ""))
    end = parse_datetime(request.POST.get("end", ""))

    if start and timezone.is_naive(start):
        start = timezone.make_aware(start)
    if end and timezone.is_naive(end):
        end = timezone.make_aware(end)

    if not start or not end or end < start:
        messages.error(request, "Please select a valid start and end date/time.")
        return redirect("category_list")

    is_booked = Booking.objects.filter(
        outfit=outfit,
        start_date__lte=end,
        end_date__gte=start,
    ).exists()

    if is_booked:
        messages.error(request, f"{outfit} is no longer available for that period.")
        return redirect("category_list")

    cart = request.session.get("rental_cart", [])
    cart = [item for item in cart if item["outfit_id"] != outfit.id]
    cart.append(
        {
            "outfit_id": outfit.id,
            "start": start.isoformat(),
            "end": end.isoformat(),
        }
    )
    request.session["rental_cart"] = cart

    messages.success(request, f"{outfit} added to the booking.")
    return redirect("cart")


@staff_required
def cart_view(request):
    return render(request, "rentals/cart.html", {"items": get_cart_items(request)})


@staff_required
@require_POST
def remove_from_cart(request, item_index):
    cart = request.session.get("rental_cart", [])

    if 0 <= item_index < len(cart):
        cart.pop(item_index)
        request.session["rental_cart"] = cart

    return redirect("cart")


@staff_required
@require_POST
def complete_booking(request):
    items = get_cart_items(request)
    customer_name = request.POST.get("customer_name", "").strip()
    customer_phone = request.POST.get("customer_phone", "").strip()

    if not items:
        messages.error(request, "Add at least one outfit before creating a booking.")
        return redirect("cart")

    if not customer_name or not customer_phone:
        messages.error(request, "Customer name and phone number are required.")
        return redirect("cart")

    valid_statuses = {value for value, _ in Rental.PaymentStatus.choices}
    payment_status = request.POST.get("payment_status", "unpaid")
    if payment_status not in valid_statuses:
        payment_status = "unpaid"

    try:
        with transaction.atomic():
            rental = Rental.objects.create(
                customer_name=customer_name,
                customer_phone=customer_phone,
                deposit_amount=request.POST.get("deposit_amount") or 0,
                advance_amount=request.POST.get("advance_amount") or 0,
                payment_status=payment_status,
                confirmed=request.POST.get("confirmed") == "on",
                notes=request.POST.get("notes", ""),
                created_by=request.user,
            )

            for item in items:
                booking = Booking(
                    rental=rental,
                    outfit=item["outfit"],
                    customer_name=rental.customer_name,
                    customer_phone=rental.customer_phone,
                    start_date=item["start"],
                    end_date=item["end"],
                    confirmed=rental.confirmed,
                    payment_status=rental.payment_status,
                    deposit_amount=rental.deposit_amount,
                    advance_amount=rental.advance_amount,
                    notes=rental.notes,
                )
                booking.full_clean()
                booking.save()

    except ValidationError as error:
        messages.error(request, "Could not create booking: " + "; ".join(error.messages))
        return redirect("cart")

    request.session["rental_cart"] = []
    messages.success(request, "Booking created successfully.")
    return redirect("category_list")