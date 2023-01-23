from __future__ import annotations

from os import environ
from logging import basicConfig, getLogger, DEBUG
from asyncio import StreamReader, StreamWriter, open_connection, sleep
from dataclasses import dataclass
from binascii import unhexlify
from io import BytesIO
from re import compile
import json
from contextlib import suppress

import disnake
from dotenv import load_dotenv
from disnake.ext import commands
from rich.logging import RichHandler

with suppress(ImportError):
    from uvloop import install


install()

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

@dataclass
class SbbConnection:
    ip: str
    connected: bool = False
    reader: StreamReader = None
    writer: StreamWriter = None
    overworldPointer = ["0x43A7848", "0x348", "0x10", "0xD8", "0x28"]
    isConnectedPointer = ["0x437E280", "0x30"]

    async def _connect(self) -> None:
        log.info(f"connecting to {self.ip}")
        self.reader, self.writer = await open_connection(self.ip, port=6000, limit=(1024 * 1024))
        self.connected = True
        await self.send("configure echoCommands 1")
        await self.send("detatchController")

    async def send(self, command: str) -> bytes:
        log.info(f">> {command}")
        command = command + "\r\n"
        if not self.connected:
            await self._connect()
        self.writer.write(command.encode())
        await self.writer.drain()
        res = []
        while True:
            r = await self.reader.readline()
            if r == command.encode():
                log.info("<< echo")
                break
            else:
                res.append(r[:-1].decode())
            await sleep(0)
        if res:
            return res[0]

    async def send_seq(self, command: str) -> None:
        _, args_str = command.split(" ")
        cmds = args_str.split(",")
        for cmd in cmds:
            if wait_pattern.match(cmd):
                t = int(wait_pattern.findall(cmd)[0])
                log.info(f"sleeping for {t}")
                await sleep(float(t))
            else:
                await self.send(f"click {cmd}")

    async def pointerPeek(self, pointer, length) -> str:
        request = f"pointerPeek {str(length)}"
        for jump in pointer:
            request += f" {jump}"
        return await self.send(request)

    async def isOnOverworld(self) -> bool:
        onOverworld = await self.pointerPeek(self.overworldPointer, 1)
        return onOverworld == "11"
    
    async def isConnected(self) -> bool:
        connected = await self.pointerPeek(self.isConnectedPointer, 1)
        return connected =="01"

    async def goingOnline(self) -> None:
        online = False
        while online is not True:
            await sleep(1)
            online = await self.isOnOverworld()
            #log.info(f"pointer -> {online}")
        await self.send_seq("clickSeq X,W1,L")

        connected = False
        while connected is not True:
            await sleep(2)
            connected = await self.isConnected()
        await self.send_seq("clickSeq W2,A,W1,A,W1,B,W1,B,W1")

    async def raid_battle(self) -> None:
        inRaid = True
        while inRaid:
            await self.send_seq("clickSeq A,W1,A,W1,A,W1,A,W1,A,W1,A,W1,B,W1,B,W1,B,W1,B,W1,B,W1,B,W1")
            inRaid = not await self.isOnOverworld()
            await sleep(5)
        return None

    async def quit_game(self) -> None:
        await self.send_seq("clickSeq B,W1,HOME,W1,X,W1,X,W1,A,W1,A,W3")
        return None

    async def start_game(self) -> None:
        await self.send_seq("clickSeq A,W1,A,W1,A,W1,A,W1")
        await sleep(16)
        await self.send_seq("clickSwq A,W1,A,W1")
        return None



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
    image_hold = await bot.sbbcon.send("pixelPeek")
    await inter.send(file=disnake.File(BytesIO(unhexlify(image_hold)), "peek.jpg"))



bot.run(environ["DISCORD_TOKEN"])