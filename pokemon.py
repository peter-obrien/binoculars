from math import sin, cos, sqrt, atan2, radians
from datetime import datetime
from orm.models import Sighting, PokemonZone


class PokemonManager:
    def __init__(self):
        self.active_sightings = []

    def create_pokemon(self, pokemon_name, pokemon_number, end, latitude, longitude):
        sighting = Sighting(pokemon_name=pokemon_name, pokemon_number=pokemon_number, expiration=end, latitude=latitude,
                            longitude=longitude)
        sighting.save()
        self.active_sightings.append(sighting)
        return sighting

    def remove_pokemon(self, sighting):
        self.active_sightings.remove(sighting)


class ZoneManager:
    def __init__(self):
        self.zones = dict()

    def create_zone(self, guild, destination, latitude, longitude):
        pz = PokemonZone(guild=guild, destination=destination, latitude=latitude, longitude=longitude)
        pz.save()
        self.zones[destination] = pz
        return pz

    async def load_from_database(self, bot):
        for pz in PokemonZone.objects.all():
            guild = bot.get_guild(pz.guild)
            channel = guild.get_channel(pz.destination)
            if channel is None:
                channel = guild.get_member(pz.destination)
            if channel is not None:
                pz.discord_destination = channel
                self.zones[pz.destination] = pz
            else:
                print('Unable to load pokemon zone for id {} destination {}'.format(pz.id, pz.destination))
