from django.urls import path
from . import views

urlpatterns = [
    path("", views.category_list, name="category_list"),
    path("category/<int:category_id>/", views.outfit_catalogue, name="outfit_catalogue"),
    path(
        "category/<int:category_id>/outfit/<str:model_code>/",
        views.outfit_detail,
        name="outfit_detail",
    ),
]