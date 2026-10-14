from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import Booking, Category, Outfit


def get_selected_period(request):
    start = parse_datetime(request.GET.get("start", ""))
    end = parse_datetime(request.GET.get("end", ""))

    if start and timezone.is_naive(start):
        start = timezone.make_aware(start)

    if end and timezone.is_naive(end):
        end = timezone.make_aware(end)

    return start, end


def category_list(request):
    categories = Category.objects.all().order_by("name")
    return render(request, "rentals/category_list.html", {"categories": categories})


def outfit_catalogue(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    outfits = Outfit.objects.filter(category=category, active=True).order_by(
        "model_code", "size"
    )

    # One card per design/model, rather than one card for every size.
    model_cards = {}
    for outfit in outfits:
        if outfit.model_code not in model_cards:
            model_cards[outfit.model_code] = outfit

    return render(
        request,
        "rentals/outfit_catalogue.html",
        {
            "category": category,
            "model_cards": model_cards.values(),
        },
    )


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