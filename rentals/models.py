from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Outfit(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    model_code = models.CharField(max_length=50)
    size = models.CharField(max_length=10)
    rental_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    photo = models.ImageField(upload_to="outfit_photos/", blank=True, null=True)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["model_code", "size"],
                name="unique_outfit_model_and_size",
            )
        ]

    def __str__(self):
        return f"{self.model_code} — Size {self.size}"


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
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    deposit_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    advance_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    payment_status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
    )
    confirmed = models.BooleanField(default=False)
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
            (booking.outfit.rental_price for booking in self.bookings.select_related("outfit")),
            Decimal("0"),
        )

    @property
    def remaining_due(self):
        return max(Decimal("0"), self.total_amount - self.advance_amount)

    def __str__(self):
        return self.bill_number or f"Rental #{self.pk}"


class Booking(models.Model):
    rental = models.ForeignKey(
        Rental,
        on_delete=models.CASCADE,
        related_name="bookings",
        null=True,
        blank=True,
    )
    outfit = models.ForeignKey(Outfit, on_delete=models.PROTECT)
    notes = models.TextField(blank=True)

    def clean(self):
        if not self.rental_id:
            raise ValidationError("Every outfit booking must belong to a rental/bill.")

        if not self.rental.start_date or not self.rental.end_date:
            raise ValidationError("The rental must have a valid booking and return time.")

        overlaps = Booking.objects.filter(
            outfit=self.outfit,
            rental__start_date__lte=self.rental.end_date,
            rental__end_date__gte=self.rental.start_date,
        ).exclude(pk=self.pk)

        if overlaps.exists():
            raise ValidationError(
                "This outfit is already booked during the rental period."
            )

    def __str__(self):
        return str(self.outfit)