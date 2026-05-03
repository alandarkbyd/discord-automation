import discord
from discord.ext import commands
from groq import Groq
import os
import json
import re

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

pending_drafts = {}

MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]


def get_completion(messages, max_tokens=4048):
    for model in MODELS:
        try:
            return groq_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
            )
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                continue
            raise
    raise Exception("সব model এর limit শেষ! কিছুক্ষণ পর আবার চেষ্টা করো।")


def extract_json(text: str) -> dict:
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"JSON পাওয়া যায়নি। Raw response:\n{text[:300]}")


async def generate_post(topic: str, language: str = "বাংলা") -> dict:
    response = get_completion([
        {
            "role": "system",
            "content": (
                f"You are an expert content writer. Write a Substack post in {language}.\n"
                "IMPORTANT: Your entire response must be ONLY a valid JSON object. "
                "No explanation, no markdown, no extra text before or after.\n"
                'Respond with exactly this structure (no extra keys):\n'
                '{"title": "post title here", "subtitle": "subtitle here", "body": "full post content here"}'
            )
        },
        {
            "role": "user",
            "content": f"Write an engaging Substack post about: {topic}"
        }
    ])
    raw = response.choices[0].message.content
    return extract_json(raw)


class SubstackCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="writepost")
    async def write_post(self, ctx, lang: str = "bangla", *, topic: str):
        """AI দিয়ে Substack post লিখবে — !writepost [bangla/english] [বিষয়]"""
        language = "বাংলা" if lang.lower() in ("bangla", "bn", "বাংলা") else "English"
        msg = await ctx.reply(f"✍️ {language} তে post লিখছি, একটু অপেক্ষা করো...")

        try:
            post = await generate_post(topic, language)
            pending_drafts[ctx.author.id] = post

            embed = discord.Embed(
                title=f"📝 {post['title']}",
                description=post.get("subtitle", ""),
                color=0xFF6719
            )
            preview = post["body"][:800] + ("..." if len(post["body"]) > 800 else "")
            embed.add_field(name="Preview", value=preview, inline=False)
            embed.set_footer(text="পুরো post পেতে !getpost | বাদ দিতে !cancelpost")

            await msg.edit(content="✅ Post তৈরি হয়েছে!", embed=embed)

        except ValueError as e:
            await msg.edit(content=f"❌ {e}")
        except Exception as e:
            await msg.edit(content=f"❌ Error: `{e}`")

    @commands.command(name="getpost")
    async def get_post(self, ctx):
        """পুরো post copy করার জন্য দেখাও — !getpost"""
        user_id = ctx.author.id
        if user_id not in pending_drafts:
            await ctx.reply("❌ কোনো post নেই। আগে `!writepost [বিষয়]` দিয়ে লেখো।")
            return

        post = pending_drafts[user_id]

        await ctx.reply(f"**📌 Title:**\n```\n{post['title']}\n```")

        if post.get("subtitle"):
            await ctx.reply(f"**📌 Subtitle:**\n```\n{post['subtitle']}\n```")

        body = post["body"]
        chunks = [body[i:i+1900] for i in range(0, len(body), 1900)]
        for i, chunk in enumerate(chunks):
            label = f"**📄 Body ({i+1}/{len(chunks)}):**\n" if len(chunks) > 1 else "**📄 Body:**\n"
            await ctx.reply(f"{label}```\n{chunk}\n```")

        await ctx.reply("✅ Copy করে Substack এ paste করো!\n🔗 https://substack.com/publish/post/new")

    @commands.command(name="cancelpost")
    async def cancel_post(self, ctx):
        """Pending post বাদ দাও — !cancelpost"""
        if ctx.author.id in pending_drafts:
            del pending_drafts[ctx.author.id]
            await ctx.reply("🗑️ Post বাদ দেওয়া হয়েছে।")
        else:
            await ctx.reply("❌ কোনো pending post নেই।")


async def setup(bot):
    await bot.add_cog(SubstackCog(bot))
