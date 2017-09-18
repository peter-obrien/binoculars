import os, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

import configparser
import logging
import traceback
import aiohttp
import asyncio
import sys
import discord

from pokemon import ZoneManager, PokemonManager
from discord.ext import commands
from cogs.utils import context
from alarm_handler import process_raid
from django.utils import timezone

description = """
I'm a Pokemon Go sightings bot
"""

log = logging.getLogger(__name__)

initial_extensions = (
    'cogs.zones',
    'cogs.admin'
)

# Process startup configurations
propFilename = 'properties.ini'
config = configparser.ConfigParser()
config.read(propFilename)
if not config['DEFAULT']['bot_token']:
    print('bot_token is not set. Please update ' + propFilename)
    quit()
elif not config['DEFAULT']['pokemon_src_channel_id']:
    print('pokemon_src_channel_id is not set. Please update ' + propFilename)
    quit()
elif not config['DEFAULT']['server_id']:
    print('server_id is not set. Please update ' + propFilename)
    quit()

bot_token = config['DEFAULT']['bot_token']
try:
    sighting_src_id = int(config['DEFAULT']['pokemon_src_channel_id'])
except ValueError:
    print('pokemon_src_channel_id is not a number.')
    quit()
try:
    guild_id = int(config['DEFAULT']['server_id'])
except ValueError:
    print('server_id is not a number.')
    quit()

try:
    test_message_id = config['DEFAULT']['test_message_id']
except Exception as e:
    test_message_id = None


def _prefix_callable(bot, msg):
    return '$'


class SightingsBot(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(command_prefix=_prefix_callable, description=description,
                         pm_help=True, help_attrs=dict(hidden=True))

        self.session = aiohttp.ClientSession(loop=self.loop)
        self.zones = ZoneManager()
        self.map = PokemonManager()
        self.bot_guild = None

        # create the background task and run it in the background
        self.bg_task = self.loop.create_task(self.background_cleanup())

        for extension in initial_extensions:
            try:
                self.load_extension(extension)
            except Exception:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send('This command cannot be used in private messages.')
        elif isinstance(error, commands.DisabledCommand):
            await ctx.author.send('Sorry. This command is disabled and cannot be used.')
        elif isinstance(error, commands.CommandInvokeError):
            print(f'In {ctx.command.qualified_name}:', file=sys.stderr)
            traceback.print_tb(error.original.__traceback__)
            print(f'{error.original.__class__.__name__}: {error.original}', file=sys.stderr)
        elif isinstance(error, commands.BadArgument):
            await ctx.author.send(str(error))
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.author.send('Missing required argument for: {}'.format(ctx.command))
            await ctx.show_help(command=ctx.command)
            await ctx.message.delete()

    async def on_ready(self):
        self.bot_guild = self.get_guild(guild_id)
        await self.zones.load_from_database(self)
        print(f'Ready: {self.user} (ID: {self.user.id})')

    async def on_resumed(self):
        print('resumed...')

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=context.Context)

        # Make base commands case insensitive
        if ctx.prefix is not None:
            command = ctx.invoked_with
            if command:
                ctx.command = self.get_command(command.lower())

        if ctx.command is None:
            return

        await self.invoke(ctx)

    async def on_message(self, message):

        # Used for testing purposes
        if message.content.startswith('!go') and test_message_id is not None:
            await message.delete()
            message = await message.channel.get_message(test_message_id)

        if message.channel.id == sighting_src_id and message.author.bot:
            await process_raid(self, message)
        else:
            if message.author.bot:
                return

            await self.process_commands(message)

    async def on_guild_channel_delete(self, channel):
        # If the channel was a sighting zone, delete it.
        if channel.id in self.zones.zones:
            self.zones.zones[channel.id].delete()

    async def close(self):
        await super().close()
        await self.session.close()

    def run(self):
        super().run(bot_token, reconnect=True)

    async def background_cleanup(self):
        await self.wait_until_ready()

        while not self.is_closed():
            # Delete expired pokemon
            expiredPokemon = []
            current_time = timezone.localtime(timezone.now())
            # Find expired pokemon
            for sighting in self.map.active_sightings:
                if current_time > sighting.expiration:
                    expiredPokemon.append(sighting)
            # Process expired pokemon
            for sighting in expiredPokemon:
                for sm in sighting.sightingmessage_set.all():
                    try:
                        msgCh = self.bot_guild.get_channel(sm.channel)
                        msg = await msgCh.get_message(sm.message)
                        await msg.delete()
                    except discord.errors.NotFound:
                        pass
                sighting.active = False
                sighting.save()
                self.map.remove_pokemon(sighting)

            await asyncio.sleep(60)  # task runs every 60 seconds


bot = SightingsBot()
bot.run()
