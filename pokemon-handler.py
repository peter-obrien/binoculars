import discord
import asyncio
import sys
import configparser
from datetime import datetime, timedelta
from pytz import timezone
import pytz
from pokemon import Pokemon, PokemonManager, PokemonZone

propFilename = 'properties.ini'
config = configparser.ConfigParser()
config.read(propFilename)
serverId = config['DEFAULT']['server_id']
botToken = config['DEFAULT']['bot_token']
pokemonSourceChannelId = config['DEFAULT']['pokemon_src_channel_id']
pokemonDestChannelId = config['DEFAULT']['pokemon_dest_channel_id']
zonesRaw = config['DEFAULT']['zones'].split(',')
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
easternTz = timezone('US/Eastern')
utcTz = timezone('UTC')
timeFmt = '%m/%d %I:%M %p'
embedColor = 0x408fd0

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
        print('Could not locate Raid srouce channel: [{}]'.format(pokemonSourceChannelId))
        quit(1)

    pokemonDestChannel = discordServer.get_channel(pokemonDestChannelId)
    if pokemonDestChannel is None:
        print('Could not locate Raid destination channel: [{}]'.format(pokemonDestChannelId))
        quit(1)

    try:
        pokemonZones = []
        for zoneData in zonesRaw:
            zoneTokens = zoneData.split('|')
            pz = PokemonZone(discordServer.get_channel(zoneTokens[0].strip()), zoneTokens[1].strip(), zoneTokens[2].strip(), zoneTokens[3].strip())
            pokemonZones.append(pz)
            i = 4
            while i < len(zoneTokens):
                pz.targetPokemon.append(int(zoneTokens[i]))
                i += 1
    except Exception as e:
        print('Could not initialize pokemon zones. Please check the config.')
        quit(1)

@client.event
async def on_message(message):

    if message.content.startswith('!go') and test_message_id is not None:
        message = await client.get_message(message.channel, test_message_id)

    if message.channel == pokemonInputChannel:
        if len(message.embeds) > 0:
            theEmbed = message.embeds[0]

            body = theEmbed['description'].split('}{')
            attributes = dict()
            for token in body:
                keyAndValue = token.split('::')
                attributes[keyAndValue[0].upper()] = keyAndValue[1]

            pokemonName = attributes['POKEMON']
            pokemonNumber = attributes['POKEMON#']
            endTimeTokens = attributes['TIMEUNTILGONE'].split(':')
            street = attributes['ADDRESS']
            city = attributes['CITY']
            zipcode = attributes['ZIP']

            now = datetime.now(easternTz)
            endTime = now.replace(hour=int(endTimeTokens[0]), minute=int(endTimeTokens[1]), second=0)

            # Get the coordinate of the gym so we can determine which zone(s) it belongs to
            coordTokens = theEmbed['url'].split('=')[1].split(',')
            latitude = float(coordTokens[0])
            longitude = float(coordTokens[1])

            pokemon = monMap.create_pokemon(pokemonName, pokemonNumber, endTime, latitude, longitude)

            desc = '{}, {}, {}\n\n*Disappears: {}*'.format(street, city, zipcode, endTime.strftime(timeFmt))

            result = discord.Embed(title='A wild {} has appeared!'.format(pokemonName), url=theEmbed['url'], description=desc, colour=embedColor)

            imageContent = theEmbed['image']
            result.set_image(url=imageContent['url'])
            result.image.height=imageContent['height']
            result.image.width=imageContent['width']
            result.image.proxy_url=imageContent['proxy_url']

            thumbnailContent = theEmbed['thumbnail']
            result.set_thumbnail(url=thumbnailContent['url'])
            result.thumbnail.height=thumbnailContent['height']
            result.thumbnail.width=thumbnailContent['width']
            result.thumbnail.proxy_url=thumbnailContent['proxy_url']

            pokemon.embed = result

            raidMessage = await client.send_message(pokemonDestChannel, embed=pokemon.embed)
            pokemon.add_message(raidMessage)

            # Send the raids to any compatible raid zones.
            for pz in pokemonZones:
                if pz.isInZone(pokemon) and pz.filterPokemon(pokemon.pokemonNumber):
                    raidMessage = await client.send_message(pz.channel, embed=pokemon.embed)
                    pokemon.add_message(raidMessage)

async def background_cleanup():
    await client.wait_until_ready()
    while not client.is_closed:
        # Delete expired pokemon
        expiredPokemon = []
        currentTime = datetime.now(easternTz)
        # Find expired pokemon
        for pokemon in monMap.monsters:
            if currentTime > pokemon.end:
                expiredPokemon.append(pokemon)
        # Process expired pokemon
        for pokemon in expiredPokemon:
            for message in pokemon.messages:
                try:
                    await client.delete_message(message)
                except discord.errors.NotFound as e:
                    pass
            monMap.remove_pokemon(pokemon)

        await asyncio.sleep(60) # task runs every 60 seconds

client.loop.create_task(background_cleanup())

client.run(botToken)
