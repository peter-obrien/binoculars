from decimal import Decimal, InvalidOperation

from discord.ext import commands

from orm.models import PokemonZone


class ChannelOrMember(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return await commands.TextChannelConverter().convert(ctx, argument)
        except commands.BadArgument:
            return await commands.MemberConverter().convert(ctx, argument)


class Zones:
    """Pokemon zone setup and configuration. To invoke user must have Manage Channels permission."""

    def __init__(self, bot):
        self.bot = bot

    # async def __after_invoke(self, ctx):
    #     if isinstance(ctx.channel, discord.TextChannel):
    #         await ctx.message.delete()

    @commands.command(hidden=True, usage='channel_id/user_id')
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def zones(self, ctx, destination: ChannelOrMember = None):
        """List the named zones for a channel or member."""
        if destination is None:
            zone_id = ctx.channel.id
        else:
            zone_id = destination.id
        listed_zones = ctx.zones.zones[zone_id]
        if len(listed_zones) == 0:
            await ctx.send('There are no available zones.')
        else:
            msg = 'Here are the available pokemon zones:'
            for index in range(0, len(listed_zones)):
                msg += '\n\t{}) {}'.format(index + 1, listed_zones[index].name)
            await ctx.send(msg)

    @commands.group(pass_context=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def config(self, ctx, destination: ChannelOrMember, number: int):
        """Allow for configuration of a specified pokemon zone.

        Allows for multiple zones to be setup for a channel or setting up a zone for a member."""
        if ctx.invoked_subcommand is None:
            await ctx.send(f'Incorrect config subcommand passed. Try {ctx.prefix}help config')
        else:
            if destination.id in ctx.zones.zones and number <= len(ctx.zones.zones[destination.id]):
                ctx.pz = ctx.zones.zones[destination.id][number - 1]
            elif ctx.subcommand_passed == 'setup':
                ctx.pz = destination
            else:
                raise commands.BadArgument(
                    f'ctx.message.contentThe pokemon zone specified does not exist: `{destination} {number}`')

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def setup(self, ctx, latitude: str, longitude: str):
        """Creates a pokemon zone with radius 5km. If used again replaces the coordinates."""
        try:
            lat = Decimal(latitude)
            lon = Decimal(longitude)

            if ctx.channel.id in ctx.zones.zones:
                pz = ctx.zones.zones[ctx.channel.id][0]
                pz.latitude = lat
                pz.longitude = lon
                pz.save()
                await ctx.send(f'Pokemon zone coordinates updated: `{lat}, {lon}`')
            else:
                pz = ctx.zones.create_zone(ctx.guild.id, ctx.channel.id, lat, lon)
                pz.discord_destination = ctx.channel
                await ctx.send(f'Pokemon zone created: `{lat}, {lon}`')
        except Exception as e:
            print(e)
            await ctx.send(f'There was an error handling your request.\n\n`{ctx.message.content}`')

    @config.command(name='setup', hidden=True)
    async def setup_sub(self, ctx, latitude: str, longitude: str):
        """Creates a pokemon zone with radius 5km. If used again replaces the coordinates."""
        try:
            lat = Decimal(latitude)
            lon = Decimal(longitude)

            if isinstance(ctx.pz, PokemonZone):
                ctx.pz.latitude = lat
                ctx.pz.longitude = lon
                ctx.pz.save()
                await ctx.pz.discord_destination.send(f'Pokemon zone coordinates updated: {lat}, {lon}')
                await ctx.send(f'Pokemon zone coordinates updated: {lat}, {lon}')
            else:
                pz = ctx.zones.create_zone(ctx.guild.id, ctx.pz.id, lat, lon)
                pz.discord_destination = ctx.pz
                await ctx.pz.send(f'Pokemon zone created: {lat}, {lon}')
                await ctx.send(f'Pokemon zone created: {lat}, {lon}')
        except Exception as e:
            print(e)
            await ctx.send(f'There was an error handling your request.\n\n`{ctx.message.content}`')

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def rename(self, ctx, new_name: str):
        """Changes the name of a zone."""
        if ctx.message.channel.id in ctx.zones.zones:
            pz = ctx.zones.zones[ctx.channel.id][0]
            pz.name = new_name
            pz.save()
            await ctx.send(f'Zone renamed to {new_name}')
        else:
            await ctx.send('Setup has not been run for this channel.')

    @config.command(name='rename')
    async def rename_sub(self, ctx, new_name: str):
        """Changes the name of a zone."""
        ctx.pz.name = new_name
        ctx.pz.save()
        await ctx.pz.discord_destination.send(f'Zone renamed to {new_name}')
        await ctx.send(f'Zone renamed to {new_name}')

    @commands.command(hidden=True, usage='xxxx.xx')
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def radius(self, ctx, value: str):
        """Changes the pokemon zone radius."""
        try:
            radius = Decimal(value)
            if radius >= 1000.0:
                await ctx.send('Radius is too large.')
            else:
                if ctx.message.channel.id in ctx.zones.zones:
                    pz = ctx.zones.zones[ctx.channel.id][0]
                    pz.radius = radius
                    pz.save()
                    await ctx.send(f'Radius updated to {radius}')
                else:
                    await ctx.send('Setup has not been run for this channel.')
        except InvalidOperation:
            raise commands.BadArgument(f'Invalid radius: {value}')

    @config.command(name='radius', hidden=True)
    async def radius_sub(self, ctx, value: str):
        """Changes the pokemon zone radius."""
        try:
            radius = Decimal(value)
            if radius >= 1000.0:
                await ctx.send('Radius is too large.')
            else:
                ctx.pz.radius = radius
                ctx.pz.save()
                await ctx.pz.discord_destination.send(f'Radius updated to {radius}')
                await ctx.send(f'Radius updated to {radius}')
        except InvalidOperation:
            raise commands.BadArgument(f'Invalid radius: {value}')

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def zone(self, ctx, value: str):
        """Toggles if this pokemon zone is active or not."""
        if ctx.channel.id in ctx.zones.zones:
            pz = ctx.zones.zones[ctx.channel.id][0]
            if value == 'on':
                pz.active = True
                pz.save()
                await ctx.send('Pokemon messages enabled.')
            elif value == 'off':
                pz.active = False
                pz.save()
                await ctx.send('Pokemon messages disabled.')
            else:
                raise commands.BadArgument(f'Unable to process argument `{value}` for `{ctx.command}`')

        else:
            await ctx.send('Setup has not been run for this channel.')

    @config.command(name='zone', hidden=True)
    async def zone_sub(self, ctx, value: str):
        """Toggles if this pokemon zone is active or not."""
        if value == 'on':
            ctx.pz.active = True
            ctx.pz.save()
            await ctx.pz.discord_destination.send('Pokemon messages enabled.')
            await ctx.send('Pokemon messages enabled.')
        elif value == 'off':
            ctx.pz.active = False
            ctx.pz.save()
            await ctx.pz.discord_destination.send('Pokemon messages disabled.')
            await ctx.send('Pokemon messages disabled.')
        else:
            raise commands.BadArgument(f'Unable to process argument `{value}` for `{ctx.command}`')

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def info(self, ctx):
        """Displays the pokemon zone's configuration for a channel."""
        if ctx.channel.id in ctx.zones.zones:
            pz = ctx.zones.zones[ctx.channel.id][0]
            output = f'''Here is the pokemon zone configuration for this channel:
Name: `{pz.name}`
Status: `{pz.status}`
Coordinates: `{pz.latitude}, {pz.longitude}`
Radius: `{pz.radius}`
Pokemon: `{pz.filters['pokemon']}`'''
            await ctx.send(output)
        else:
            await ctx.send('This channel is not configured as a pokemon zone.')

    @config.command(name='info', hidden=True)
    async def info_sub(self, ctx):
        """Displays the pokemon zone's configuration for a channel."""
        output = f'''Here is the pokemon zone configuration for this channel:
Name: `{ctx.pz.name}`
Status: `{ctx.pz.status}`
Coordinates: `{ctx.pz.latitude}, {ctx.pz.longitude}`
Radius: `{ctx.pz.radius}`
Pokemon: `{ctx.pz.filters['pokemon']}`'''
        await ctx.send(output)

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def filter(self, ctx, *pokemon_numbers: str):
        """Allows for a list of pokemon numbers to enable filtering. Use `0` to clear the filter."""
        if len(pokemon_numbers) == 0:
            await ctx.author.send(f'Please provide at least one pokemon number for command `{ctx.command}`')
            return
        try:
            if ctx.channel.id in ctx.zones.zones:
                pz = ctx.zones.zones[ctx.channel.id][0]
                new_filter = []
                if pokemon_numbers[0] != '0':
                    for raid_level in pokemon_numbers:
                        new_filter.append(int(raid_level))
                pz.filters['pokemon'].clear()
                pz.filters['pokemon'] = sorted(new_filter)
                pz.save()
                await ctx.send(f"Updated pokemon filter list: `{pz.filters['pokemon']}`")
            else:
                await ctx.send('Setup has not been run for this channel.')
        except ValueError:
            await ctx.send(f'Unable to process filter. Please verify your input: `{ctx.message.content}`')
            pass

    @config.command(name='filter', hidden=True)
    async def filter_sub(self, ctx, *pokemon_numbers: str):
        """Allows for a list of pokemon numbers to enable filtering. Use `0` to clear the filter."""
        if len(pokemon_numbers) == 0:
            await ctx.author('Please provide at least one pokemon number for command `{}`'.format(ctx.command))
            return
        try:
            new_filter = []
            if pokemon_numbers[0] != '0':
                for raid_level in pokemon_numbers:
                    new_filter.append(int(raid_level))
            ctx.pz.filters['pokemon'].clear()
            ctx.pz.filters['pokemon'] = sorted(new_filter)
            ctx.pz.save()
            await ctx.pz.discord_destination.send(f"Updated pokemon filter list: `{ctx.pz.filters['pokemon']}`")
            await ctx.send(f"Updated pokemon filter list: `{ctx.pz.filters['pokemon']}`")
        except ValueError:
            await ctx.pz.discord_destination.send(
                f'Unable to process filter. Please verify your input: `{ctx.message.content}`')
            pass


def setup(bot):
    bot.add_cog(Zones(bot))
