import discord
from discord.ext import commands
from groq import Groq
import aiohttp
import os
import json
import re

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SUBSTACK_SID = os.getenv("SUBSTACK_SID")
SUBSTACK_URL = os.getenv("SUBSTACK_URL")  # example: https://yourname.substack.com

# Draft গুলো temporarily রাখার জন্য
pending_drafts = {}


def get_headers():
    return {
        "Cookie": SUBSTACK_SID,  # পুরো cookie string
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": SUBSTACK_URL,
        "Origin": SUBSTACK_URL,  # ← এটা যোগ করো
    }

def extract_json(text: str) -> dict:
    """Raw text থেকে JSON বের করার multiple fallback"""
    # Attempt 1: সরাসরি parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Attempt 2: ```json ... ``` block থেকে বের করো
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Attempt 3: প্রথম { থেকে শেষ } পর্যন্ত নাও
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"JSON পাওয়া যায়নি। Raw response:\n{text[:300]}")


async def generate_post(topic: str, language: str = "বাংলা") -> dict:
    """Groq দিয়ে post তৈরি করো"""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
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
        ],
        max_tokens=2048,
        temperature=0.7,
    )

    raw = response.choices[0].message.content
    return extract_json(raw)


async def create_draft(title: str, subtitle: str, body: str) -> dict:
    """Substack এ draft তৈরি করো"""
    payload = {
        "draft_title": title,
        "draft_subtitle": subtitle,
        "draft_body": json.dumps({
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": body}]
                }
            ]
        }),
        "draft_podcast_url": "",
        "draft_podcast_duration": None,
        "draft_video_upload_id": None,
        "draft_podcast_upload_id": None,
        "draft_podcast_preview_upload_id": None,
        "draft_cover_image": None,
        "section_chosen": False,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{SUBSTACK_URL}/api/v1/drafts",
            headers=get_headers(),
            json=payload
        ) as resp:
            if resp.status in (200, 201):
                return await resp.json()
            else:
                text = await resp.text()
                raise Exception(f"Draft তৈরি হয়নি। Status: {resp.status} — {text}")


async def publish_draft(draft_id: int) -> bool:
    """Draft টা publish করো"""
    payload = {
        "send": True,
        "share_automatically": False,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{SUBSTACK_URL}/api/v1/drafts/{draft_id}/publish",
            headers=get_headers(),
            json=payload
        ) as resp:
            return resp.status in (200, 201)


class SubstackCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="writepost")
    async def write_post(self, ctx, lang: str = "bangla", *, topic: str):
        """AI দিয়ে Substack post লিখবে — !writepost [bangla/english] [বিষয়]"""
        if not SUBSTACK_SID or not SUBSTACK_URL:
            await ctx.reply("❌ `SUBSTACK_SID` বা `SUBSTACK_URL` Railway তে set করা নেই!")
            return

        language = "বাংলা" if lang.lower() in ("bangla", "bn", "বাংলা") else "English"
        msg = await ctx.reply(f"✍️ {language} তে post লিখছি, একটু অপেক্ষা করো...")

        try:
            post = await generate_post(topic, language)

            # Draft হিসেবে save করো user এর জন্য
            pending_drafts[ctx.author.id] = post

            embed = discord.Embed(
                title=f"📝 {post['title']}",
                description=post.get("subtitle", ""),
                color=0xFF6719
            )

            # Body এর প্রথম ৮০০ char preview দেখাও
            preview = post["body"][:800] + ("..." if len(post["body"]) > 800 else "")
            embed.add_field(name="Preview", value=preview, inline=False)
            embed.set_footer(text="Publish করতে !publishpost | বাদ দিতে !cancelpost")

            await msg.edit(content="✅ Post তৈরি হয়েছে! দেখো:", embed=embed)

        except ValueError as e:
            await msg.edit(content=f"❌ {e}")
        except Exception as e:
            await msg.edit(content=f"❌ Error: `{e}`")

    @commands.command(name="publishpost")
    async def publish_post(self, ctx):
        """লেখা post টা Substack এ publish করো — !publishpost"""
        user_id = ctx.author.id

        if user_id not in pending_drafts:
            await ctx.reply("❌ কোনো pending post নেই। আগে `!writepost [বিষয়]` দিয়ে লেখো।")
            return

        msg = await ctx.reply("📤 Substack এ publish করছি...")

        try:
            post = pending_drafts[user_id]

            draft = await create_draft(post["title"], post.get("subtitle", ""), post["body"])
            draft_id = draft.get("id")

            if not draft_id:
                await msg.edit(content="❌ Draft তৈরি হয়নি। Cookie expire হয়নি তো?")
                return

            success = await publish_draft(draft_id)

            if success:
                del pending_drafts[user_id]
                await msg.edit(content=f"🎉 **Post publish হয়েছে!**\n🔗 {SUBSTACK_URL}")
            else:
                await msg.edit(content="❌ Publish হয়নি। Cookie বা permission চেক করো।")

        except Exception as e:
            await msg.edit(content=f"❌ Error: `{e}`")

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
