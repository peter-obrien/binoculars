from django.contrib.postgres.fields import JSONField
from django.db import models
from math import sin, cos, sqrt, atan2, radians


class Sighting(models.Model):
    pokemon_name = models.CharField(max_length=100)
    pokemon_number = models.IntegerField()
    expiration = models.DateTimeField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    active = models.BooleanField(default=True)
    iv = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    cp = models.DecimalField(max_digits=6, decimal_places=2, null=True)


class SightingMessage(models.Model):
    sighting = models.ForeignKey(Sighting, on_delete=models.CASCADE)
    channel = models.BigIntegerField()
    message = models.BigIntegerField()


def filter_default():
    return {'pokemon': []}


class PokemonZone(models.Model):
    guild = models.BigIntegerField()
    destination = models.BigIntegerField()
    name = models.CharField(max_length=100, default='Default')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    radius = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)
    active = models.BooleanField(default=True)
    filters = JSONField(default=filter_default)
    is_filter_blacklist = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Since the destination field is the ID of the discord channel/user, this attribute will hold the full object.
        self.discord_destination = None

    @property
    def status(self):
        if self.active:
            return 'on'
        else:
            return 'off'

    def filter(self, sighting):
        return self.active and self.__isInZone(sighting) and self.__filter_pokemon(sighting)

    def __isInZone(self, sighting):
        earth_radius = 6373.0

        center_lat = radians(self.latitude)
        center_lon = radians(self.longitude)
        pokemon_lat = radians(sighting.latitude)
        pokemon_lon = radians(sighting.longitude)

        lon_diff = pokemon_lon - center_lon
        lat_diff = pokemon_lat - center_lat

        a = sin(lat_diff / 2) ** 2 + cos(center_lat) * cos(pokemon_lat) * sin(lon_diff / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = earth_radius * c

        return distance <= self.radius

    def __filter_pokemon(self, sighting):
        if len(self.filters['pokemon']) > 0:
            if self.is_filter_blacklist:
                return int(sighting.pokemon_number) not in self.filters['pokemon']
            else:
                return int(sighting.pokemon_number) in self.filters['pokemon']
        else:
            # No matter if the filter is a blacklist or a whitelist if there are no entries then allow everything.
            return True
