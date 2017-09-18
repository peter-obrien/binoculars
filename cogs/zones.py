import discord
from decimal import Decimal, InvalidOperation
from discord.ext import commands


class Zones:
    """Pokemon zone setup and configuration. To invoke user must have Manage Channels permission."""

    def __init__(self, bot):
        self.bot = bot

    async def __after_invoke(self, ctx):
        if isinstance(ctx.channel, discord.TextChannel):
            await ctx.message.delete()

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def setup(self, ctx, latitude: str, longitude: str):
        """Creates a pokemon zone with radius 5km. If used again replaces the coordinates."""
        try:
            lat = Decimal(latitude)
            lon = Decimal(longitude)

            if ctx.channel.id in ctx.zones.zones:
                rz = ctx.zones.zones[ctx.channel.id]
                rz.latitude = lat
                rz.longitude = lon
                rz.save()
                await ctx.send('Pokemon zone coordinates updated')
            else:
                rz = ctx.zones.create_zone(ctx.guild.id, ctx.channel.id, lat, lon)
                rz.discord_destination = ctx.channel
                await ctx.send('Pokemon zone created')
        except Exception as e:
            print(e)
            await ctx.send('There was an error handling your request.\n\n`{}`'.format(ctx.message.content))

    @commands.command(hidden=True, usage='xxx.x')
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
                    rz = ctx.zones.zones[ctx.channel.id]
                    rz.radius = radius
                    rz.save()
                    await ctx.send('Radius updated')
                else:
                    await ctx.send('Setup has not been run for this channel.')
        except InvalidOperation:
            raise commands.BadArgument('Invalid radius: {}'.format(value))

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def zone(self, ctx, value: str):
        """Toggles if this pokemon zone is active or not."""
        if ctx.channel.id in ctx.zones.zones:
            rz = ctx.zones.zones[ctx.channel.id]
            if value == 'on':
                rz.active = True
                rz.save()
                await ctx.send('Pokemon messages enabled.')
            elif value == 'off':
                rz.active = False
                rz.save()
                await ctx.send('Pokemon messages disabled.')
            else:
                raise commands.BadArgument('Unable to process argument `{}` for `{}`'.format(value, ctx.command))

        else:
            await ctx.send('Setup has not been run for this channel.')

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def info(self, ctx):
        """Displays the pokemon zone's configuration for a channel."""
        if ctx.channel.id in ctx.zones.zones:
            rz = ctx.zones.zones[ctx.channel.id]
            output = '''Here is the pokemon zone configuration for this channel:
Status: `{}`
Coordinates: `{}, {}`
Radius: `{}`
Pokemon: `{}`'''.format(rz.status, rz.latitude, rz.longitude, rz.radius, rz.filters['pokemon'])
            await ctx.send(output)
        else:
            await ctx.send('This channel is not configured as a pokemon zone.')

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def filter(self, ctx, *pokemon_numbers: str):
        """Allows for a list of pokemon numbers to enable filtering. Use `0` to clear the filter."""
        if len(pokemon_numbers) == 0:
            await ctx.author('Please provide at least one pokemon number for command `{}`'.format(ctx.command))
            return
        try:
            if ctx.channel.id in ctx.zones.zones:
                rz = ctx.zones.zones[ctx.channel.id]
                new_filter = []
                if pokemon_numbers[0] != '0':
                    for raid_level in pokemon_numbers:
                        new_filter.append(int(raid_level))
                rz.filters['pokemon'].clear()
                rz.filters['pokemon'] = sorted(new_filter)
                rz.save()
                await ctx.send('Updated pokemon filter list: `{}`'.format(rz.filters['pokemon']))
            else:
                await ctx.send('Setup has not been run for this channel.')
        except ValueError:
            await ctx.send('Unable to process filter. Please verify your input: `{}`'.format(ctx.message.content))
            pass


def setup(bot):
    bot.add_cog(Zones(bot))
