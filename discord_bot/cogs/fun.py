import discord
from discord.ext import commands
from Utils.sqlManager import SQLManager
from config import Config

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)

    @commands.command(name='roster')
    async def show_roster(self, ctx):
        """Shows the top 10 players by Trust Score."""
        players = self.db.get_full_roster_including_leavers()
        # Filter active only
        active = [p for p in players if p['is_in_clan']]
        top_10 = active[:10]
        
        msg = "**🏆 Top 10 Clan Members**\n"
        for i, p in enumerate(top_10, 1):
            msg += f"{i}. **{p['name']}** (TH{p['town_hall_level']}) - Score: {p.get('trust_score', 50)}\n"
            
        await ctx.send(msg)

    @commands.command(name='best')
    async def best_attacker(self, ctx):
        """Shows the player with the highest Trust Score."""
        players = self.db.get_full_roster_including_leavers()
        if not players:
            await ctx.send("No players found.")
            return
            
        best = players[0]
        await ctx.send(f"👑 **The MVP is {best['name']}** with a Trust Score of {best.get('trust_score', 50)}!")

    @commands.command(name='worst')
    async def worst_attacker(self, ctx):
        """Shows the player with the lowest Trust Score (Active only)."""
        players = self.db.get_full_roster_including_leavers()
        active = [p for p in players if p['is_in_clan']]
        
        if not active:
            await ctx.send("No active players found.")
            return
            
        worst = active[-1]
        await ctx.send(f"🤡 **{worst['name']}** needs to practice! (Score: {worst.get('trust_score', 50)})")

async def setup(bot):
    await bot.add_cog(Fun(bot))
