from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.utils import timezone
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path

from .models import Booking, Category, Outfit, OutfitSize, Rental

def revenue_totals(rentals):
    sales = Decimal("0")
    paid = Decimal("0")
    outstanding = Decimal("0")

    for rental in rentals:
        outfit_total = sum(
            (
                booking.outfit_size.outfit.rental_price
                for booking in rental.bookings.all()
                if booking.outfit_size_id
            ),
            Decimal("0"),
        )

        net_sale = max(Decimal("0"), outfit_total - rental.discount_amount)
        amount_paid = min(rental.advance_amount, net_sale)
        due = max(Decimal("0"), net_sale - amount_paid)

        sales += net_sale
        paid += amount_paid
        outstanding += due

    return {
        "sales": sales,
        "paid": paid,
        "outstanding": outstanding,
    }

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ["name"]


class OutfitSizeInline(admin.TabularInline):
    model = OutfitSize
    extra = 1
    fields = ["size", "active"]


@admin.register(Outfit)
class OutfitAdmin(admin.ModelAdmin):
    list_display = ["model_code", "category", "rental_price", "active"]
    list_filter = ["category", "active"]
    search_fields = ["model_code"]
    inlines = [OutfitSizeInline]


class BookingInline(admin.TabularInline):
    model = Booking
    extra = 0
    can_delete = False

    fields = ["outfit_size", "outfit_price"]
    readonly_fields = ["outfit_size", "outfit_price"]

    @admin.display(description="Rental price")
    def outfit_price(self, obj):
        if not obj or not obj.outfit_size_id:
            return "-"
        return f"₹{obj.outfit_size.outfit.rental_price:.2f}"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    change_form_template = "admin/rentals/rental/change_form.html"
    change_list_template = "admin/rentals/rental/change_list.html"

    list_display = [
        "bill_number",
        "customer_name",
        "customer_phone",
        "confirmed",
        "pickup_ready",
        "payment_status",
        "created_at",
        "outfit_total",
        "balance_due",
    ]
    list_filter = ["confirmed", "payment_status", "created_at"]
    search_fields = ["bill_number", "customer_name", "customer_phone", "additional_phone"]
    inlines = [BookingInline]

    readonly_fields = [
        "bill_number",
        "created_at",
        "created_by",
        "outfit_total",
        "net_total",
        "balance_due",
    ]

    fieldsets = (
        (
            "Bill details",
            {
                "fields": (
                    "bill_number",
                    "created_at",
                    "created_by",
                    "confirmed",
                )
            },
        ),
        (
            "Customer",
            {
                "fields": (
                    "customer_name",
                    "customer_phone",
                    "additional_phone",
                )
            },
        ),
        (
            "Rental period",
            {
                "fields": (
                    "start_date",
                    "end_date",
                    "pickup_ready",
                )
            },
        ),
        (
            "Payment",
            {
                "fields": (
                    "deposit_amount",
                    "advance_amount",
                    "discount_amount",
                    "payment_status",
                    "outfit_total",
                    "net_total",
                    "balance_due",
                )
            },
        ),
        (
            "Additional notes",
            {
                "fields": (
                    "notes",
                )
            },
        ),
    )

    @admin.display(description="Outfit total")
    def outfit_total(self, obj):
        return f"₹{obj.total_amount:.2f}"

    @admin.display(description="Total after discount")
    def net_total(self, obj):
        return f"₹{obj.net_amount:.2f}"

    @admin.display(description="Remaining due")
    def balance_due(self, obj):
        return f"₹{obj.remaining_due:.2f}"

    def get_urls(self):
        custom_urls = [
            path(
                "upcoming-pickups/",
                self.admin_site.admin_view(self.upcoming_pickups),
                name="rentals_upcoming_pickups",
            ),
            path(
                "pickups/<int:rental_id>/mark-ready/",
                self.admin_site.admin_view(self.mark_pickup_ready),
                name="rentals_mark_pickup_ready",
            ),
            path(
                "revenue/",
                self.admin_site.admin_view(self.revenue_overview),
                name="rentals_revenue_overview",
            ),
            path(
                "<int:rental_id>/print/",
                self.admin_site.admin_view(self.print_bill),
                name="rentals_rental_print",
            ),
        ]
        return custom_urls + super().get_urls()

    def upcoming_pickups(self, request):
        today = timezone.localdate()

        today_start = timezone.make_aware(
            datetime.combine(today, time.min)
        )
        tomorrow_start = today_start + timedelta(days=1)
        day_after_tomorrow = tomorrow_start + timedelta(days=1)
        future_end = day_after_tomorrow + timedelta(days=7)

        base_queryset = Rental.objects.prefetch_related(
            "bookings__outfit_size__outfit"
        ).order_by("start_date")

        today_pickups = base_queryset.filter(
            start_date__gte=today_start,
            start_date__lt=tomorrow_start,
        )

        tomorrow_pickups = base_queryset.filter(
            start_date__gte=tomorrow_start,
            start_date__lt=day_after_tomorrow,
        )

        upcoming_pickups = base_queryset.filter(
            start_date__gte=day_after_tomorrow,
            start_date__lt=future_end,
        )

        return TemplateResponse(
            request,
            "admin/rentals/upcoming_pickups.html",
            {
                **self.admin_site.each_context(request),
                "title": "Upcoming pickups",
                "today_pickups": today_pickups,
                "tomorrow_pickups": tomorrow_pickups,
                "upcoming_pickups": upcoming_pickups,
            },
        )


    def mark_pickup_ready(self, request, rental_id):
        if request.method != "POST":
            return redirect("admin:rentals_upcoming_pickups")

        rental = get_object_or_404(Rental, pk=rental_id)
        rental.pickup_ready = True
        rental.save(update_fields=["pickup_ready"])

        self.message_user(
            request,
            f"{rental.bill_number} marked ready for pickup.",
        )

        return redirect("admin:rentals_upcoming_pickups")

    def revenue_overview(self, request):
        if not request.user.is_superuser:
            raise PermissionDenied

        rentals = list(
            Rental.objects.prefetch_related(
                "bookings__outfit_size__outfit"
            ).order_by("-created_at")
        )

        today = timezone.localdate()
        monthly_groups = defaultdict(list)
        yearly_groups = defaultdict(list)

        current_month_rentals = []
        current_year_rentals = []

        for rental in rentals:
            rental_date = timezone.localtime(rental.created_at).date()

            monthly_groups[(rental_date.year, rental_date.month)].append(rental)
            yearly_groups[rental_date.year].append(rental)

            if (
                rental_date.year == today.year
                and rental_date.month == today.month
            ):
                current_month_rentals.append(rental)

            if rental_date.year == today.year:
                current_year_rentals.append(rental)

        monthly_data = [
            {
                "label": date(year, month, 1).strftime("%B %Y"),
                **revenue_totals(group),
            }
            for (year, month), group in sorted(
                monthly_groups.items(),
                reverse=True,
            )
        ]

        yearly_data = [
            {
                "label": str(year),
                **revenue_totals(group),
            }
            for year, group in sorted(
                yearly_groups.items(),
                reverse=True,
            )
        ]

        return TemplateResponse(
            request,
            "admin/rentals/revenue_overview.html",
            {
                **self.admin_site.each_context(request),
                "title": "Revenue overview",
                "current_month": revenue_totals(current_month_rentals),
                "current_year": revenue_totals(current_year_rentals),
                "monthly_data": monthly_data,
                "yearly_data": yearly_data,
            },
        )

    def print_bill(self, request, rental_id):
        if not request.user.is_superuser:
            raise PermissionDenied

        rental = get_object_or_404(Rental, pk=rental_id)
        bookings = rental.bookings.select_related("outfit_size__outfit").all()

        return TemplateResponse(
            request,
            "admin/rentals/rental/print_bill.html",
            {
                **self.admin_site.each_context(request),
                "rental": rental,
                "bookings": bookings,
            },
        )

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        "outfit_size",
        "rental_bill_number",
        "rental_period",
    ]

    search_fields = [
        "outfit_size__outfit__model_code",
        "rental__bill_number",
        "rental__customer_name",
        "rental__customer_phone",
    ]

    fields = [
        "rental_bill_number",
        "rental_period",
        "outfit_size",
        "notes",
    ]

    readonly_fields = [
        "rental_bill_number",
        "rental_period",
    ]

    @admin.display(description="Bill number", ordering="rental__bill_number")
    def rental_bill_number(self, obj):
        return obj.rental.bill_number

    @admin.display(description="Rental period")
    def rental_period(self, obj):
        return (
            f"{obj.rental.start_date:%d %b %Y, %I:%M %p} "
            f"to {obj.rental.end_date:%d %b %Y, %I:%M %p}"
        )