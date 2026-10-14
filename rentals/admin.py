from django.contrib import admin

from .models import Booking, Category, Outfit, Rental


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Outfit)
class OutfitAdmin(admin.ModelAdmin):
    list_display = ["model_code", "category", "size", "rental_price", "active"]
    list_filter = ["category", "size", "active"]
    search_fields = ["model_code"]


class BookingInline(admin.TabularInline):
    model = Booking
    extra = 0
    can_delete = False

    fields = ["outfit"]
    readonly_fields = ["outfit"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
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
        "outfit",
        "rental_bill_number",
        "rental_period",
    ]

    search_fields = [
        "outfit__model_code",
        "rental__bill_number",
        "rental__customer_name",
        "rental__customer_phone",
    ]

    fields = [
        "rental_bill_number",
        "rental_period",
        "outfit",
        "notes",
    ]

    readonly_fields = [
        "rental_bill_number",
        "rental_period",
    ]

    @admin.display(description="Bill number", ordering="rental__bill_number")
    def rental_bill_number(self, obj):
        if obj.rental:
            return obj.rental.bill_number
        return "No bill linked"

    @admin.display(description="Rental period")
    def rental_period(self, obj):
        if obj.rental and obj.rental.start_date and obj.rental.end_date:
            return (
                f"{obj.rental.start_date:%d %b %Y, %I:%M %p} "
                f"to {obj.rental.end_date:%d %b %Y, %I:%M %p}"
            )
        return "Not set"