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


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ["outfit", "start_date", "end_date", "confirmed"]
    list_filter = ["confirmed", "start_date"]
    search_fields = ["outfit__model_code"]
    fields = ["outfit", "start_date", "end_date", "confirmed", "notes"]


@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    list_display = [
        "bill_number",
        "customer_name",
        "customer_phone",
        "confirmed",
        "payment_status",
        "created_at",
        "total_amount",
        "remaining_due",
    ]
    list_filter = ["confirmed", "payment_status", "created_at"]
    search_fields = ["bill_number", "customer_name", "customer_phone"]
    readonly_fields = ["bill_number", "created_at", "total_amount", "remaining_due"]

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