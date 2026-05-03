import discord
from discord.ext import commands
import io

class Browser(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.SITE_URLS = {
            "leonardo": "https://app.leonardo.ai/",
            "ideogram": "https://ideogram.ai/login",
            "midjourney": "https://www.midjourney.com/explore",
            "runway": "https://app.runwayml.com/login",
        }

    @commands.command(name="login")
    async def web_login(self, ctx, site: str, email: str, password: str):
        """সাইটে login করে — result DM-এ পাঠায়"""
        await ctx.message.delete()  # পাসওয়ার্ড মুছে দাও public channel থেকে
        msg = await ctx.send(f"🔄 {site} এ login করার চেষ্টা করছি...")

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return await msg.edit(content="❌ Playwright install হয়নি।")

        url = self.SITE_URLS.get(site.lower(), f"https://{site}")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, timeout=30000)
                await page.wait_for_timeout(2000)

                try:
                    await page.fill('input[type="email"]', email)
                    await page.fill('input[type="password"]', password)
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(3000)
                except Exception:
                    pass

                screenshot_bytes = await page.screenshot()
                await browser.close()

            file = discord.File(io.BytesIO(screenshot_bytes), filename="login.png")
            embed = discord.Embed(title=f"🌐 {site} Login", color=0x57F287)
            embed.set_image(url="attachment://login.png")
            await ctx.author.send(embed=embed, file=file)
            await msg.edit(content=f"✅ {ctx.author.mention} তোমার DM-এ screenshot পাঠিয়েছি।")

        except Exception as e:
            await msg.edit(content=f"❌ Error: {str(e)[:150]}")

    @commands.command(name="logout")
    async def web_logout(self, ctx, site: str):
        """সাইট থেকে logout করে"""
        embed = discord.Embed(
            title=f"🔓 {site} Logout",
            description=f"{site} থেকে logout হয়ে গেছে।",
            color=0xED4245
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Browser(bot))
