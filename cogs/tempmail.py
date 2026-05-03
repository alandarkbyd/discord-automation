import discord
from discord.ext import commands
import aiohttp
import random
import string
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import send_to_channel

class TempMail(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}
        self.BASE = "https://api.mail.tm"

    async def _create_account(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.BASE}/domains") as r:
                if r.status != 200:
                    return None, None, None
                domains = await r.json()
                domain = domains["hydra:member"][0]["domain"]

            name = ''.join(random.choices(string.ascii_lowercase, k=10))
            email = f"{name}@{domain}"
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

            async with session.post(
                f"{self.BASE}/accounts",
                json={"address": email, "password": password}
            ) as r:
                if r.status != 201:
                    return None, None, None

            async with session.post(
                f"{self.BASE}/token",
                json={"address": email, "password": password}
            ) as r:
                data = await r.json()
                token = data.get("token")

            return email, password, token

    @commands.command(name="tempmail")
    async def get_temp_mail(self, ctx):
        """নতুন temp email → সেখানেই reply (DM safe)"""
        await ctx.typing()
        email, _, token = await self._create_account()

        if not email:
            return await ctx.send("❌ Email তৈরি করা যায়নি। আবার চেষ্টা করো।")

        self.sessions[ctx.author.id] = {"token": token, "address": email}

        embed = discord.Embed(title="📧 নতুন TempMail তৈরি হয়েছে!", color=0x57F287)
        embed.add_field(name="📮 Email Address", value=f"`{email}`", inline=False)
        embed.add_field(name="📬 মেইল দেখতে", value="`!getmail` লিখো", inline=False)
        embed.add_field(name="🔄 নতুন mail নিতে", value="`!newmail` লিখো", inline=False)
        # TempMail result এখানেই — private info, DM-এ পাঠানো ভালো
        try:
            await ctx.author.send(embed=embed)
            await ctx.send("✅ Email address তোমার DM-এ পাঠিয়েছি!")
        except discord.Forbidden:
            await ctx.send(embed=embed)  # DM বন্ধ থাকলে এখানেই

    @commands.command(name="getmail")
    async def get_messages(self, ctx):
        """Inbox দেখায় — DM-এ (verification code সহ)"""
        data = self.sessions.get(ctx.author.id)
        if not data:
            return await ctx.send("আগে `!tempmail` দিয়ে email নাও।")

        await ctx.typing()
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.BASE}/messages",
                headers={"Authorization": f"Bearer {data['token']}"}
            ) as r:
                result = await r.json()
                messages = result.get("hydra:member", [])

        if not messages:
            return await ctx.send("📭 এখনো কোনো মেইল আসেনি। কিছুক্ষণ অপেক্ষা করো।")

        embed = discord.Embed(
            title=f"📬 Inbox — {data['address']}",
            color=0x5865F2
        )

        for msg in messages[:3]:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE}/messages/{msg['id']}",
                    headers={"Authorization": f"Bearer {data['token']}"}
                ) as r:
                    full = await r.json()

            body = full.get("text", "")[:400].strip()
            embed.add_field(
                name=f"✉ From: {msg['from']['address']}",
                value=f"**Subject:** {msg['subject']}\n```{body}```",
                inline=False
            )

        try:
            await ctx.author.send(embed=embed)
            await ctx.send("✅ Inbox তোমার DM-এ পাঠিয়েছি!")
        except discord.Forbidden:
            await ctx.send(embed=embed)

    @commands.command(name="newmail")
    async def new_mail(self, ctx):
        """নতুন email address নিয়ে আসে"""
        await self.get_temp_mail(ctx)

async def setup(bot):
    await bot.add_cog(TempMail(bot))
