import discord
from discord.ext import commands, tasks
import coc
import asyncio
import os
from datetime import datetime, timedelta
from config import Config
from Utils.sqlManager import SQLManager
from Utils.war_strategy import get_war_recommendations

class War(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.coc_client = coc.Client()
        self.db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
        self.channel_id = int(os.environ.get('DISCORD_CHANNEL_ID', 0))
        
        # Start the background task
        self.war_reminder.start()

    async def cog_load(self):
        await self.coc_client.login(Config.COC_EMAIL, Config.COC_PASSWORD)

    async def cog_unload(self):
        await self.coc_client.close()

    @tasks.loop(minutes=30)
    async def war_reminder(self):
        """Checks war status and pings people if needed."""
        if not self.channel_id:
            return

        try:
            war = await self.coc_client.get_current_war(Config.CLAN_TAG)
        except coc.PrivateWarLog:
            return
        except Exception as e:
            print(f"Error fetching war: {e}")
            return

        if war.state != 'inWar':
            return

        # Check time remaining
        # war.end_time is a coc.Timestamp object (datetime)
        now = datetime.utcnow()
        # Ensure war.end_time is offset-naive or convert now to offset-aware if needed
        # coc.py usually returns UTC naive or aware. Let's assume UTC.
        
        time_left = war.end_time.time - now
        hours_left = time_left.total_seconds() / 3600

        if hours_left <= 4:
            channel = self.bot.get_channel(self.channel_id)
            if not channel:
                return

            # Find who hasn't attacked
            missing_attacks = []
            for member in war.clan.members:
                if len(member.attacks) < 2:
                    # Get Discord ID
                    player = self.db.get_player(member.tag)
                    if player and player.get('discord_id'):
                        mention = f"<@{player['discord_id']}>"
                    else:
                        mention = member.name
                    
                    attacks_left = 2 - len(member.attacks)
                    missing_attacks.append(f"{mention} ({attacks_left} left)")

            if missing_attacks:
                msg = f"⚠️ **WAR ENDING SOON!** ({int(hours_left)}h {int((hours_left%1)*60)}m left)\n"
                msg += "The following players still need to attack:\n"
                msg += "\n".join(missing_attacks)
                msg += "\n\n**Please get your hits in!**"
                
                await channel.send(msg)

    @war_reminder.before_loop
    async def before_war_reminder(self):
        await self.bot.wait_until_ready()

    @commands.command(name='war')
    async def war_status(self, ctx):
        """Shows current war status."""
        try:
            war = await self.coc_client.get_current_war(Config.CLAN_TAG)
        except:
            await ctx.send("❌ Could not fetch war data.")
            return

        if war.state == 'notInWar':
            await ctx.send("💤 Clan is not in war.")
            return

        embed = discord.Embed(title=f"War vs {war.opponent.name}", color=discord.Color.red())
        embed.add_field(name="State", value=str(war.state).capitalize(), inline=True)
        embed.add_field(name="Score", value=f"{war.clan.stars} ⭐ - {war.opponent.stars} ⭐", inline=True)
        
        if war.end_time:
            embed.add_field(name="End Time", value=f"<t:{int(war.end_time.time.timestamp())}:R>", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name='targets')
    async def war_targets(self, ctx):
        """Get recommended targets from the War Room logic."""
        # This requires fetching data from DB as our logic uses DB objects
        active_war = self.db.get_active_war()
        if not active_war:
            await ctx.send("❌ No active war found in database.")
            return

        # Fetch war from API to get accurate time
        try:
            war_data = await self.coc_client.get_current_war(Config.CLAN_TAG)
            now = datetime.utcnow()
            # coc.py timestamps are usually UTC
            time_left = war_data.end_time.time - now
            hours_left = time_left.total_seconds() / 3600
        except:
            hours_left = 24 # Default if API fails

        our_team, enemy_team = self.db.get_full_war_map(active_war['war_id'])
        
        # Calculate Triple Rate for each player
        for p in our_team:
            triples = p.get('total_triples', 0)
            attacks = p.get('total_attacks', 0)
            p['triple_rate'] = triples / attacks if attacks > 0 else 0.30 # Default to 30% if no data

        war_context = {'hours_left': hours_left, 'score_diff': 0}
        recommendations = get_war_recommendations(our_team, enemy_team, war_context)

        # Filter for the user if they are linked
        discord_id = str(ctx.author.id)
        player = self.db.get_player_by_discord_id(discord_id)
        
        if player:
            # Find their recommendation
            my_rec = next((r for r in recommendations if r['player']['player_tag'] == player['player_tag']), None)
            if my_rec:
                if my_rec['target']:
                    target = my_rec['target']
                    msg = f"🎯 **Your Recommended Target:**\n"
                    msg += f"**#{target['map_position']} {target['town_hall_level']}** (Stars: {target['stars']})\n"
                    msg += f"Strategy: {my_rec['reason']}\n"
                    msg += f"Confidence: {my_rec['confidence']}%"
                    await ctx.send(msg)
                else:
                    await ctx.send(f"ℹ️ Status: {my_rec['reason']}")
            else:
                await ctx.send("❌ You are not in the current war roster.")
        else:
            await ctx.send("❌ You are not linked. Use `!link #TAG` to see your target.")

    @commands.command(name='nudge')
    @commands.has_permissions(mention_everyone=True)
    async def nudge_attackers(self, ctx):
        """Manually pings players who haven't attacked."""
        try:
            war = await self.coc_client.get_current_war(Config.CLAN_TAG)
        except:
            await ctx.send("❌ Could not fetch war data.")
            return

        if war.state != 'inWar':
            await ctx.send("💤 Clan is not in war.")
            return

        missing_attacks = []
        for member in war.clan.members:
            if len(member.attacks) < 2:
                # Get Discord ID
                player = self.db.get_player(member.tag)
                if player and player.get('discord_id'):
                    mention = f"<@{player['discord_id']}>"
                else:
                    mention = member.name
                
                attacks_left = 2 - len(member.attacks)
                missing_attacks.append(f"{mention} ({attacks_left} left)")

        if missing_attacks:
            msg = f"🔔 **WAR REMINDER!**\n"
            msg += "The following players still need to attack:\n"
            msg += "\n".join(missing_attacks)
            msg += "\n\n**Please get your hits in!**"
            await ctx.send(msg)
        else:
            await ctx.send("✅ Everyone has attacked!")



    @nudge_attackers.error
    async def nudge_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You do not have permission to use this command. You need 'Mention Everyone' rights.")
        else:
            await ctx.send(f"❌ An error occurred: {error}")

async def setup(bot):
    await bot.add_cog(War(bot))
