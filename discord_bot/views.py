import discord
from discord import ui
from Utils.sqlManager import SQLManager
from config import Config

class LinkModal(ui.Modal, title='Link Clash of Clans Account'):
    tag = ui.TextInput(label='Player Tag', placeholder='#8GGPQLPU', required=True)

    def __init__(self, db):
        super().__init__()
        self.db = db

    async def on_submit(self, interaction: discord.Interaction):
        player_tag = self.tag.value.strip()
        if not player_tag.startswith('#'):
            player_tag = '#' + player_tag
        
        # Check if player exists in DB
        player = self.db.get_player(player_tag)
        
        if player:
            # Link
            self.db.link_discord_user(player_tag, str(interaction.user.id))
            
            # Sync Roles
            # We access the bot via interaction.client
            bot = interaction.client
            cog = bot.get_cog('Management')
            if cog:
                await cog.sync_roles(interaction.guild, interaction.user, player)
            
            await interaction.response.send_message(f"✅ Successfully linked **{player['name']}** to {interaction.user.mention}!", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Player tag `{player_tag}` not found. Please wait for the system to sync or check the tag.", ephemeral=True)

class LinkView(ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Persistent view
        self.db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)

    @ui.button(label="🔗 Link Account", style=discord.ButtonStyle.green, custom_id="link_account_button")
    async def link_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(LinkModal(self.db))
