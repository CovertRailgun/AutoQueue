from asyncio import Queue, create_task
from logging import getLogger
import json

import disnake
from disnake.ext import commands, components

with open("config.json") as file:
    config_data = json.load(file)
servers = config_data["servers"]

class RaidQueue(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        #self.bot._test_guilds(servers)
        self.raid_queue = Queue()
        self.log = getLogger("rich")
        self.raidtask_running = False
        self.queue_running = False
        self.raid_information = []

    async def autoraid_task(
        self,
        inter
    ):
        raid_counter = 0
        #quit game
        await self.bot.sbbcon.quit_game()
        self.log.info("quit game")

        while self.raidtask_running:
            #start game
            await self.bot.sbbcon.start_game()
            self.log.info("started game")

            #going online
            self.log.info("raidtask started")
            await self.bot.sbbcon.going_online()
            self.log.info("connected to internet")

            #raid lobby
            await self.bot.sbbcon.raid_lobby(self.raid_queue)
            #await self.inter.send("Raid starting")
            self.log.info("starting raid")

            #raid battle
            await self.bot.sbbcon.raid_battle()
            self.log.info("raid finished")

            #quit game
            await self.bot.sbbcon.quit_game()
            self.log.info("quit game")

            raid_counter += 1
            self.log.info(f"Raids finished: {raid_counter}")
            if (self.raid_queue.empty() and not self.queue_running):
                self.raidtask_running = False

        inter.send(f"raid finished, {raid_counter} raids done")
            
    @commands.slash_command(
        name="open_queue",
        description="Starts hosting the raid and opens the queue for users to join.",
        guild_ids=servers
        )
    async def open_queue(
        self, 
        inter,
        raid_level:str,
        pokemon:str,
        tera_type:str,
        notes:str
        ) -> None:

        if inter.author.id != self.bot.owner_id:
            return None
        await inter.send(
            content="Raid hosting has been started!!!"
        )
        self.raid_information = [raid_level, pokemon, tera_type, notes]
        self.raidtask_running = True
        self.queue_running = True
        await create_task(self.autoraid_task(inter))

    @components.button_listener()
    async def join_listener(self, inter: disnake.MessageInteraction, *, author: disnake.User):
        self.log.info(author)
        user = inter.author.id
        if user in list(self.raid_queue._queue):
            await inter.send("You are already in the queue", ephemeral=True)
            return None
        self.raid_queue.put_nowait(user)
        await inter.send("joined queue!\nKeep an eye on DMs!", ephemeral=True)

    @commands.slash_command(
        name="join_queue",
        description="Provieds information on the current raid and gives you the option to join.",
        guild_ids=servers
    )
    async def join_queue(self, inter):
        if self.queue_running == False:
            await inter.response.defer("queue is closed", ephemeral=True)
            return None
        await inter.send(
            content=f"A {self.raid_information[0]} star tera type {self.raid_information[2]} {self.raid_information[1]} is being hosted.\n{self.raid_information[3]}. \nJoin?",
            components=disnake.ui.Button(
                label="Join",
                custom_id=await self.join_listener.build_custom_id(author=inter.author)
            ),
            ephemeral=True
            
        )

    @commands.slash_command(
        name="show_queue",
        description="Shows the users in the queue and where users are.",
        guild_ids=servers
    )
    async def show_queue(self, inter) -> None:
        if self.raid_queue.empty():
            await inter.send(
                content="Queue is empty",
                ephemeral=True
            )
            return
        await inter.send(
            content="\n".join([f"<@{str(user)}>" for user in list(self.raid_queue._queue)]),
            ephemeral=True
        )
    
    @commands.slash_command(
        name="close_queue",
        description="Hoster stops people from joining the queue, queue can then empty out before the raid is closed.",
        guild_ids=servers
        )  
    async def close_queue(self, inter) -> None:
        if inter.author.id != self.bot.owner_id:
            return None
        self.queue_running = False
        await inter.send("Raid Queue is now closed!")

    @commands.slash_command(
        name="end_raid",
        description="Hoster end hosting the raid imidiatly after the current raid.",
        guild_ids=servers
        )
    async def end_raid(self, inter) -> None:
        if inter.author.id != self.bot.owner_id:
            return None
        self.raidtask_running = False
        inter.send("Raid hosting will end after the current raid.")

def setup(bot: commands.Bot):
    bot.add_cog(RaidQueue(bot))