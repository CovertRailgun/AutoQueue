from __future__ import annotations

import json
import re
from asyncio import Queue, sleep
from binascii import unhexlify
from contextlib import suppress
from io import BytesIO
from logging import basicConfig, getLogger
from os import environ

import disnake
from aiosbb import SBBClient
from disnake.ext import commands
from dotenv import load_dotenv
from rich.logging import RichHandler

with suppress(ImportError):
    from uvloop import install

    install()


def main():
    with open("config.json") as file:
        config_data = json.load(file)
    basicConfig(
        level=config_data["log_level"],
        format="%(message)s",
        datefmt="[X]",
        handlers=[RichHandler()],
    )
    log = getLogger("rich")
    load_dotenv()

    wait_pattern = re.compile(r"^W(\d*)$")

    class SbbConnection(SBBClient):
        def __init__(self, ip):
            self.overworldPointer = ("0x43A7848", "0x348", "0x10", "0xD8", "0x28")
            self.isConnectedPointer = ("0x437E280", "0x30")
            super().__init__(ip, timeout=10.0, verbose=True)

        async def detach_controller(self) -> None:
            await self("detachController")

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
            starting = True
            while starting:
                starting = not await self.is_in_overworld()
                await sleep(1)

        async def going_online(self) -> None:
            online = False
            loop_counter = 0
            while not online:
                loop_counter += 1
                await sleep(1)
                online = await self.is_in_overworld()
                log.info(
                    f"To see if self.is_in_overworld() is not true attempts: {loop_counter}"
                )
            await self.send_seq("clickSeq X,W1,L")

            connected = False
            loop_counter2 = 0
            while not connected:
                loop_counter2 += 1
                await sleep(2)
                connected = await self.is_connected()
                log.info(
                    f"To see if self.is_connected() is not true attempts: {loop_counter2}"
                )
            await self.send_seq("clickSeq W2,A,W1,A,W1,B,W1,B,W1")

        async def raid_lobby(self, raid_queue: Queue) -> None:
            await self.send_seq("clickSeq A,W3,A,W3,A,W6")
            _file = await self.pixelpeek()
            users = []
            while not raid_queue.empty() and len(users) < 3:
                user = await bot.getch_user(await raid_queue.get())
                users.append(user)
                await user.send(files=[disnake.File(BytesIO(_file), "raid.jpg")])
            log.info("code sent")
            await sleep(150)
            await self.send_seq("click A,W3,A")

        async def raid_battle(self) -> None:
            inRaid = True
            loop_counter = 0
            while inRaid:
                loop_counter += 1
                await self.send_seq(
                    "clickSeq A,W1,A,W1,A,W1,A,W1,A,W1,A,W1,B,W1,B,W1,B,W1,B,W1,B,W1,B,W1"
                )
                inRaid = not await self.is_in_overworld()
                await sleep(5)
                log.info(f"Times though raid: {loop_counter}")
              
        async def error_screenshot(self) -> None:
            _file = await self.pixelpeek()
            await self.bot.owner_id.send(files=[disnake.File(BytesIO(_file), "raid.jpg")])
            await self.bot.owner_id.send("A timeout error has occured")

    class Bot(commands.InteractionBot):
        def __init__(self, *args, **kwargs) -> None:
            self.config = config_data
            self.sbbcon = SbbConnection(ip=config_data["IP"])
            super().__init__(*args, **kwargs)

    bot = Bot(intents=disnake.Intents.all(), asyncio_debug=True)
    bot.load_extensions("cogs")

    @bot.slash_command()
    async def pixelpeek(inter) -> None:
        await inter.response.defer()
        if inter.author.id != bot.owner_id:
            return None
        image_hold = await bot.sbbcon.pixelpeek()
        await inter.send(file=disnake.File(BytesIO(image_hold), "peek.jpg"), ephemeral=True)

    bot.run(environ["DISCORD_TOKEN"])


if __name__ == "__main__":
    main()
