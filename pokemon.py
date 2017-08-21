from math import sin, cos, sqrt, atan2, radians
from datetime import datetime
from orm.models import Sighting

class PokemonManager:
    def __init__(self):
        self.monsters = []

    def create_pokemon(self, pokemon_name, pokemon_number, end, latitude, longitude):
        sighting = Sighting(pokemon_name=pokemon_name, pokemon_number=pokemon_number, expiration=end, latitude=latitude, longitude=longitude)
        sighting.save()
        self.monsters.append(sighting)
        return sighting

    def remove_pokemon(self, sighting):
        self.monsters.remove(sighting)

class PokemonZone:
    def __init__(self,channel,lat,lon,radius):
        self.channel = channel
        self.latitude = float(lat)
        self.longitude = float(lon)
        self.radius = float(radius)
        self.targetPokemon = []

    def isInZone(self, sighting):
        earth_radius = 6373.0

        center_lat = radians(self.latitude)
        center_lon = radians(self.longitude)
        gym_lat = radians(sighting.latitude)
        gym_lon = radians(sighting.longitude)

        dlon = gym_lon - center_lon
        dlat = gym_lat - center_lat

        a = sin(dlat / 2)**2 + cos(center_lat) * cos(gym_lat) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = earth_radius * c

        return distance <= self.radius

    def filterPokemon(self, pokemonNumber):
        if len(self.targetPokemon) == 0:
            return True
        else:
            return int(pokemonNumber) in self.targetPokemon
