import discord
from discord.ext import commands
from groq import Groq
import aiohttp
import os
import json

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SUBSTACK_SID = os.getenv("SUBSTACK_SID")
SUBSTACK_URL = os.getenv("SUBSTACK_URL")  # example: https://yourname.substack.com

# Draft গুলো temporarily রাখার জন্য
pending_drafts = {}


def get_headers():
    return {
        "Cookie": f"substack.sid={SUBSTACK_SID}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Referer": SUBSTACK_URL,
    }


async def generate_post(topic: str) -> dict:
    """Groq দিয়ে post তৈরি করো"""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": """তুমি একজন expert content writer। 
                তোমাকে একটা Substack post লিখতে হবে।
                Response শুধুমাত্র JSON format এ দাও, অন্য কিছু না।
                Format:
                {
                  "title": "post এর title",
                  "subtitle": "একটা আকর্ষণীয় subtitle",
                  "body": "পুরো post এর content (markdown format এ)"
                }"""
            },
            {
                "role": "user",
                "content": f"এই বিষয়ে একটা engaging Substack post লেখো: {topic}"
            }
        ],
        max_tokens=2048,
        temperature=0.7,
    )

    raw = response.choices[0].message.content
    # JSON parse করো
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


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
    async def write_post(self, ctx, *, topic: str):
        """বিষয় দিলে AI দিয়ে Substack post লিখবে — !writepost [বিষয়]"""
        if not SUBSTACK_SID or not SUBSTACK_URL:
            await ctx.reply("❌ `SUBSTACK_SID` বা `SUBSTACK_URL` Railway তে set করা নেই!")
            return

        msg = await ctx.reply("✍️ Post লিখছি, একটু অপেক্ষা করো...")

        try:
            post = await generate_post(topic)

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

        except json.JSONDecodeError:
            await msg.edit(content="❌ AI এর response parse করা যায়নি। আবার চেষ্টা করো।")
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

            # Draft তৈরি করো
            draft = await create_draft(post["title"], post.get("subtitle", ""), post["body"])
            draft_id = draft.get("id")

            if not draft_id:
                await msg.edit(content="❌ Draft তৈরি হয়নি। Cookie expire হয়নি তো?")
                return

            # Publish করো
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
