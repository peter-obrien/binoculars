from datetime import timedelta
from decimal import Decimal

import discord
import pytz
from django.utils.timezone import make_aware, localtime

from orm.models import SightingMessage, Sighting

timeFmt = '%m/%d %I:%M %p'
embedColor = 0x408fd0


async def process_pokemon(bot, message):
    # Only attempt to process messages with an embed
    if len(message.embeds) == 0:
        return

    the_embed = message.embeds[0]

    body = the_embed.description.split('}{')
    attributes = dict()
    for token in body:
        key_and_value = token.split('::')
        attributes[key_and_value[0].upper()] = key_and_value[1]

    pokemon_name = attributes['POKEMON']
    pokemon_number = attributes['POKEMON#']
    time_remaining_tokens = attributes['TIMELEFT'].split(' ')
    street = attributes['ADDRESS']
    city = attributes['CITY']
    zipcode = attributes['ZIP']

    seconds_to_end = 0
    for token in time_remaining_tokens:
        if token.endswith('h'):
            seconds_to_end += int(token.rstrip('h')) * 60 * 60
        elif token.endswith('m'):
            seconds_to_end += int(token.rstrip('m')) * 60
        elif token.endswith('s'):
            seconds_to_end += int(token.rstrip('s'))

    end_time = make_aware(message.created_at, timezone=pytz.utc) + timedelta(seconds=seconds_to_end)
    end_time = end_time.replace(microsecond=0)

    # Get the coordinate of the pokemon so we can determine which zone(s) it belongs to
    latitude = Decimal(attributes['LATITUDE'])
    longitude = Decimal(attributes['LONGITUDE'])

    pokemon = bot.map.create_pokemon(pokemon_name, pokemon_number, end_time, latitude, longitude)

    # Assign IV and CP (if available)
    if 'IV' in attributes and attributes['IV'] != '?':
        pokemon.iv = attributes['IV']
    if 'CP' in attributes and attributes['CP'] != '?':
        pokemon.cp = attributes['CP']

    iv_and_cp = get_iv_and_cp_string(pokemon)

    if iv_and_cp is not None:
        desc = f'{street}, {city}, {zipcode}\n\n{iv_and_cp}\n\n*Disappears: {localtime(pokemon.expiration).strftime(timeFmt)}*'
    else:
        desc = f'{street}, {city}, {zipcode}\n\n*Disappears: {localtime(pokemon.expiration).strftime(timeFmt)}*'

    result = discord.Embed(title=f'A wild {pokemon_name} has appeared!', url=the_embed.url, description=desc,
                           colour=embedColor)

    image_content = the_embed.image
    result.set_image(url=image_content.url)
    result.image.height = image_content.height
    result.image.width = image_content.width
    result.image.proxy_url = image_content.proxy_url

    thumbnail_content = the_embed.thumbnail
    result.set_thumbnail(url=thumbnail_content.url)
    result.thumbnail.height = thumbnail_content.height
    result.thumbnail.width = thumbnail_content.width
    result.thumbnail.proxy_url = thumbnail_content.proxy_url

    # Send the raids to any compatible raid zones.
    messages = []
    for zone_list in bot.zones.zones.values():
        for pz in zone_list:
            if pz.filter(pokemon):
                try:
                    pokemon_message = await pz.discord_destination.send(embed=result)
                    if not isinstance(pz.discord_destination, discord.member.Member):
                        msg = SightingMessage(message=pokemon_message.id, channel=pokemon_message.channel.id,
                                              sighting=pokemon)
                        messages.append(msg)
                except discord.errors.Forbidden:
                    print(
                        f'Unable to send pokemon to channel {pz.discord_destination.name}. The bot does not have permission.')
                    pass

    SightingMessage.objects.bulk_create(messages)


def get_iv_and_cp_string(pokemon: Sighting):
    iv = pokemon.iv
    cp = pokemon.cp
    if iv is not None and cp is not None:
        result = f'IV: {iv} / CP: {cp}'
    else:
        if iv is not None:
            result = f'IV: {iv}'
        elif cp is not None:
            result = f'CP: {cp}'
        else:
            result = None
    return result
