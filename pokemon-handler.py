import os, django

import pytz
from django.utils.timezone import make_aware, localtime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

import discord
import asyncio
import configparser
from datetime import datetime, timedelta
from pytz import timezone
from decimal import *
from pokemon import PokemonManager, ZoneManager
from orm.models import SightingMessage

propFilename = 'properties.ini'
config = configparser.ConfigParser()
config.read(propFilename)
serverId = config['DEFAULT']['server_id']
botToken = config['DEFAULT']['bot_token']
pokemonSourceChannelId = config['DEFAULT']['pokemon_src_channel_id']
pokemonDestChannelId = config['DEFAULT']['pokemon_dest_channel_id']
if not serverId:
    print('server_id is not set. Please update ' + propFilename)
    quit()
if not botToken:
    print('bot_token is not set. Please update ' + propFilename)
    quit()
if not pokemonSourceChannelId:
    print('raid_src_channel_id is not set. Please update ' + propFilename)
    quit()
if not pokemonDestChannelId:
    print('raid_dest_channel_id is not set. Please update ' + propFilename)
    quit()

try:
    test_message_id = config['DEFAULT']['test_message_id']
except Exception as e:
    test_message_id = None

client = discord.Client()
monMap = PokemonManager()
pokemon_zones = ZoneManager()
easternTz = timezone('US/Eastern')
timeFmt = '%m/%d %I:%M %p'
embedColor = 0x408fd0

channelConfigMessage = discord.Embed(title="Channel Config Commands",
                                     description="Here are the available commands to configure channels.",
                                     color=0xf0040b)
channelConfigMessage.add_field(name="!setup latitude, longitude",
                               value="Creates a pokemon zone with radius 5km. If used again replaces the coordinates.",
                               inline=False)
channelConfigMessage.add_field(name="!radius xxx.x",
                               value="Changes the pokemon zone radius.",
                               inline=False)
channelConfigMessage.add_field(name="!filter pokemon_numbers",
                               value="Allows for a comma separated list of pokemon numbers to enable filtering. E.g. `!filter 144,145,146`. Use `0` to clear the filter.",
                               inline=False)
channelConfigMessage.add_field(name="!pokemon [on/off]",
                               value="Toggles if this pokemon zone is active or not.",
                               inline=False)
channelConfigMessage.add_field(name="!info",
                               value="Displays the configuration for the channel.",
                               inline=False)


@client.event
async def on_ready():
    global discordServer
    global pokemonInputChannel
    global pokemonDestChannel
    global pokemonZones
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

    discordServer = client.get_server(serverId)
    if discordServer is None:
        print('Could not obtain server: [{}]'.format(serverId))
        quit(1)

    pokemonInputChannel = discordServer.get_channel(pokemonSourceChannelId)
    if pokemonInputChannel is None:
        print('Could not locate Pokemon source channel: [{}]'.format(pokemonSourceChannelId))
        quit(1)

    pokemonDestChannel = discordServer.get_channel(pokemonDestChannelId)
    if pokemonDestChannel is None:
        print('Could not locate Pokemon destination channel: [{}]'.format(pokemonDestChannelId))
        quit(1)

    await pokemon_zones.load_from_database(discordServer)


@client.event
async def on_message(message):
    if message.content.startswith('!go') and test_message_id is not None:
        message = await client.get_message(message.channel, test_message_id)

    if message.channel == pokemonInputChannel:
        if len(message.embeds) > 0:
            the_embed = message.embeds[0]

            body = the_embed['description'].split('}{')
            attributes = dict()
            for token in body:
                keyAndValue = token.split('::')
                attributes[keyAndValue[0].upper()] = keyAndValue[1]

            pokemon_name = attributes['POKEMON']
            pokemon_number = attributes['POKEMON#']
            end_time_tokens = attributes['TIMEUNTILGONE'].split(':')
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

            end_time = make_aware(message.timestamp, timezone=pytz.utc) + timedelta(seconds=seconds_to_end)
            end_time = end_time.replace(microsecond=0)

            # Get the coordinate of the pokemon so we can determine which zone(s) it belongs to
            coord_tokens = the_embed['url'].split('=')[1].split(',')
            latitude = Decimal(coord_tokens[0])
            longitude = Decimal(coord_tokens[1])

            pokemon = monMap.create_pokemon(pokemon_name, pokemon_number, end_time, latitude, longitude)

            desc = '{}, {}, {}\n\n*Disappears: {}*'.format(street, city, zipcode,
                                                           localtime(pokemon.expiration).strftime(timeFmt))

            result = discord.Embed(title='A wild {} has appeared!'.format(pokemon_name), url=the_embed['url'],
                                   description=desc, colour=embedColor)

            image_content = the_embed['image']
            result.set_image(url=image_content['url'])
            result.image.height = image_content['height']
            result.image.width = image_content['width']
            result.image.proxy_url = image_content['proxy_url']

            thumbnail_content = the_embed['thumbnail']
            result.set_thumbnail(url=thumbnail_content['url'])
            result.thumbnail.height = thumbnail_content['height']
            result.thumbnail.width = thumbnail_content['width']
            result.thumbnail.proxy_url = thumbnail_content['proxy_url']

            pokemon_message = await client.send_message(pokemonDestChannel, embed=result)
            messages = []
            msg = SightingMessage(message=pokemon_message.id, channel=pokemon_message.channel.id, sighting=pokemon)
            messages.append(msg)

            # Send the raids to any compatible raid zones.
            for pz in pokemon_zones.zones.values():
                if pz.filter(pokemon):
                    pokemon_message = await client.send_message(pz.discord_destination, embed=result)
                    if not isinstance(pz.discord_destination, discord.member.Member):
                        msg = SightingMessage(message=pokemon_message.id, channel=pokemon_message.channel.id,
                                              sighting=pokemon)
                        messages.append(msg)
            SightingMessage.objects.bulk_create(messages)
    else:
        # Covert the message to lowercase to make the commands case-insensitive.
        lowercase_message = message.content.lower()

        # Ignore bots (including self)
        if message.author.bot:
            return

        is_pm = message.channel.is_private
        is_pm = False # Turning this off for now

        # Used for channel configuration commands
        if isinstance(message.author, discord.member.Member):
            can_manage_channels = message.channel.permissions_for(message.author).manage_channels
        else:
            can_manage_channels = False

        destination = message.channel.id
        if is_pm:
            destination = message.author.id

        if (can_manage_channels or is_pm) and lowercase_message.startswith('!setup '):
            coordinates = message.content[7:]
            if coordinates.find(',') != -1:
                try:
                    coord_tokens = coordinates.split(',')
                    latitude = Decimal(coord_tokens[0].strip())
                    longitude = Decimal(coord_tokens[1].strip())

                    if destination in pokemon_zones.zones:
                        pz = pokemon_zones.zones[destination]
                        pz.latitude = latitude
                        pz.longitude = longitude
                        pz.save()
                        await client.send_message(message.channel, 'Pokemon zone coordinates updated')
                    else:
                        pz = pokemon_zones.create_zone(destination, latitude, longitude)
                        pz.discord_destination = message.channel
                        await client.send_message(message.channel, 'Pokemon zone created')
                except Exception as e:
                    print(e)
                    await client.send_message(message.channel, embed=channelConfigMessage,
                                              content='There was an error handling your request.\n\n`{}`'.format(
                                                  message.content))
            else:
                await client.send_message(message.channel, content='Invalid command: `{}`'.format(message.content),
                                          embed=channelConfigMessage)
            if not is_pm:
                await client.delete_message(message)
        elif (can_manage_channels or is_pm) and lowercase_message.startswith('!radius '):
            user_radius = message.content[8:]
            try:
                radius = Decimal(user_radius)
                if destination in pokemon_zones.zones:
                    pz = pokemon_zones.zones[destination]
                    pz.radius = radius
                    pz.save()
                    await client.send_message(message.channel, 'Radius updated')
                else:
                    await client.send_message(message.channel,
                                              content='Setup has not been run for this channel.',
                                              embed=channelConfigMessage)
            except InvalidOperation:
                await client.send_message(message.channel, 'Invalid radius: {}'.format(user_radius))
                pass
            finally:
                if not is_pm:
                    await client.delete_message(message)
        elif (can_manage_channels or is_pm) and lowercase_message.startswith('!filter '):
            user_pokemon_list = message.content[8:]
            try:
                if destination in pokemon_zones.zones:
                    pz = pokemon_zones.zones[destination]
                    new_pokemon_filter = []
                    if user_pokemon_list.find(',') == -1:
                        if '0' != user_pokemon_list:
                            new_pokemon_filter.append(int(user_pokemon_list))
                    else:
                        for pokemon_number in user_pokemon_list.split(','):
                            new_pokemon_filter.append(int(pokemon_number))
                    pz.filters['pokemon'].clear()
                    pz.filters['pokemon'] = new_pokemon_filter
                    pz.save()
                    await client.send_message(message.channel, 'Updated filter list')
                else:
                    await client.send_message(message.channel, embed=channelConfigMessage,
                                              content='Setup has not been run for this channel.')
            except Exception as e:
                print('Unable to process: {}'.format(message.content))
                print(e)
                await client.send_message(message.channel,
                                          'Unable to process filter. Please verify your input: {}'.format(
                                              user_pokemon_list))
                pass
            if not is_pm:
                await client.delete_message(message)
        elif (can_manage_channels or is_pm) and lowercase_message.startswith('!pokemon '):
            if destination in pokemon_zones.zones:
                pz = pokemon_zones.zones[destination]
                token = lowercase_message[9:]
                try:
                    if token == 'on':
                        pz.active = True
                        pz.save()
                        await client.send_message(message.channel, 'Pokemon sightings enabled.')
                    elif token == 'off':
                        pz.active = False
                        pz.save()
                        await client.send_message(message.channel, 'Pokemon sightings disabled.')
                    else:
                        await client.send_message(message.channel, embed=channelConfigMessage,
                                                  content='Unknown command: `{}`'.format(message.content))
                finally:
                    await client.delete_message(message)
            else:
                await client.send_message(message.channel, embed=channelConfigMessage,
                                          content='Setup has not been run for this channel.')
        elif (can_manage_channels or is_pm) and lowercase_message == '!info':
            if destination in pokemon_zones.zones:
                pz = pokemon_zones.zones[destination]
                output = 'Here is the pokemon zone configuration for this channel:\n\nStatus: `{}`\nCoordinates: `{}, {}`\nRadius: `{}`\nPokemon: `{}`'.format(
                    pz.status, pz.latitude, pz.longitude, pz.radius, pz.filters['pokemon'])
                await client.send_message(message.channel, output)
            else:
                await client.send_message(message.channel, 'This channel is not configured as a pokemon zone.')
            if not is_pm:
                await client.delete_message(message)


async def background_cleanup():
    await client.wait_until_ready()
    while not client.is_closed:
        # Delete expired pokemon
        expiredPokemon = []
        currentTime = datetime.now(easternTz)
        # Find expired pokemon
        for sighting in monMap.active_sightings:
            if currentTime > sighting.expiration:
                expiredPokemon.append(sighting)
        # Process expired pokemon
        for sighting in expiredPokemon:
            for sm in sighting.sightingmessage_set.all():
                try:
                    msgCh = discordServer.get_channel(sm.channel)
                    msg = await client.get_message(msgCh, sm.message)
                    await client.delete_message(msg)
                except discord.errors.NotFound:
                    pass
            sighting.active = False
            sighting.save()
            monMap.remove_pokemon(sighting)

        await asyncio.sleep(60)  # task runs every 60 seconds


client.loop.create_task(background_cleanup())

client.run(botToken)
