from __future__ import annotations

from os import environ
from logging import basicConfig, getLogger
from asyncio import Queue, sleep
from binascii import unhexlify
from io import BytesIO
from re import compile
import json
from contextlib import suppress

from aiosbb import SBBClient
import disnake
from dotenv import load_dotenv
from disnake.ext import commands
from rich.logging import RichHandler

with suppress(ImportError):
    from uvloop import install

    install()


def main():
    basicConfig(
        level="INFO",
        format="%(message)s",
        datefmt="[X]",
        handlers=[RichHandler()]
    )

    with open("config.json") as file:
        config_data = json.load(file)
    servers = config_data["servers"]
    ip_address = config_data["IP"]

    log = getLogger("rich")
    load_dotenv()

    wait_pattern = compile(r"^W{1}(\d*)$")

    class SbbConnection(SBBClient):
        def __init__(self, ip):
            self.overworldPointer = ["0x43A7848", "0x348", "0x10", "0xD8", "0x28"]
            self.isConnectedPointer = ["0x437E280", "0x30"]
            super().__init__(ip)

        async def send_seq(self, command: str) -> None:
            _, args_str = command.split(" ")
            cmds = args_str.split(",")
            for cmd in cmds:
                if wait_pattern.match(cmd):
                    t = int(wait_pattern.findall(cmd)[0])
                    log.info(f"sleeping for {t}")
                    await sleep(float(t))
                else:
                    await self(f"click {cmd}")

        async def pointer_peek(self, pointer, length) -> str:
            request = f"pointerPeek {str(length)}"
            for jump in pointer:
                request += f" {jump}"
            return await self(request)

        async def pixelpeek(self):
            holder_variable = await self("pixelPeek")
            log.info("code logged")
            return unhexlify(holder_variable)

        async def is_in_overworld(self) -> bool:
            onOverworld = await self.pointer_peek(self.overworldPointer, 1)
            return onOverworld == "11"

        async def is_connected(self) -> bool:
            connected = await self.pointer_peek(self.isConnectedPointer, 1)
            return connected == "01"

        async def quit_game(self) -> None:
            await self.send_seq("clickSeq B,W1,HOME,W1,X,W1,X,W1,A,W1,A,W3")

        async def start_game(self) -> None:
            await self.send_seq("clickSeq A,W1,A,W1,A,W1,A,W1")
            await sleep(16)
            await self.send_seq("clickSwq A,W1,A,W1")

        async def going_online(self) -> None:
            online = False
            loop_counter = 0
            while online is not True:
                loop_counter += 1
                await sleep(1)
                online = await self.is_in_overworld()
                log.info(f"To see if self.is_in_overworld() is not true attempts: {loop_counter}")
            await self.send_seq("clickSeq X,W1,L")

            connected = False
            loop_counter2 = 0
            while connected is not True:
                loop_counter2 += 1
                await sleep(2)
                connected = await self.is_connected()
                log.info(f"To see if self.is_connected() is not true attempts: {loop_counter2}")
            await self.send_seq("clickSeq W2,A,W1,A,W1,B,W1,B,W1")

        async def raid_lobby(self, raid_queue: Queue) -> None:
            await self.send_seq("clickSeq A,W3,A,W3,A,W6")
            file = await self.pixelpeek()
            users = []
            while not raid_queue.empty() and len(users) < 3:
                user = await bot.getch_user(await raid_queue.get())
                users.append(user)
                await user.send(files=[disnake.File(BytesIO(file), "raid.jpg")])
            log.info("code sent")
            await sleep(150)
            await self.send_seq("click A,W3,A")

        async def raid_battle(self) -> None:
            inRaid = True
            loop_counter = 0
            while inRaid:
                loop_counter += 1
                await self.send_seq("clickSeq A,W1,A,W1,A,W1,A,W1,A,W1,A,W1,B,W1,B,W1,B,W1,B,W1,B,W1,B,W1")
                inRaid = not await self.is_in_overworld()
                await sleep(5)
                log.info(f"Times though raid: {loop_counter}")

    class Bot(commands.InteractionBot):
        def __init__(self, *args, **kwargs) -> None:
            self.sbbcon = SbbConnection(ip=ip_address)
            super().__init__(*args, **kwargs)

    bot = Bot(
        intents=disnake.Intents.all(),
        asyncio_debug=True
    )
    bot.load_extensions("cogs")

    @bot.slash_command(guild_ids=servers)
    async def pixelpeek(inter) -> None:
        if inter.author.id != bot.owner_id:
            return None
        image_hold = await bot.sbbcon("pixelPeek")
        await inter.send(file=disnake.File(BytesIO(unhexlify(image_hold)), "peek.jpg"), ephemeral=True)

    bot.run(environ["DISCORD_TOKEN"])


if __name__ == "__main__":
    main()
