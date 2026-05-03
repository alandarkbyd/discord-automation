import discord
from discord.ext import commands
import urllib.parse
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import send_to_channel

class Media(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="image")
    async def generate_image(self, ctx, *, prompt: str):
        """Image generation লিংক পাঠায় → #image channel এ"""
        encoded = urllib.parse.quote(prompt)
        embed = discord.Embed(
            title="🎨 Image Generation",
            description=f"**Prompt:** {prompt}",
            color=0x5865F2
        )
        embed.add_field(
            name="1. Whisk AI (Google Labs) — সেরা",
            value=f"[labs.google/fx/tools/whisk](https://labs.google/fx/tools/whisk)\nPrompt দাও: `{prompt}`",
            inline=False
        )
        embed.add_field(
            name="2. Ideogram AI",
            value=f"[ideogram.ai](https://ideogram.ai/generate?prompt={encoded})",
            inline=False
        )
        embed.add_field(
            name="3. Adobe Firefly",
            value="[firefly.adobe.com](https://firefly.adobe.com)",
            inline=False
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await send_to_channel(ctx, "image", embed=embed)

    @commands.command(name="video")
    async def generate_video(self, ctx, *, prompt: str):
        """Video generation লিংক পাঠায় → #video channel এ"""
        embed = discord.Embed(
            title="🎬 Video Generation",
            description=f"**Prompt:** {prompt}",
            color=0xEB459E
        )
        embed.add_field(
            name="1. Meta AI",
            value=f"[meta.ai](https://www.meta.ai)\nPrompt: `{prompt} — create a short video`",
            inline=False
        )
        embed.add_field(
            name="2. Runway ML — Free Trial",
            value="[runwayml.com](https://runwayml.com)",
            inline=False
        )
        embed.add_field(
            name="3. Pika Labs — Free",
            value="[pika.art](https://pika.art)",
            inline=False
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await send_to_channel(ctx, "video", embed=embed)

    @commands.command(name="idea")
    async def post_idea(self, ctx, *, idea: str):
        """Idea পোস্ট করে → #idea channel এ"""
        embed = discord.Embed(
            title="💡 নতুন Idea",
            description=idea,
            color=0xFEE75C
        )
        embed.set_footer(text=f"Posted by {ctx.author.display_name}")
        await send_to_channel(ctx, "idea", embed=embed)

async def setup(bot):
    await bot.add_cog(Media(bot))
