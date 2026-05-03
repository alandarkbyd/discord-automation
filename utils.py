import discord

async def send_to_channel(ctx, channel_name: str, embed: discord.Embed = None, content: str = None, file=None):
    """
    Result সবসময় নির্দিষ্ট channel-এ পাঠায়।
    যেই channel নেই সেটা জানিয়ে দেয়।
    """
    target = discord.utils.get(ctx.guild.text_channels, name=channel_name.lower())

    if target is None:
        # Channel নেই — জানিয়ে দাও, সেখানেই পাঠাও
        warn = await ctx.send(
            f"⚠ **#{channel_name}** channel নেই! `!setup` দিয়ে তৈরি করো।\nএখানেই result দিচ্ছি:"
        )
        if embed:
            await ctx.send(embed=embed, file=file if file else discord.utils.MISSING)
        elif content:
            await ctx.send(content)
        return

    # Command যেখান থেকে দেওয়া হয়েছে সেখানে ছোট confirmation
    if ctx.channel.id != target.id:
        await ctx.send(f"✅ Result পাঠানো হয়েছে → {target.mention}", delete_after=5)

    # Target channel-এ result পাঠাও
    if embed:
        await target.send(embed=embed, file=file if file else discord.utils.MISSING)
    elif content:
        await target.send(content)
