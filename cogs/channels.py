import discord
from discord.ext import commands

class Channels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.default_channels = [
            "TED", "Substack", "Medium",
            "Youtube", "Facebook", "Image", "Idea", "Video"
        ]

    @commands.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup_channels(self, ctx):
        """সব default channel তৈরি করে"""
        guild = ctx.guild
        created = []
        existing = []

        for name in self.default_channels:
            found = discord.utils.get(guild.channels, name=name.lower())
            if not found:
                await guild.create_text_channel(name.lower())
                created.append(name)
            else:
                existing.append(name)

        embed = discord.Embed(title="📁 Channel Setup", color=0x57F287)
        if created:
            embed.add_field(name="✅ তৈরি হয়েছে", value=", ".join(created), inline=False)
        if existing:
            embed.add_field(name="ℹ আগে থেকে ছিল", value=", ".join(existing), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="createchannel")
    @commands.has_permissions(administrator=True)
    async def create_channel(self, ctx, *, name: str):
        """একটি নির্দিষ্ট channel তৈরি করে"""
        channel = await ctx.guild.create_text_channel(name.lower())
        await ctx.send(f"✅ {channel.mention} channel তৈরি হয়েছে!")

    @setup_channels.error
    @create_channel.error
    async def permission_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ তোমার Administrator permission নেই।")

async def setup(bot):
    await bot.add_cog(Channels(bot))
