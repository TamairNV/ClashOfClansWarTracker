import asyncio
import coc
import os
from dotenv import load_dotenv
load_dotenv()

async def main():
    async with coc.Client() as coc_client:
        try:
            await coc_client.login(os.environ.get('EMAIL'),os.environ.get('PASSWORD'))
        except coc.InvalidCredentials as error:
            exit(error)

        player = await coc_client.get_player("#G2JUUUGO")
        print(f"{player.name} has {player.trophies} trophies!")
        print(player.donations)
        print(player.received)

        clans = await coc_client.search_clans(name="Wizardly Minds", limit=1)
        for clan in clans:
            print(f"{clan.name} ({clan.tag}) has {clan.member_count} members")

        clan = await coc_client.get_clan(clans[0].tag)
        async for player in clan.get_detailed_members():
            print(player)

        try:
            war = await coc_client.get_current_war("8GGPQLPU")
            print(f"{war.clan_tag} is currently in {war.state} state.")
        except:
            print("uh oh, they have a private war log!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass