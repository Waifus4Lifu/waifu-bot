# waifu-bot

[![Official Website](https://cdn.discordapp.com/avatars/309569979450130432/67a809d8741d4973b00eef4ec46d155f.png?size=64)](https://waifus4lifu.com)

## Environment Variables

### Discord Config
These are **required** in order for waifu-bot to work.
* `DISCORD_TOKEN`
* `DISCORD_GUILD_ID`

### API Keys
These are currently required until we add some code to disable commands that need them if the env variables aren't set.
* `API_UNSPLASH`
* `API_GOOGLE`

## Volumes
* `/app/data/`
    * Required if you want data to be saved across container executions