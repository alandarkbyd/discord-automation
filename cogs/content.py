import discord
from discord.ext import commands
from groq import Groq
import os
import urllib.parse
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import send_to_channel

class Content(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def ask_groq(self, prompt: str, max_tokens: int = 600) -> str:
        response = self.groq.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

    @commands.command(name="ted")
    async def find_ted(self, ctx, *, topic: str):
        """TED Talk খোঁজে → #ted channel এ পাঠায়"""
        await ctx.typing()
        prompt = f"""'{topic}' বিষয়ে সেরা 2টি TED Talk recommend করো।
প্রতিটির জন্য দাও:
1. Title
2. Speaker  
3. TED.com link (https://www.ted.com/talks/ format)
4. কেন দেখব (1 বাক্যে)
শুধু এই তথ্য দাও, অন্য কথা না।"""

        result = self.ask_groq(prompt)
        embed = discord.Embed(
            title=f"🎤 TED Talks: {topic}",
            description=result,
            color=0xE62B1E
        )
        embed.add_field(
            name="সরাসরি সার্চ",
            value=f"[TED.com এ খোঁজো](https://www.ted.com/search?q={urllib.parse.quote(topic)})"
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name} • ted.com")
        await send_to_channel(ctx, "ted", embed=embed)

    @commands.command(name="medium")
    async def find_medium(self, ctx, *, topic: str):
        """Medium আর্টিকেল খোঁজে → #medium channel এ পাঠায়"""
        await ctx.typing()
        search_url = f"https://medium.com/search?q={urllib.parse.quote(topic)}"
        prompt = f"'{topic}' বিষয়ে Medium.com এ কী ধরনের article পাওয়া যায় সেটা 3-4 বাক্যে বলো।"
        result = self.ask_groq(prompt, max_tokens=250)

        embed = discord.Embed(title=f"📝 Medium: {topic}", description=result, color=0x000000)
        embed.add_field(name="সার্চ করো", value=f"[Medium এ খোঁজো]({search_url})", inline=False)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await send_to_channel(ctx, "medium", embed=embed)

    @commands.command(name="substack")
    async def find_substack(self, ctx, *, topic: str):
        """Substack newsletter খোঁজে → #substack channel এ পাঠায়"""
        await ctx.typing()
        search_url = f"https://substack.com/search/{urllib.parse.quote(topic)}"
        prompt = f"'{topic}' বিষয়ে Substack এ কী ধরনের newsletter পাওয়া যায় সেটা সংক্ষেপে বলো।"
        result = self.ask_groq(prompt, max_tokens=250)

        embed = discord.Embed(title=f"📧 Substack: {topic}", description=result, color=0xFF6719)
        embed.add_field(name="সার্চ করো", value=f"[Substack এ খোঁজো]({search_url})", inline=False)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await send_to_channel(ctx, "substack", embed=embed)

async def setup(bot):
    await bot.add_cog(Content(bot))
