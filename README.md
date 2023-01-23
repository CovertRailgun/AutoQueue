# AutoQueue
Pokemon Scarlet/Violet raid auto hosting with a queue discord bot.

To use this code you will first need to set up a discord bot and have the bot token.
You will also need to have Sysbot-Base installed onto your switch.

Install the dependencies in requirements.txt

Get your discord bot token and create a .env file and create a variable called "DISCORD_TOKEN" end then set it equal to your bot token.

![envformating](https://user-images.githubusercontent.com/100811635/214173171-84286135-66f4-45ab-a6cb-1ed0ca0f982a.png)

Open the config.json file and input the Discord server IDs between the [] for the servers you have the bots in, if you have more than one server separate the IDs with a comma. Then get your switches IP address and input it between the "".

![jsonformating](https://user-images.githubusercontent.com/100811635/214173757-ed375de7-f15a-419e-9208-31c90e6470cc.png)

Stand next to the raid crystal in Scarlet/Violet makeing sure that when A is pressed you bring up the raid menu and save the game.
Start the code and use /open_queue to start hosting and letting people join the queue by hitting the join button.
Once you wish to stop hosting the raid /close_queue will prevent people from joining the queue and let the program continue until the queue is empty.


Thanks to the people over at autoraid for inspireing this project.
https://github.com/MicheleBiena/autoraid

Code was written and tested on python3.11.
