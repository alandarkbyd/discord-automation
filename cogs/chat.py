import discord
from discord.ext import commands
from groq import Groq
import os

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

conversation_histories = {}

SYSTEM_PROMPT = """তুমি একজন personal AI assistant।
তুমি বাংলা এবং English দুটো ভাষাতেই কথা বলতে পারো।
তুমি বন্ধুর মতো, সৎ এবং helpful।
User যে ভাষায় কথা বলবে তুমি সেই ভাষায় উত্তর দেবে।
আগের কথোপকথন মনে রেখে context অনুযায়ী উত্তর দেবে।"""

MAX_HISTORY = 20

MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]


def get_completion(messages, max_tokens=2024):
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


def get_history(user_id: int):
    if user_id not in conversation_histories:
        conversation_histories[user_id] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
    return conversation_histories[user_id]


def trim_history(user_id: int):
    history = conversation_histories[user_id]
    if len(history) > MAX_HISTORY + 1:
        conversation_histories[user_id] = [history[0]] + history[-(MAX_HISTORY):]


class Chat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="chat")
    async def chat(self, ctx, *, message: str):
        """AI এর সাথে কথা বলো — !chat [তোমার message]"""
        user_id = ctx.author.id
        history = get_history(user_id)
        history.append({"role": "user", "content": message})

        async with ctx.typing():
            try:
                response = get_completion(history)
                reply = response.choices[0].message.content

                history.append({"role": "assistant", "content": reply})
                trim_history(user_id)

                if len(reply) > 1900:
                    chunks = [reply[i:i+1900] for i in range(0, len(reply), 1900)]
                    for chunk in chunks:
                        await ctx.reply(chunk)
                else:
                    await ctx.reply(reply)

            except Exception as e:
                await ctx.reply(f"❌ Error: `{e}`")

    @commands.command(name="clearchat")
    async def clear_chat(self, ctx):
        """Conversation history মুছো — !clearchat"""
        if ctx.author.id in conversation_histories:
            del conversation_histories[ctx.author.id]
        await ctx.reply("🗑️ তোমার conversation history মুছে ফেলা হয়েছে!")

    @commands.command(name="chathistory")
    async def chat_history(self, ctx):
        """কতটুকু history আছে দেখো — !chathistory"""
        history = conversation_histories.get(ctx.author.id, [])
        msg_count = len(history) - 1
        if msg_count <= 0:
            await ctx.reply("📭 এখনো কোনো conversation নেই। `!chat` দিয়ে শুরু করো!")
        else:
            await ctx.reply(f"📊 তোমার history তে **{msg_count}** টা message আছে। (সর্বোচ্চ {MAX_HISTORY} টা মনে রাখা হয়)")


async def setup(bot):
    await bot.add_cog(Chat(bot))
