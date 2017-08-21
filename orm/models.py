from django.db import models

class Sighting(models.Model):
    pokemon_name = models.CharField(max_length=100)
    pokemon_number = models.IntegerField()
    expiration = models.DateTimeField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    source = models.CharField(max_length=64, null=True)

class SightingMessage(models.Model):
    sighting = models.ForeignKey(Sighting, on_delete=models.CASCADE)
    channel = models.CharField(max_length=64)
    message = models.CharField(max_length=64)
