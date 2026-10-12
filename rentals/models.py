from django.db import models
from django.core.exceptions import ValidationError


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Outfit(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    model_code = models.CharField(max_length=50)  # KT-1, IW-2, etc.
    size = models.CharField(max_length=10)        # 38, 40, 42, 44
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


class Booking(models.Model):
    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PARTIAL = "partial", "Partially paid"
        PAID = "paid", "Paid"

    outfit = models.ForeignKey(Outfit, on_delete=models.PROTECT)
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    confirmed = models.BooleanField(default=False)
    payment_status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
    )
    advance_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.customer_name} — {self.outfit}"

    def clean(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": "End time cannot be before the start time."}
            )

        if not self.outfit_id or not self.start_date or not self.end_date:
            return

        overlapping_booking = Booking.objects.filter(
            outfit=self.outfit,
            start_date__lte=self.end_date,
            end_date__gte=self.start_date,
        ).exclude(pk=self.pk)

        if overlapping_booking.exists():
            raise ValidationError(
                "This outfit is already booked during the selected dates."
            )