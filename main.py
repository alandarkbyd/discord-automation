import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()
PREFIX = os.getenv("PREFIX", "!")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} চালু হয়েছে!")
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, name=f"{PREFIX}help"
    ))

@bot.command(name="help")
async def help_cmd(ctx):
    embed = discord.Embed(title="📋 Bot Commands", color=0x5865F2)
    embed.add_field(name="Channel", value="`!setup` `!createchannel [নাম]`", inline=False)
    embed.add_field(name="Content", value="`!ted [বিষয়]` `!medium [বিষয়]` `!substack [বিষয়]`", inline=False)
    embed.add_field(name="Media", value="`!image [prompt]` `!video [prompt]`", inline=False)
    embed.add_field(name="TempMail", value="`!tempmail` `!getmail` `!newmail`", inline=False)
    embed.add_field(name="Browser", value="`!login [site] [email] [pass]` `!logout [site]`", inline=False)
    await ctx.send(embed=embed)

async def load_cogs():
    for cog in ["channels", "content", "media", "tempmail", "browser"]:
        try:
            await bot.load_extension(f"cogs.{cog}")
            print(f"✅ {cog} লোড হয়েছে")
        except Exception as e:
            print(f"❌ {cog} লোড হয়নি: {e}")

@bot.event
async def setup_hook():
    await load_cogs()

keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
