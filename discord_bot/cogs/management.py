import discord
from discord.ext import commands, tasks
from Utils.sqlManager import SQLManager
from config import Config
from discord_bot.views import LinkView

import coc

class Management(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
        self.coc_client = coc.Client()
        self.sync_roles_loop.start()

    async def cog_load(self):
        await self.coc_client.login(Config.COC_EMAIL, Config.COC_PASSWORD)

    async def cog_unload(self):
        self.sync_roles_loop.cancel()
        await self.coc_client.close()

    @tasks.loop(hours=1)
    async def sync_roles_loop(self):
        """Periodically syncs roles for all linked players."""
        print("🔄 Starting Hourly Role Sync...")
        players = self.db.get_full_roster_including_leavers()
        
        # Get the guild (Assuming bot is in one main guild for now)
        # In a real multi-guild bot, we'd loop through guilds or store guild_id in config
        # For this user, we can try to find the guild by ID if known, or just iterate bot.guilds
        
        for guild in self.bot.guilds:
            for player in players:
                if player.get('discord_id'):
                    try:
                        member = await guild.fetch_member(int(player['discord_id']))
                        if member:
                            await self.sync_roles(guild, member, player)
                    except discord.NotFound:
                        pass # Member not in server
                    except Exception as e:
                        print(f"Error syncing {player['name']}: {e}")
        print("✅ Hourly Role Sync Complete")

    @sync_roles_loop.before_loop
    async def before_sync_loop(self):
        await self.bot.wait_until_ready()

    @commands.command(name='link')
    async def link_player(self, ctx, player_tag: str):
        """Links your Discord account to a Clash of Clans player tag."""
        if not player_tag.startswith('#'):
            player_tag = '#' + player_tag

        player = self.db.get_player(player_tag)
        if not player:
            await ctx.send(f"❌ Player tag `{player_tag}` not found in our database. Please wait for the system to sync or check the tag.")
            return

        self.db.link_discord_user(player_tag, str(ctx.author.id))
        await ctx.send(f"✅ Successfully linked **{player['name']}** to {ctx.author.mention}!")
        
        # Trigger role sync immediately
        await self.sync_roles(ctx.guild, ctx.author, player)

    @commands.command(name='sync')
    async def manual_sync(self, ctx):
        """Manually syncs roles for the user."""
        discord_id = str(ctx.author.id)
        player = self.db.get_player_by_discord_id(discord_id)
        
        if not player:
            await ctx.send("❌ You are not linked to any player. Use `!link #TAG` first.")
            return

        await self.sync_roles(ctx.guild, ctx.author, player)
        await ctx.send(f"✅ Roles synced for **{player['name']}**.")

    async def sync_roles(self, guild, member, player_data):
        """Syncs Discord roles based on In-Game role."""
        
        # 0. Fetch Fresh Data from API to ensure role is up to date
        try:
            player_tag = player_data['player_tag']
            fresh_player = await self.coc_client.get_player(player_tag)
            
            # Update DB with fresh role
            # We can use a simplified update or reuse update_player_roster if we mock an object
            # But let's just update the role directly for speed/safety
            role_str = str(fresh_player.role)
            self.db.execute("UPDATE players SET role = %s, name = %s, town_hall_level = %s WHERE player_tag = %s", 
                            (role_str, fresh_player.name, fresh_player.town_hall, player_tag))
            
            # Update local player_data dict so we use the new role below
            player_data['role'] = role_str
            print(f"🔄 Refreshed data for {fresh_player.name}: Role is {role_str}")
            
        except Exception as e:
            print(f"⚠️ Could not fetch fresh data for {player_data.get('name')}: {e}")
            # Continue with existing DB data if API fails

        role_map = {
            'member': 'Member',
            'Member': 'Member',
            'admin': 'Elder',
            'Elder': 'Elder',
            'coLeader': 'Co-Leader',
            'Co-Leader': 'Co-Leader',
            'leader': 'Leader',
            'Leader': 'Leader'
        }
        
        in_game_role = player_data.get('role', 'member') # Default to member
        target_role_name = role_map.get(str(in_game_role), 'Member') # Ensure string
        
        # Roles to manage
        managed_roles = ['Member', 'Elder', 'Co-Leader', 'Leader']
        
        # 1. Add the correct role
        target_role = discord.utils.get(guild.roles, name=target_role_name)
        if target_role:
            if target_role not in member.roles:
                try:
                    await member.add_roles(target_role)
                    print(f"Added {target_role.name} to {member.name}")
                except discord.Forbidden:
                    print(f"❌ Missing permissions to add role {target_role.name}")
        else:
            print(f"⚠️ Role '{target_role_name}' not found.")

        # 2. Remove incorrect roles (only from the managed set)
        for role_name in managed_roles:
            if role_name != target_role_name:
                role_to_remove = discord.utils.get(guild.roles, name=role_name)
                if role_to_remove and role_to_remove in member.roles:
                    try:
                        await member.remove_roles(role_to_remove)
                        print(f"Removed {role_to_remove.name} from {member.name}")
                    except discord.Forbidden:
                        print(f"❌ Missing permissions to remove role {role_to_remove.name}")

        # 3. Sync Nickname
        # We want the Discord nickname to match the In-Game Name
        in_game_name = player_data.get('name')
        if in_game_name and member.display_name != in_game_name:
            try:
                await member.edit(nick=in_game_name)
                print(f"✅ Updated nickname for {member.name} to {in_game_name}")
            except discord.Forbidden:
                print(f"❌ Cannot change nickname for {member.name} (Missing Permissions or User is Owner/Higher Role)")
            except Exception as e:
                print(f"⚠️ Error changing nickname for {member.name}: {e}")

    @commands.command(name='setup_server')
    @commands.has_permissions(administrator=True)
    async def setup_server(self, ctx):
        """Creates necessary roles and channels for the clan server."""
        guild = ctx.guild
        
        # 1. Create Roles
        roles_to_create = {
            'Leader': discord.Color.gold(),
            'Co-Leader': discord.Color.red(),
            'Elder': discord.Color.blue(),
            'Member': discord.Color.green()
        }
        
        created_roles = []
        for role_name, color in roles_to_create.items():
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                try:
                    role = await guild.create_role(name=role_name, color=color, hoist=True)
                    created_roles.append(role_name)
                except discord.Forbidden:
                    await ctx.send(f"❌ Missing permissions to create role '{role_name}'.")
                    return

        # 2. Create Channels
        # Categories
        category_name = "Clash War Tracker"
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            try:
                category = await guild.create_category(category_name)
            except discord.Forbidden:
                await ctx.send("❌ Missing permissions to create categories.")
                return

        channels_to_create = {
            'welcome': {'private': False}, # Public welcome
            'general': {'private': False},
            'bot-commands': {'private': False},
            'war-room': {'private': True, 'roles': ['Member', 'Elder', 'Co-Leader', 'Leader']},
            'elders-lounge': {'private': True, 'roles': ['Elder', 'Co-Leader', 'Leader']},
            'leaders-den': {'private': True, 'roles': ['Co-Leader', 'Leader']}
        }
        
        created_channels = []
        for channel_name, options in channels_to_create.items():
            channel = discord.utils.get(guild.text_channels, name=channel_name)
            if not channel:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False if options['private'] else None),
                    guild.me: discord.PermissionOverwrite(read_messages=True)
                }
                
                # Add role permissions
                if 'roles' in options:
                    for r_name in options['roles']:
                        role = discord.utils.get(guild.roles, name=r_name)
                        if role:
                            overwrites[role] = discord.PermissionOverwrite(read_messages=True)

                try:
                    await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
                    created_channels.append(channel_name)
                except discord.Forbidden:
                    await ctx.send(f"❌ Missing permissions to create channel '{channel_name}'.")

        msg = "✅ **Server Setup Complete!**\n"
        if created_roles:
            msg += f"Roles Created: {', '.join(created_roles)}\n"
        else:
            msg += "Roles: All existed.\n"
            
        if created_channels:
            msg += f"Channels Created: {', '.join(created_channels)}\n"
        else:
            msg += "Channels: All existed."
            
        await ctx.send(msg)



    @commands.command(name='welcome')
    @commands.has_permissions(administrator=True)
    async def welcome_message(self, ctx):
        """Sends the 'Start Page' welcome message with Link button."""
        embed = discord.Embed(
            title="🛡️ Welcome to the Clan!",
            description="To get the full experience, please **link your Clash of Clans account**.\n\n"
                        "**Once linked, you will get:**\n"
                        "🎯 **War Room Access**: Personalized attack targets to maximize our stars.\n"
                        "🤖 **Auto-Role Sync**: Your Discord role will match your in-game status.\n"
                        "🔔 **War Reminders**: Never miss an attack again!\n\n"
                        "*Click the button below to get started!*",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed, view=LinkView())

    @commands.command(name='bot_guide')
    @commands.has_permissions(administrator=True)
    async def guide_command(self, ctx):
        """Posts a guide explaining all bot commands."""
        embed = discord.Embed(
            title="🤖 Clan War Tracker Bot Guide",
            description="Here is how to use the bot to dominate in wars!",
            color=discord.Color.blue()
        )
        
        # General Commands
        embed.add_field(
            name="🔗 Account Setup",
            value="**`!welcome`** (Admins): Posts the Link Button.\n"
                  "**`!link #TAG`**: Manually link your Clash account.\n"
                  "**`!sync`**: Updates your Discord role to match in-game.",
            inline=False
        )
        
        # War Commands
        embed.add_field(
            name="⚔️ War Room",
            value="**`!targets`**: 🎯 **Most Important!** Tells you exactly who to attack.\n"
                  "**`!war`**: Shows the current war score and time remaining.\n"
                  "**`!nudge`** (Admins): Pings everyone who hasn't attacked yet.",
            inline=False
        )
        
        # Fun/Stats
        embed.add_field(
            name="📊 Stats & Fun",
            value="**`!roster`**: Shows the Top 10 players by Trust Score.\n"
                  "**`!best`**: Announces the current MVP.\n"
                  "**`!worst`**: Shames the lowest scoring active player.",
            inline=False
        )
        
        embed.set_footer(text="Use these commands in #bot-commands")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Management(bot))
    # We should add the view to the bot for persistence if we want it to work after restart
    # But for now, the command creates it. To make it truly persistent across restarts, 
    # we need to add it in bot.setup_hook in main.py. 
    # For this task, we'll just let the command deploy it.

