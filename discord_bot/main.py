import discord
from discord.ext import commands
import os
import sys
import asyncio

# Add parent directory to path to import config and Utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from discord_bot.views import LinkView

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True # Required for role management

class MyBot(commands.Bot):
    async def setup_hook(self):
        # Load persistent views
        self.add_view(LinkView())
        print("✅ Persistent Views Loaded")
        
        # Load Cogs
        await self.load_extension('cogs.management')
        await self.load_extension('cogs.war')
        await self.load_extension('cogs.fun')
        print("✅ All Cogs Loaded")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return # Ignore unknown commands
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to do that.")
        else:
            print(f"❌ Command Error: {error}")
            await ctx.send(f"❌ An error occurred: {error}")

bot = MyBot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

async def main():
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("❌ Error: DISCORD_BOT_TOKEN not found in environment variables.")
        return
    
    async with bot:
        await bot.start(token)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        pass
