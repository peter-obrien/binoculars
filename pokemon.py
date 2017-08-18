from math import sin, cos, sqrt, atan2, radians
from datetime import datetime

class Pokemon:
    def __init__(self, pokemon, pokemonNumber, end, latitude, longitude):
        self.pokemon = pokemon
        self.pokemonNumber = int(pokemonNumber)
        self.end = end
        self.latitude = latitude
        self.longitude = longitude
        self.embed = None
        self.messages = []

    def add_message(self, message):
        self.messages.append(message)

    def __hash__(self):
        return hash((self.pokemon, self.latitude, self.longitude))

    def __eq__(self, other):
        return (self.pokemon == other.pokemon
            and self.latitude == other.latitude
            and self.longitude == other.longitude)

class PokemonManager:
    def __init__(self):
        self.monsters = []

    def create_pokemon(self, pokemon, pokemonNumber, end, latitude, longitude):
        poke = Pokemon(pokemon, pokemonNumber, end, latitude, longitude)
        self.monsters.append(poke)
        return poke

    def remove_pokemon(self, pokemon):
        self.monsters.remove(pokemon)

    def clear_raids(self):
        self.monsters.clear()

class PokemonZone:
    def __init__(self,channel,lat,lon,radius):
        self.channel = channel
        self.latitude = float(lat)
        self.longitude = float(lon)
        self.radius = float(radius)
        self.targetPokemon = []

    def isInZone(self, raid):
        earthRadius = 6373.0

        centerLat = radians(self.latitude)
        centerLon = radians(self.longitude)
        gymLat = radians(raid.latitude)
        gymLon = radians(raid.longitude)

        dlon = gymLon - centerLon
        dlat = gymLat - centerLat

        a = sin(dlat / 2)**2 + cos(centerLat) * cos(gymLat) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = earthRadius * c

        return distance <= self.radius

    def filterPokemon(self, pokemonNumber):
        if len(self.targetPokemon) == 0:
            return True
        else:
            return int(pokemonNumber) in self.targetPokemon
