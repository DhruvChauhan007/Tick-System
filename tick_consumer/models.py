from django.db import models


class Broker(models.Model):
    type = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    api_config = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Script(models.Model):
    broker = models.ForeignKey(
        Broker,
        on_delete=models.CASCADE,
        related_name="scripts"
    )

    name = models.CharField(max_length=100)
    trading_symbol = models.CharField(max_length=50)
    additional_data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Tick(models.Model):
    script = models.ForeignKey(
        Script,
        on_delete=models.CASCADE
    )

    tick_value = models.DecimalField(
        max_digits=20,
        decimal_places=8
    )

    volume = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True
    )

    received_at_producer = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)