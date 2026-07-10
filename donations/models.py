"""Donation records (modelled on Paystack channels for Ghana)."""
from decimal import Decimal
from django.conf import settings
from django.db import models


class Donation(models.Model):
    class Channel(models.TextChoices):
        MOMO = "MOMO", "Mobile Money"
        CARD = "CARD", "Card"
        BANK = "BANK", "Bank Transfer"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Successful"
        FAILED = "FAILED", "Failed"

    donor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="donations")
    donor_name = models.CharField(max_length=160, blank=True)
    donor_email = models.EmailField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2,
                                 default=Decimal("0.00"))
    currency = models.CharField(max_length=8, default="GHS")
    channel = models.CharField(max_length=8, choices=Channel.choices,
                               default=Channel.MOMO)
    status = models.CharField(max_length=8, choices=Status.choices,
                              default=Status.SUCCESS, db_index=True)
    reference = models.CharField(max_length=64, blank=True)
    campaign = models.CharField(max_length=120, blank=True, default="General Fund")
    note = models.CharField(max_length=300, blank=True,
                            help_text="Optional message from the donor.")
    is_recurring = models.BooleanField(default=False)
    receipt_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.currency} {self.amount:.2f} via {self.get_channel_display()}"
