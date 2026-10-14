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


def get_rental_period(request):
    period = request.session.get("rental_period", {})
    start = parse_datetime(period.get("start", ""))
    end = parse_datetime(period.get("end", ""))

    return start, end


@staff_required
@require_POST
def set_rental_period(request):
    start = parse_datetime(request.POST.get("start", ""))
    end = parse_datetime(request.POST.get("end", ""))

    if start and timezone.is_naive(start):
        start = timezone.make_aware(start)

    if end and timezone.is_naive(end):
        end = timezone.make_aware(end)

    if not start or not end or end < start:
        messages.error(request, "Please select a valid booking and return date/time.")
        return redirect("category_list")

    # Changing dates starts a fresh booking selection.
    request.session["rental_period"] = {
        "start": start.isoformat(),
        "end": end.isoformat(),
    }
    request.session["rental_cart"] = []

    messages.success(request, "Rental period selected. You can now choose outfits.")
    return redirect("category_list")


def get_cart_items(request):
    outfit_ids = request.session.get("rental_cart", [])
    outfits = Outfit.objects.in_bulk(outfit_ids)

    return [
        {"outfit": outfits[outfit_id]}
        for outfit_id in outfit_ids
        if outfit_id in outfits
    ]


@staff_required
def category_list(request):
    start, end = get_rental_period(request)
    categories = Category.objects.all().order_by("name")

    return render(
        request,
        "rentals/category_list.html",
        {
            "categories": categories,
            "selected_start": start,
            "selected_end": end,
        },
    )


@staff_required
def outfit_catalogue(request, category_id):
    start, end = get_rental_period(request)

    if not start or not end:
        messages.error(request, "Select the rental period first.")
        return redirect("category_list")

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
        {
            "category": category,
            "model_cards": model_cards.values(),
        },
    )


@staff_required
def outfit_detail(request, category_id, model_code):
    start, end = get_rental_period(request)

    if not start or not end:
        messages.error(request, "Select the rental period first.")
        return redirect("category_list")

    category = get_object_or_404(Category, pk=category_id)
    outfits = Outfit.objects.filter(
        category=category,
        model_code=model_code,
        active=True,
    ).order_by("size")

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
    start, end = get_rental_period(request)
    outfit = get_object_or_404(Outfit, pk=outfit_id, active=True)

    if not start or not end:
        messages.error(request, "Select the rental period first.")
        return redirect("category_list")

    is_booked = Booking.objects.filter(
        outfit=outfit,
        start_date__lte=end,
        end_date__gte=start,
    ).exists()

    if is_booked:
        messages.error(request, f"{outfit} is no longer available.")
        return redirect("category_list")

    cart = request.session.get("rental_cart", [])

    if outfit.id not in cart:
        cart.append(outfit.id)
        request.session["rental_cart"] = cart
        messages.success(request, f"{outfit} added to the booking.")

    return redirect("cart")


@staff_required
def cart_view(request):
    start, end = get_rental_period(request)

    if not start or not end:
        messages.error(request, "Select the rental period first.")
        return redirect("category_list")

    return render(
        request,
        "rentals/cart.html",
        {
            "items": get_cart_items(request),
            "selected_start": start,
            "selected_end": end,
        },
    )


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
    start, end = get_rental_period(request)
    items = get_cart_items(request)

    customer_name = request.POST.get("customer_name", "").strip()
    customer_phone = request.POST.get("customer_phone", "").strip()

    if not start or not end:
        messages.error(request, "Select the rental period first.")
        return redirect("category_list")

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
                start_date=start,
                end_date=end,
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
                    start_date=start,
                    end_date=end,
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
    request.session.pop("rental_period", None)

    messages.success(request, "Booking created successfully.")
    return redirect("category_list")