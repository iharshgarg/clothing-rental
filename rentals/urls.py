from django.urls import path

from . import views

urlpatterns = [
    path("", views.category_list, name="category_list"),
    path("rental-period/", views.set_rental_period, name="set_rental_period"),
    path(
        "category/<int:category_id>/",
        views.outfit_catalogue,
        name="outfit_catalogue",
    ),
    path(
        "category/<int:category_id>/outfit/<int:outfit_id>/",
        views.outfit_detail,
        name="outfit_detail",
    ),
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:size_id>/", views.add_to_cart, name="add_to_cart"),
    path(
        "cart/remove/<int:item_index>/",
        views.remove_from_cart,
        name="remove_from_cart",
    ),
    path("cart/complete/", views.complete_booking, name="complete_booking"),
]