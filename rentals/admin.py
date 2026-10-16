from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path

from .models import Booking, Category, Outfit, OutfitSize, Rental


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

    list_display = [
        "bill_number",
        "customer_name",
        "customer_phone",
        "confirmed",
        "payment_status",
        "created_at",
        "outfit_total",
        "balance_due",
    ]
    list_filter = ["confirmed", "payment_status", "created_at"]
    search_fields = ["bill_number", "customer_name", "customer_phone"]
    inlines = [BookingInline]

    readonly_fields = [
        "bill_number",
        "created_at",
        "created_by",
        "outfit_total",
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
                )
            },
        ),
        (
            "Rental period",
            {
                "fields": (
                    "start_date",
                    "end_date",
                )
            },
        ),
        (
            "Payment",
            {
                "fields": (
                    "deposit_amount",
                    "advance_amount",
                    "payment_status",
                    "outfit_total",
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

    @admin.display(description="Remaining due")
    def balance_due(self, obj):
        return f"₹{obj.remaining_due:.2f}"

    def get_urls(self):
        custom_urls = [
            path(
                "<int:rental_id>/print/",
                self.admin_site.admin_view(self.print_bill),
                name="rentals_rental_print",
            ),
        ]
        return custom_urls + super().get_urls()

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