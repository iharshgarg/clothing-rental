from decimal import Decimal

from cloudinary.models import CloudinaryField
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Outfit(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    model_code = models.CharField(max_length=50, unique=True)
    rental_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    photo = CloudinaryField(
        "outfit photo",
        asset_folder="outfit_photos",
        use_asset_folder_as_public_id_prefix=True,
        blank=True,
        null=True,
    )
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.model_code


class OutfitSize(models.Model):
    outfit = models.ForeignKey(
        Outfit,
        on_delete=models.CASCADE,
        related_name="sizes",
    )
    size = models.CharField(max_length=10)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["outfit", "size"],
                name="unique_outfit_and_size",
            )
        ]

    def __str__(self):
        return f"{self.outfit.model_code} — Size {self.size}"


class Rental(models.Model):
    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PARTIAL = "partial", "Partially paid"
        PAID = "paid", "Paid"

    bill_number = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        null=True,
        editable=False,
    )
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20)
    additional_phone = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    # Temporarily nullable to preserve old test records during this refactor.
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    deposit_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    advance_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    payment_status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
    )
    confirmed = models.BooleanField(default=False)
    pickup_ready = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and not self.bill_number:
            self.bill_number = f"BILL-{self.created_at:%Y%m%d}-{self.pk:05d}"
            Rental.objects.filter(pk=self.pk).update(bill_number=self.bill_number)

    @property
    def total_amount(self):
        return sum(
            (
                booking.outfit_size.outfit.rental_price
                for booking in self.bookings.select_related(
                    "outfit_size__outfit"
                ).exclude(outfit_size__isnull=True)
            ),
            Decimal("0"),
        )

    @property
    def net_amount(self):
        return max(Decimal("0"), self.total_amount - self.discount_amount)

    @property
    def remaining_due(self):
        return max(Decimal("0"), self.net_amount - self.advance_amount)

    def __str__(self):
        return self.bill_number or f"Rental #{self.pk}"


class Booking(models.Model):
    # Temporarily nullable to preserve old test records during this refactor.
    rental = models.ForeignKey(
        Rental,
        on_delete=models.CASCADE,
        related_name="bookings",
        null=True,
        blank=True,
    )

    outfit_size = models.ForeignKey(
        OutfitSize,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    notes = models.TextField(blank=True)

    def clean(self):
        if not self.rental_id:
            raise ValidationError("A booking must belong to a rental/bill.")

        if not self.outfit_size_id:
            raise ValidationError("A booking must have an outfit size.")

        if not self.rental.start_date or not self.rental.end_date:
            raise ValidationError("The rental must have a valid rental period.")

        overlaps = Booking.objects.filter(
            outfit_size=self.outfit_size,
            rental__start_date__lte=self.rental.end_date,
            rental__end_date__gte=self.rental.start_date,
        ).exclude(pk=self.pk)

        if overlaps.exists():
            raise ValidationError(
                "This outfit size is already booked during the rental period."
            )

    def __str__(self):
        return str(self.outfit_size) if self.outfit_size else "No outfit size"