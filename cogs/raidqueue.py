from asyncio import Queue, create_task
from io import BytesIO
from logging import getLogger

import disnake
from aiohttp import ClientSession
from disnake.ext import commands, components


class RaidQueue(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.raid_queue = Queue()
        self.log = getLogger("rich")
        self.raidtask_running = False
        self.queue_running = False
        self.raid_information = None
        self.types = None
        self.mons = None

    async def fetch_data(self):
        self.log.info("fetching assets infos")
        async with ClientSession() as session:
            async with session.get(
                "https://raw.githubusercontent.com/Z1R343L/raid_assets/main/sprites_list.json"
            ) as response:
                self.mons = disnake.utils._from_json(await response.text())
            async with session.get(
                "https://raw.githubusercontent.com/Z1R343L/raid_assets/main/tera_types.json"
            ) as response:
                self.types = disnake.utils._from_json(await response.text())

    async def autoraid_task(self, inter):
        raid_counter = 0
        # quit game
        await self.bot.sbbcon.quit_game()
        self.log.info("quit game")

        while self.raidtask_running:
            # start game
            await self.bot.sbbcon.start_game()
            self.log.info("started game")

            # going online
            self.log.info("raidtask started")
            if not self.bot.config["offline_mode"]:
                await self.bot.sbbcon.going_online()
                self.log.info("connected to internet")

            await self.bot.sbbcon.send_seq("clickSeq W2,A,W1,A,W1,B,W1,B,W1")
            # raid lobby
            await self.bot.sbbcon.raid_lobby(self.raid_queue)
            # await self.inter.send("Raid starting")
            self.log.info("starting raid")

            # raid battle
            await self.bot.sbbcon.raid_battle()
            self.log.info("raid finished")

            # quit game
            await self.bot.sbbcon.quit_game()
            self.log.info("quit game")

            raid_counter += 1
            self.log.info(f"Raids finished: {raid_counter}")
            if self.raid_queue.empty() and not self.queue_running:
                self.raidtask_running = False

        inter.send(f"raid finished, {raid_counter} raids done")

    @commands.slash_command(
        name="open_queue",
        description="Starts hosting the raid and opens the queue for users to join.",
    )
    async def open_queue(
        self,
        inter: disnake.AppCommandInter,
        pokemon: str,
        tera_type: str,
        raid_level: int = commands.Param(choices=list(range(1, 7))),
    ) -> None:
        if inter.author.id != self.bot.owner_id:
            await inter.send("not allowed")
        await inter.response.send_modal(
            title="Additional raid info",
            custom_id="notes_modal",
            components=[
                disnake.ui.TextInput(
                    label="notes",
                    placeholder="...",
                    custom_id="notes",
                    style=disnake.TextInputStyle.multi_line,
                    min_length=0,
                    max_length=1024,
                ),
            ],
        )
        modal_inter = await self.bot.wait_for(
            "modal_submit",
            check=lambda i: i.custom_id == "notes_modal"
            and i.author.id == inter.author.id,
        )
        await modal_inter.response.send_message("done")
        notes = modal_inter.text_values["notes"]

        emb = disnake.Embed(
            title=self.bot.config["emojis"]["star"] * raid_level,
            description=notes,
            color=disnake.Colour.from_rgb(*self.types[tera_type]),
        )
        emb.set_author(
            name=pokemon.replace("_", " ").replace("female", "").title(),
            icon_url=f"https://raw.githubusercontent.com/Z1R343L/raid_assets/main/tera_types/{tera_type}.png",
        )
        emb.set_thumbnail(
            f"https://github.com/Z1R343L/raid_assets/raw/main/sprites/shiny/{pokemon}.gif"
        )
        self.raid_information = emb
        self.raidtask_running = True
        self.queue_running = True
        create_task(self.autoraid_task(inter))

    @open_queue.autocomplete("pokemon")
    async def autocomp_mon(self, _: disnake.CommandInteraction, string: str):
        self.log.info("autocomp mon")
        if self.mons is None:
            await self.fetch_data()
        return (
            [mon for mon in self.mons if mon.lower().startswith(string.lower())][:25]
            if string
            else []
        )

    @open_queue.autocomplete("tera_type")
    async def autocomp_tera(self, _: disnake.CommandInteraction, string: str):
        self.log.info("autocomp tera")
        string = string.lower()
        if self.types is None:
            await self.fetch_data()
        return [t for t in list(self.types.keys()) if t.lower().startswith(string)]

    @components.button_listener()
    async def join_listener(
        self, inter: disnake.MessageInteraction, *, author: disnake.User
    ):
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
    )
    async def join_queue(self, inter):
        if not self.queue_running:
            await inter.send("queue is closed", ephemeral=True)
            return None
        await inter.send(
            embeds=[self.raid_information],
            components=disnake.ui.Button(
                label="Join",
                custom_id=await self.join_listener.build_custom_id(author=inter.author),
            ),
            ephemeral=True,
        )

    @commands.slash_command(
        name="show_queue",
        description="Shows the users in the queue and where users are.",
    )
    async def show_queue(self, inter) -> None:
        if self.raid_queue.empty():
            await inter.send(content="Queue is empty", ephemeral=True)
            return
        await inter.send(
            content="\n".join(
                [f"<@{str(user)}>" for user in list(self.raid_queue._queue)]
            ),
            ephemeral=True,
        )

    @commands.slash_command(
        name="close_queue",
        description="Hoster stops people from joining the queue, queue can then empty out before the raid is closed.",
    )
    async def close_queue(self, inter) -> None:
        if inter.author.id != self.bot.owner_id:
            return None
        self.queue_running = False
        await inter.send("Raid Queue is now closed!")

    @commands.slash_command(
        name="end_raid",
        description="Hoster end hosting the raid imidiatly after the current raid.",
    )
    async def end_raid(self, inter) -> None:
        if inter.author.id != self.bot.owner_id:
            return None
        self.raidtask_running = False
        await inter.send("Raid hosting will end after the current raid.")


def setup(bot: commands.Bot):
    bot.add_cog(RaidQueue(bot))
