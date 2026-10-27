from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from .models import Booking, Category, Outfit, OutfitSize, Rental


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

    request.session["rental_period"] = {
        "start": start.isoformat(),
        "end": end.isoformat(),
    }
    request.session["rental_cart"] = []

    messages.success(request, "Rental period selected. You can now choose outfits.")
    return redirect("category_list")


def get_cart_items(request):
    size_ids = request.session.get("rental_cart", [])

    outfit_sizes = OutfitSize.objects.select_related("outfit").in_bulk(size_ids)

    return [
        {"outfit_size": outfit_sizes[size_id]}
        for size_id in size_ids
        if size_id in outfit_sizes
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
    outfits = Outfit.objects.filter(
        category=category,
        active=True,
    ).order_by("model_code")

    return render(
        request,
        "rentals/outfit_catalogue.html",
        {
            "category": category,
            "outfits": outfits,
        },
    )


@staff_required
def outfit_detail(request, category_id, outfit_id):
    start, end = get_rental_period(request)

    if not start or not end:
        messages.error(request, "Select the rental period first.")
        return redirect("category_list")

    category = get_object_or_404(Category, pk=category_id)
    outfit = get_object_or_404(
        Outfit,
        pk=outfit_id,
        category=category,
        active=True,
    )

    sizes = outfit.sizes.filter(active=True).order_by("size")

    booked_size_ids = set(
        Booking.objects.filter(
            outfit_size__in=sizes,
            rental__start_date__lte=end,
            rental__end_date__gte=start,
        ).values_list("outfit_size_id", flat=True)
    )

    for outfit_size in sizes:
        outfit_size.is_available = outfit_size.id not in booked_size_ids

    return render(
        request,
        "rentals/outfit_detail.html",
        {
            "category": category,
            "outfit": outfit,
            "sizes": sizes,
            "selected_start": start,
            "selected_end": end,
        },
    )


@staff_required
@require_POST
def add_to_cart(request, size_id):
    start, end = get_rental_period(request)

    outfit_size = get_object_or_404(
        OutfitSize.objects.select_related("outfit"),
        pk=size_id,
        active=True,
        outfit__active=True,
    )

    if not start or not end:
        messages.error(request, "Select the rental period first.")
        return redirect("category_list")

    is_booked = Booking.objects.filter(
        outfit_size=outfit_size,
        rental__start_date__lte=end,
        rental__end_date__gte=start,
    ).exists()

    if is_booked:
        messages.error(request, f"{outfit_size} is no longer available.")
        return redirect("category_list")

    cart = request.session.get("rental_cart", [])

    if outfit_size.id not in cart:
        cart.append(outfit_size.id)
        request.session["rental_cart"] = cart
        messages.success(request, f"{outfit_size} added to the booking.")

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
                additional_phone=request.POST.get("additional_phone", "").strip(),
                start_date=start,
                end_date=end,
                deposit_amount=request.POST.get("deposit_amount") or 0,
                advance_amount=request.POST.get("advance_amount") or 0,
                discount_amount=request.POST.get("discount_amount") or 0,
                payment_status=payment_status,
                confirmed=request.POST.get("confirmed") == "on",
                notes=request.POST.get("notes", ""),
                created_by=request.user,
            )

            for item in items:
                booking = Booking(
                    rental=rental,
                    outfit_size=item["outfit_size"],
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