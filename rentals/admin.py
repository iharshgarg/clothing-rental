from django.contrib import admin
from .models import Booking, Category, Outfit


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Outfit)
class OutfitAdmin(admin.ModelAdmin):
    list_display = [
        "model_code",
        "category",
        "size",
        "rental_price",
        "active",
    ]
    list_filter = ["category", "size", "active"]
    search_fields = ["model_code"]

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        "customer_name",
        "outfit",
        "start_date",
        "end_date",
        "confirmed",
        "payment_status",
    ]
    list_filter = ["confirmed", "payment_status", "start_date"]
    search_fields = ["customer_name", "customer_phone", "outfit__model_code"]