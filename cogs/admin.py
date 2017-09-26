import discord
from discord.ext import commands


class Admin:
    """Commands for the owner, admins, and mods."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.guild_only()
    async def clear(self, ctx, msg_count_to_delete: int = 5):
        """Deletes groups of messages. Cannot delete messages older than 14 days."""
        if ctx.author == ctx.guild.owner:
            try:
                message_to_delete = []
                async for message in ctx.message.channel.history(limit=msg_count_to_delete):
                    message_to_delete.append(message)
                await ctx.channel.delete_messages(message_to_delete)
            except discord.HTTPException:
                # Assume that messages older than 14 days were found and delete one at a time.
                async for message in ctx.message.channel.history(limit=msg_count_to_delete):
                    await message.delete()
        else:
            raise commands.CommandInvokeError('User cannot run this command.')

    @commands.command(hidden=True)
    @commands.is_owner()
    async def logout(self, ctx):
        """Logs the bot out of Discord."""
        print('Logout command invoked. Shutting down.')
        await ctx.message.delete()
        await ctx.bot.logout()


def setup(bot):
    bot.add_cog(Admin(bot))
