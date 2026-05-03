import discord
from discord.ext import commands
from groq import Groq
import os

# Groq client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# প্রতি user এর conversation history আলাদা রাখা হবে
conversation_histories = {}

# System prompt - তোমার personal AI এর personality
SYSTEM_PROMPT = """তুমি একজন personal AI assistant। তুমি বাংলা এবং English দুটো ভাষাতেই কথা বলতে পারো।
তুমি বন্ধুর মতো, সৎ এবং helpful। User যে ভাষায় কথা বলবে তুমি সেই ভাষায় উত্তর দেবে।
আগের কথোপকথন মনে রেখে context অনুযায়ী উত্তর দেবে।"""

MAX_HISTORY = 20  # মনে রাখার সর্বোচ্চ message সংখ্যা


class Chat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_history(self, user_id: int):
        """User এর history না থাকলে নতুন তৈরি করো"""
        if user_id not in conversation_histories:
            conversation_histories[user_id] = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]
        return conversation_histories[user_id]

    def trim_history(self, user_id: int):
        """History অনেক বড় হয়ে গেলে পুরনো messages বাদ দাও (system prompt রাখো)"""
        history = conversation_histories[user_id]
        if len(history) > MAX_HISTORY + 1:  # +1 for system prompt
            conversation_histories[user_id] = [history[0]] + history[-(MAX_HISTORY):]

    @commands.command(name="chat")
    async def chat(self, ctx, *, message: str):
        """AI এর সাথে কথা বলো — !chat [তোমার message]"""
        user_id = ctx.author.id
        history = self.get_history(user_id)

        # User message যোগ করো
        history.append({"role": "user", "content": message})

        # Typing indicator দেখাও
        async with ctx.typing():
            try:
                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=history,
                    max_tokens=2000,
                    temperature=0.7,
                )

                reply = response.choices[0].message.content

                # AI reply history তে যোগ করো
                history.append({"role": "assistant", "content": reply})
                self.trim_history(user_id)

                # Reply অনেক বড় হলে ভেঙে পাঠাও (Discord 2000 char limit)
                if len(reply) > 1900:
                    chunks = [reply[i:i+1900] for i in range(0, len(reply), 1900)]
                    for chunk in chunks:
                        await ctx.reply(chunk)
                else:
                    await ctx.reply(reply)

            except Exception as e:
                await ctx.reply(f"❌ Error হয়েছে: `{e}`")

    @commands.command(name="clearchat")
    async def clear_chat(self, ctx):
        """তোমার conversation history মুছে নতুন শুরু করো — !clearchat"""
        user_id = ctx.author.id
        if user_id in conversation_histories:
            del conversation_histories[user_id]
        await ctx.reply("🗑️ তোমার conversation history মুছে ফেলা হয়েছে! নতুন করে শুরু করো।")

    @commands.command(name="chathistory")
    async def chat_history(self, ctx):
        """কতটুকু conversation history আছে দেখো — !chathistory"""
        user_id = ctx.author.id
        history = conversation_histories.get(user_id, [])
        msg_count = len(history) - 1  # system prompt বাদ দিয়ে
        if msg_count <= 0:
            await ctx.reply("📭 এখনো কোনো conversation নেই। `!chat` দিয়ে শুরু করো!")
        else:
            await ctx.reply(f"📊 তোমার history তে **{msg_count}** টা message আছে। (সর্বোচ্চ {MAX_HISTORY} টা মনে রাখা হয়)")


async def setup(bot):
    await bot.add_cog(Chat(bot))
