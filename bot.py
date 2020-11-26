import io
import re
import csv
import draw
import shutil
import typing
import asyncio
import aiohttp
import requests
from functions import *
from discord.ext import commands
from fuzzywuzzy import process
from datetime import datetime

intents = discord.Intents.default()
intents.presences = True
intents.members = True
bot = commands.Bot(command_prefix="!", case_insensitive=True,
                   help_command=None, intents=intents)


def get_command_help(command):
    help = f"`{bot.command_prefix}{command.name} "
    for alias in sorted(command.aliases):
        help = help + f"or {bot.command_prefix}{alias} "
    if command.signature != "":
        help = help + f"{command.signature} "
    help = help + f"` - {command.help}"
    return help


def is_super_channel(ctx):
    if ctx.channel.name not in config["channels"]["super_waifu"]:
        raise commands.NoPrivateMessage
    return True


def has_role(member, role_name):
    for role in member.roles:
        if role.name.lower() == role_name.lower():
            return True
    return False


def is_silly_channel(ctx):
    if isinstance(ctx.channel, discord.TextChannel):
        if ctx.channel.name not in config["channels"]["serious"]:
            return True
    raise commands.NoPrivateMessage


def get_guild():
    guild_id = config["discord"]["guild_id"]
    return bot.get_guild(guild_id)


def get_channel(name):
    for channel in get_guild().channels:
        if channel.name == name:
            return channel
    return None


def get_category(name):
    for category in get_guild().categories:
        if category.name.lower() == name.lower():
            return category
    return None


def get_channel_by_topic(topic):
    for channel in get_guild().text_channels:
        if channel.topic == topic:
            return channel
    return None


def get_role(name):
    for role in get_guild().roles:
        if role.name.lower() == name.lower():
            return role
    return None


def get_joinable_roles():
    joinable = []
    role_colors = [discord.Color.orange(), discord.Color.blue(),
                   discord.Color.from_rgb(54, 57, 63)]
    for role in get_guild().roles:
        if role.name not in config['roles']['forbidden'] and role.color in role_colors:
            joinable.append(role)
    return joinable


def get_members_by_role(name):
    return get_role(name).members


async def detect_reposts(message):
    if message.channel.name in config['channels']['ignore_reposts']:
        return
    guild = get_guild()
    title = "**REPOST DETECTED :recycle:**"
    author = message.author
    description = f"Reposter: {author.mention}"
    embed = discord.Embed(
        title=title, description=description, color=waifu_pink)
    if len(message.content.split(" ")) > 3:
        value = ""
        file = io.BytesIO(message.content.encode("utf-8"))
        bytes_hash = sha_256(file)
        channel_category = message.channel.category.name
        previous_hashes = get_hashes(bytes_hash, channel_category)
        count = len(previous_hashes)
        if count > 0:
            date_time = date_time_from_str(previous_hashes[0][2])
            delta = format_delta(time_since(date_time))
            channel = get_channel(previous_hashes[0][5])
            author = guild.get_member(previous_hashes[0][3])
            name = "Message"
            value = value + f"\"{message.content}\"\n"
            if count == 1:
                value = value + f"Previously posted: {count} time\n"
            else:
                value = value + f"Previously posted: {count} times\n"
            value = value + f"Last posted: {delta} ago\n"
            value = value + f"In: {channel.mention}\n"
            value = value + f"By: {author.mention}\n"
            embed.add_field(name=name, value=value, inline=False)
        store_hash(bytes_hash, message)
    for attachment in message.attachments:
        value = ""
        file = io.BytesIO()
        await attachment.save(file)
        bytes_hash = sha_256(file)
        channel_category = message.channel.category.name
        previous_hashes = get_hashes(bytes_hash, channel_category)
        count = len(previous_hashes)
        if count > 0:
            date_time = date_time_from_str(previous_hashes[0][2])
            delta = format_delta(time_since(date_time))
            channel = get_channel(previous_hashes[0][5])
            author = guild.get_member(previous_hashes[0][3])
            name = "Attachment"
            value = value + f"Filename: {attachment.filename}\n"
            if count == 1:
                value = value + f"Previously posted: {count} time\n"
            else:
                value = value + f"Previously posted: {count} times\n"
            value = value + f"Last posted: {delta} ago\n"
            value = value + f"In: {channel.mention}\n"
            value = value + f"By: {author.mention}\n"
            embed.add_field(name=name, value=value, inline=False)
        store_hash(bytes_hash, message)
    if len(embed.fields) > 0:
        await message.channel.send(embed=embed)
    return


async def rate_limiter(message):
    if message.channel.name not in config['channels']['rate_limited']:
        return
    if len(message.attachments) == 0:
        return
    attachments = []
    for attachment in message.attachments:
        attachments.append(attachment)
    history = await message.channel.history(limit=25).flatten()
    for previous_message in history:
        if previous_message.author == message.author:
            if len(previous_message.attachments) != 0:
                if seconds_since(previous_message.created_at) < 120:
                    for attachment in previous_message.attachments:
                        attachments.append(attachment)
    if len(attachments) > 5:
        title = "**DUMP DETECTED :poo:**"
        author = message.author
        description = f"Dumper: {author.mention}\n\n"
        description = description + \
            "You're not breaking the rules, but you are being a scumbag."
        embed = discord.Embed(
            title=title, description=description, color=waifu_pink)
        await message.channel.send(embed=embed)
    return


async def yes_no_timeout(ctx, message):
    await ctx.send(message)

    def check(answer):
        return answer.author == ctx.author and answer.channel == ctx.channel

    try:
        answer = await bot.wait_for("message", timeout=15, check=check)
        if answer.content.lower() in config["answers"][True]:
            reply = random.choice(strings["user_reply_yes"])
            await ctx.send(reply)
            return True
        reply = random.choice(strings["user_reply_no"])
        await ctx.send(reply)
        return False
    except asyncio.TimeoutError:
        reply = random.choice(strings["user_reply_timeout"])
        await ctx.send(reply)
        return None


async def reply_noob(message):
    global block_noobs
    if message.content.startswith("!"):
        image_path = os.path.join(sys.path[0], "images", "power.gif")
        file = discord.File(image_path)
        reply = f"You don't have access to commands yet, noob."
        await message.channel.send(reply, file=file)
        file.close()
        return
    answer = re.sub("[^0-9a-zA-Z]+", "", message.clean_content).lower()
    if answer == "dontbeadick":
        reply = "Yup. Thanks! I'll grant you access. Just a sec..."
        await message.channel.send(reply)
        await asyncio.sleep(1)
        block_noobs = True
        await message.author.remove_roles(get_role("noob"))
        await asyncio.sleep(1)
        await message.channel.delete()
        await asyncio.sleep(1)
        block_noobs = False
        general_chat = get_channel("general_chat")
        if message.author not in general_chat.members:
            for channel in get_guild().text_channels:
                if "quarantine" in channel.name and message.author in channel.members:
                    reply = f"Hey everyone, {message.author.mention} just joined. {message.author.mention}, please " \
                            f"introduce yourself. Thanks! "
                    await channel.send(reply)
                    reply = f"Hey everyone, {message.author.mention} just joined in {channel.mention}!"
                    await general_chat.send(reply)
                    return
        reply = f"Hey everyone, {message.author.mention} just joined. {message.author.mention}, please introduce " \
                f"yourself. Thanks! "
        await general_chat.send(reply)
        return
    else:
        reply = "Not quite. Try again."
        await message.channel.send(reply)
        return


async def always_sunny(message):
    text = message.clean_content.replace("*", "")
    text = text.replace("_", "")
    text = ascii_only("\"" + text + "\"")
    pending = await message.channel.send("Drawing some dumb shit...")
    image = draw.sunny(text)
    await pending.edit(content="Drawing is done. Sending now...")
    file = discord.File(image)
    await message.channel.send(file=file)
    image.close()
    file.close()
    await pending.delete()
    return


async def change_status():
    statuses = config["statuses"]
    while True:
        status = random.choice(statuses)
        status_code = status[:1]
        status_name = status[1:]
        if status_code == "0":
            status_code = discord.Status.online
        elif status_code == "1":
            status_code = discord.Status.idle
        else:
            status_code = discord.Status.dnd
        game = discord.Game(status_name)
        await bot.change_presence(status=status_code, activity=game)
        await asyncio.sleep(random.randint(300, 600))


async def monitor_noobs():
    global block_noobs
    guild = get_guild()
    noob_role = get_role("noob")
    super_waifu_chat = get_channel("super_waifu_chat")
    while True:
        for member in get_members_by_role("noob"):
            if get_channel_by_topic(str(member.id)) is None:
                if block_noobs:
                    await asyncio.sleep(5)
                else:
                    await member.remove_roles(noob_role)
                    reply = f"No welcome_noob channel found for {member.mention}. Removing noob role."
                    await super_waifu_chat.send(reply)
        for channel in guild.text_channels:
            if channel.name == "welcome_noob":
                id = int(channel.topic)
                member = guild.get_member(id)
                noobs = get_members_by_role("noob")
                if member is None or member not in noobs:
                    if block_noobs:
                        await asyncio.sleep(5)
                    else:
                        await channel.delete()
                        reply = f"<@{id}> no longer has the noob role. Removing welcome_noob channel."
                        await super_waifu_chat.send(reply)
        await asyncio.sleep(1)


async def monitor_deletions():
    guild = get_guild()
    waifu_audit_log = {}
    action = discord.AuditLogAction.message_delete
    async for entry in guild.audit_logs(action=action, limit=25):
        if entry.id not in waifu_audit_log:
            if seconds_since(entry.created_at) < 3600:
                waifu_audit_log[entry.id] = entry
    while True:
        message = await bot.wait_for("message_delete")
        deleted_by = message.author
        author = message.author
        async for entry in guild.audit_logs(action=action, limit=5):
            if entry.extra.channel == message.channel:
                if entry.id not in waifu_audit_log:
                    if seconds_since(entry.created_at) < 60:
                        waifu_audit_log[entry.id] = entry
                        deleted_by = entry.user
                elif waifu_audit_log[entry.id].extra.count != entry.extra.count:
                    waifu_audit_log[entry.id] = entry
                    deleted_by = entry.user
                else:
                    if seconds_since(waifu_audit_log[entry.id].created_at) > 86400:
                        del waifu_audit_log[entry.id]
        if author == bot.user and deleted_by == bot.user:
            continue
        if "deleted" in message.channel.name:
            super_waifu_chat = get_channel("super_waifu_chat")
            reply = f"Hey {deleted_by.mention}, it's best if you don't delete messages from {message.channel.mention}." \
                    f" Unless of course they're really bad. "
            await super_waifu_chat.send(reply)
            continue
        timestamp = message.created_at.strftime("%m/%d/%Y %H:%M")
        title = f"ID: {message.id}"
        description = f"Author: {author.mention}\n" \
                      f"Deleted by: {deleted_by.mention}*\n" \
                      f"Channel: {message.channel.mention}\n" \
                      f"UTC: {timestamp}"
        embed = discord.Embed(
            title=title, description=description, color=discord.Color.red())
        deleted_embeds = message.embeds
        if len(message.content) > 0:
            value = f"\"{message.content}\""
            embed.add_field(name="Message", value=value, inline=False)
        if len(message.attachments) > 0:
            name = "Attachments"
            value = ""
            for attachment in message.attachments:
                value = value + "<{}>\n".format(attachment.proxy_url)
            embed.add_field(name=name, value=value, inline=False)
        if len(message.embeds) > 0:
            name = "Embeds"
            value = f"{len(message.embeds)} found. See below:"
            embed.add_field(name=name, value=value, inline=False)
        if message.channel.name in config["channels"]["female_only"]:
            channel = get_channel("deleted_thots")
        else:
            channel = get_channel("deleted_text")
        await channel.send(embed=embed)
        for index, embed in enumerate(deleted_embeds):
            embed.color = waifu_pink
            reply = f"**Embed {index + 1} of {len(deleted_embeds)}**"
            await channel.send(reply, embed=embed)


async def monitor_joins():
    global block_noobs
    guild = get_guild()
    super_waifu_chat = get_channel("super_waifu_chat")
    title = f"**NOOB DETECTED :airplane_arriving:**"
    previous_invites = await guild.invites()
    while True:
        try:
            member = await bot.wait_for("member_join", timeout=3)
        except asyncio.TimeoutError:
            previous_invites = await guild.invites()
            continue
        super_waifu_role = get_role("super_waifu")
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True),
            super_waifu_role: discord.PermissionOverwrite(read_messages=True),
            member: discord.PermissionOverwrite(read_messages=True)
        }
        block_noobs = True
        noob_channel = await guild.create_text_channel("welcome_noob", topic=str(member.id), overwrites=overwrites)
        await asyncio.sleep(1)
        await member.add_roles(get_role("noob"))
        block_noobs = False
        description = f"Noob: {member.mention}\n"
        embed = discord.Embed(
            title=title, description=description, color=waifu_pink)
        invite_found = None
        invites = await guild.invites()
        for invite in invites:
            for previous_invite in previous_invites:
                if invite.id == previous_invite.id:
                    if invite.uses != previous_invite.uses:
                        invite_found = invite
        previous_invites = invites
        if invite_found is not None:
            invite_details = get_invite_details(invite_found)
            url = invite_found.url
            invite_channel = invite_found.channel
            if invite_found.max_uses == 2 and invite_found.uses == 1 and invite_details is not None:
                event_name = None
                invited_by = guild.get_member(int(invite_details[3])).mention
                reason = invite_details[7]
                await invite_found.delete()
                update_invite_details(invite_found, member)
            elif invite_found.max_uses == 100 and invite_details is not None:
                invited_by = guild.get_member(int(invite_details[3])).mention
                reason = invite_details[7]
                event_name = invite_details[8].replace("_chat", "")
                event_role = get_role(event_name)
                await member.add_roles(event_role)
                await member.add_roles(get_role("quarantine"))
            else:
                event_name = "UNOFFICIAL"
                invited_by = invite_found.inviter.mention
                reason = f"Fuck if I know. Ask {invited_by}."
            value = f"Event: {event_name}\n" \
                    f"Created by: {invited_by}\n" \
                    f"Channel: {invite_channel.mention}\n" \
                    f"Reason: {reason}\nURL: {url}\n"
        else:
            value = "ERROR: NO MATCHING INVITE FOUND"
        embed.add_field(name="Invite", value=value, inline=False)
        await super_waifu_chat.send(embed=embed)
        reply = f"Hey {member.mention}, welcome to Waifus_4_Lifu! I'm WaifuBot, I manage various things here." \
                f" Here is a basic outline of our rules: "
        await noob_channel.send(reply)
        reply = "1. Don't be a dick. We all like to have fun and mess around but let's try and keep it playful! On " \
                "that note, please try and keep negativity to a minimum. All it does is bring everyone else down and " \
                "we don't want that! This is intended to be a fun environment.\n\n " \
                "2. Introduce yourself before you start posting! Everybody is welcome, we just want to know " \
                "who you are and what you are into!\n\n " \
                "3. If you want to post something NSFW (or just shitpost memes) then we have a channel for " \
                "that! Just remember if its illegal we don't want to see it and you will be immediately " \
                "banned without question. The shitposting channel has it's own special rules, please read " \
                "them if you decide to join it. To gain access to the channel, join the shithead role in " \
                "#role_call.\n\n " \
                "4. Speaking of, we have a bot! If you want a list of commands just type `!wtf` or `!help` " \
                "and WaifuBot will explain!\n\n " \
                "5. If you have a problem of some sort, tag a Super Waifu. They are here to help!\n\n" \
                "6. We have voice channels for specific games and for general conversation! Please try and " \
                "use the appropriate channel based on what you are playing or doing.\n\n " \
                "7. We don't have rules for all types of behaviors and actions. That being said, if a Super " \
                "Waifu or Admin contacts you regarding something you have said or done, please be willing to " \
                "comply. We try our hardest to make sure everybody here is having a good time. On that same " \
                "note, if you have some sort of issue or concern with something that has been said or done " \
                "then please bring it to a Super Waifu or Admin's attention. Your concern will be reviewed " \
                "and addressed appropriately.\n\n " \
                "8. Have fun! That is why we made this server!\n\n**Before we continue, what's rule #1?**"
        await noob_channel.send(reply)


async def update_countdowns():
    guild = get_guild()
    while True:
        for channel in guild.text_channels:
            topic = channel.topic
            if topic is not None:
                if topic.startswith("countdown to "):
                    timestamp = topic.replace("countdown to ", "")
                    try:
                        date_time = date_time_from_str(timestamp)
                    except:
                        topic = f"INVALID FORMAT: '{channel.topic}' try: 'countdown to YYYYMMDDHHMMSS'"
                        await channel.edit(topic=topic)
                        await channel.edit(name="countdown_error")
                        continue
                    delta = time_until(date_time)
                    if delta.total_seconds() < 50:
                        await channel.delete()
                        continue
                    formatted_delta = format_countdown(delta)
                    if channel.name != formatted_delta:
                        try:
                            await channel.edit(name=formatted_delta)
                        except:
                            pass
        await asyncio.sleep(1)


async def update_game_channels():
    """Loop through dynamic voice channels and set name to majority game played in channel"""
    guild = get_guild()
    while True:
        for channel in guild.voice_channels:
            # Check if channel starts with W1-W9 or G1-G9
            if re.match(r"^[WG]\d", channel.name):
                base_channel_name = channel.name[:2]
                games = {}
                for member in channel.members:
                    for activity in member.activities:
                        if isinstance(activity, discord.Game):
                            # Increment value for game name key initializing it if it did not already exist
                            games[activity.name] = games.get(
                                activity.name, 0) + 1
                if games:
                    # Select most common game being played by those in channel
                    game = max(games, key=games.get)
                    new_channel_name = f"{base_channel_name}: {game}"
                else:
                    new_channel_name = base_channel_name
                if channel.name != new_channel_name:
                    await channel.edit(name=new_channel_name)
        await asyncio.sleep(1)


@bot.event
async def on_ready():
    log.info(f"Logged on as {bot.user}")
    loop = asyncio.get_event_loop()
    change_status_task = loop.create_task(change_status())
    monitor_noobs_task = loop.create_task(monitor_noobs())
    monitor_deletions_task = loop.create_task(monitor_deletions())
    monitor_joins_task = loop.create_task(monitor_joins())
    update_countdowns_task = loop.create_task(update_countdowns())
    update_game_channels_task = loop.create_task(update_game_channels())


among_us_colors = [
    "black",
    "brown",
    "orange",
    "green",
    "yellow",
    "red",
    "teal",
    "lime",
    "blue",
    "pink",
    "purple",
    "white"]

among_us_games = {}


class AmongUsGame:
    def __init__(self, channel):
        self.channel = channel
        self.players = {}

    def __str__(self):
        return self.channel.name

    def get_available_colors(self):
        available_colors = among_us_colors.copy()
        for player, color in self.players.items():
            available_colors.remove(color)
        return available_colors


@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user:
        return

    if before.channel == after.channel:
        return

    if before.channel is not None and after.channel is not None:
        if "among us" in before.channel.name.lower():
            if "among the dead" in after.channel.name.lower():
                return
        if "among the dead" in before.channel.name.lower():
            if "among us" in after.channel.name.lower():
                return

    if before.channel is not None:
        if "among us" in before.channel.name.lower():
            game = among_us_games.get(before.channel, None)
            if game is not None:
                game.players.pop(member, None)
                nickname = member.display_name.split(":")[0]
                try:
                    await member.edit(nick=nickname, reason="among_us")
                except discord.errors.Forbidden:
                    pass
                log.info(f"{member.display_name} left {game}")
                if len(game.players) == 0:
                    game_name = str(game)
                    among_us_games.pop(game, None)
                    log.info(f"{game_name} has been deleted.")

    if after.channel is not None:
        if "among us" in after.channel.name.lower():
            game = among_us_games.get(after.channel, None)
            if game is None:
                game = AmongUsGame(after.channel)
                among_us_games[after.channel] = game
                log.info(f"{str(game)} has been created.")
            if member not in game.players:
                color = random.choice(game.get_available_colors())
                game.players[member] = color
                nickname = f"{member.display_name[0:24]}: {color}"
                msg = f"{member.display_name} joined {game} as {color}"
                try:
                    await member.edit(nick=nickname, reason="among_us")
                except discord.errors.Forbidden:
                    await member.send(msg)
                log.info(msg)


@bot.event
async def on_command_error(ctx, error):
    error_text = str(error)
    if isinstance(error, commands.UserInputError):
        if error_text != "":
            if error_text[-1] != ".":
                error_text = error_text + "."
        error_text = sentence_case(error_text)
        error_text = error_text + "\n" + get_command_help(ctx.command)
        reply = f"{ctx.author.mention}, you sure are creative when it comes to syntax.\n{error_text}"
        await ctx.send(reply)
    elif isinstance(error, commands.MissingRole):
        image_path = os.path.join(sys.path[0], "images", "dennis.gif")
        file = discord.File(image_path)
        reply = f"{ctx.author.mention}, just who do you think you are?"
        await ctx.send(reply, file=file)
        file.close()
    elif isinstance(error, commands.NoPrivateMessage):
        image_path = os.path.join(sys.path[0], "images", "power.gif")
        file = discord.File(image_path)
        reply = f"Say, uh {ctx.author.mention}, let's find a better channel for this."
        await ctx.send(reply, file=file)
        file.close()
    elif isinstance(error, commands.errors.CommandNotFound):
        reply = f"{ctx.author.mention}, that's not a valid command. Maybe try `!wtf`."
        await ctx.send(reply)
    elif isinstance(error, commands.errors.CommandInvokeError):
        raise error.original
    log_msg = f"[{ctx.author}] - [{ctx.channel}]\n[{error.__class__}]\n{ctx.message.content}"
    log.error(log_msg)
    return


@bot.event
async def on_raw_reaction_add(payload):
    guild = get_guild()
    user_id = payload.user_id
    member = guild.get_member(user_id)
    if member == bot.user:
        return
    role_call = get_channel('role_call')
    channel_id = payload.channel_id
    message_id = payload.message_id
    emoji = payload.emoji.name
    if role_call.id == channel_id:
        messages = await role_call.history(limit=300).flatten()
        for message in messages:
            if message.id == message_id:
                for reaction in message.reactions:
                    users = await reaction.users().flatten()
                    for user in users:
                        if user != bot.user:
                            await reaction.remove(user)
                role_name = message.content.split(' - ')[0]
                if role_name not in config["roles"]["forbidden"]:
                    role = get_role(role_name)
                    if emoji == '👍':
                        if role not in member.roles:
                            await member.add_roles(role)
                            msg = f'You have been added to {role_name}'
                            await member.send(msg)
                        else:
                            msg = f'You are already a member of {role_name}'
                            await member.send(msg)
                    elif emoji == '👎':
                        if role in member.roles:
                            await member.remove_roles(role)
                            msg = f'You have been removed from {role_name}'
                            await member.send(msg)
                        else:
                            msg = f'You are not a member of {role_name}'
                            await member.send(msg)
    return


@bot.event
async def on_message(message):
    if message.author.name == "among_us":
        message_parts = message.content.split("|")
        if len(message_parts) != 4:
            log.error(f"Invalid webhook command: {message.content}")
            return
        user_key, user_id, user_name, command = message_parts
        try:
            user_id = int(user_id)
        except ValueError:
            log.error(f"Invalid user ID: {user_id}")
            return
        key = get_key(user_id, "among_us", True)
        if len(key) < 1:
            log.error(
                f"Invalid key: {user_key} for user: {user_id} - {user_name}")
            return
        if not (user_id == key[0][1] and user_key == key[0][3]):
            log.error(
                f"Invalid key: {user_key} for user: {user_id} - {user_name}")
            return
        guild = get_guild()
        host = guild.get_member(user_id)
        if host is None:
            log.error(f"Game host not found in guild: {user_id} - {user_name}")
            return
        voice_state = host.voice
        if voice_state is None:
            log.error(
                f"Game host not in any voice channels: {user_id} - {user_name}")
            return
        channel = voice_state.channel
        if channel.name.lower() == "among the dead":
            channel = None
            for game_channel, game in among_us_games.items():
                for player, color in game.players.items():
                    if host == player:
                        channel = game_channel
                        break
            if channel is None:
                log.error(
                    f"Game host not in any games: {user_id} - {user_name}")
                return
        elif "among us" not in channel.name.lower():
            msg = f"Game host: {user_id} - {user_name} is in the wrong channel: {channel.name}"
            log.error(msg)
            return
        if command == "mute":
            for player in channel.members:
                await player.edit(mute=True, reason="among_us")
                log.info(f"Muted {player.display_name}")
        elif command == "unmute":
            for player in channel.members:
                await player.edit(mute=False, reason="among_us")
                log.info(f"Un-muted {player.display_name}")
        elif command.startswith("kill"):
            dead = command.split(":")[1]
            dead = dead.replace("'", "").replace("[", "").replace("]", "")
            dead = dead.split(", ")
            game = among_us_games.get(channel, None)
            if game is None:
                log.error(f"Game {game} not found.")
                return
            for player, color in game.players.items():
                if color in dead:
                    await player.edit(voice_channel=get_channel("Among The Dead"), mute=False)
        elif command.startswith("revive"):
            game = among_us_games.get(channel, None)
            if game is None:
                log.error(f"Game {game} not found.")
                return
            for player, color in game.players.items():
                if player.voice is not None:
                    if player.voice.channel != channel:
                        await player.edit(voice_channel=channel, mute=False)
        return

    if message.author == bot.user:
        return
    lower = message.clean_content.lower()
    if isinstance(message.channel, discord.TextChannel):
        if message.channel.name == "welcome_noob" and message.channel.topic == str(message.author.id):
            await reply_noob(message)
            return
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return
    if "thank" in lower and "waifubot" in lower:
        reply = random.choice(strings["no_problem"])
        await message.channel.send(reply)
    if "fuck" in lower and "waifubot" in lower:
        reply = "Fuck me yourself, coward."
        await message.channel.send(reply)
    if "hungry" in message.content.lower().replace(" ", ""):
        if chance(config['chance']['hungry']):
            reply = "No, <@221162619497611274> is hungry."
            file = discord.File(os.path.join(
                sys.path[0], 'images', 'dennis.gif'))
            await message.channel.send(reply, file=file)
            file.close()
    if lower.startswith("*the gang") or lower.startswith("_the gang"):
        await always_sunny(message)
    if isinstance(message.channel, discord.TextChannel):
        await detect_reposts(message)
        await rate_limiter(message)
    return


@bot.command(aliases=["help"])
@commands.guild_only()
async def wtf(ctx):
    """Display this help message."""
    reply = "I understand the following commands:\n\n"
    for command in sorted(bot.commands, key=lambda x: x.name):
        if not command.hidden:
            reply = reply + get_command_help(command) + "\n"
    reply = reply + "\nIf I'm not working correctly, go fuck yourself, you aren't my boss."
    await ctx.send(reply)


@bot.command(aliases=["players"])
@commands.guild_only()
async def members(ctx, *, role):
    """Show a list of members who have signed up for a role/game."""
    role_colors = [discord.Color.orange(), discord.Color.blue(),
                   discord.Color.from_rgb(54, 57, 63)]
    role = get_role(role)
    if role is None:
        reply = f"{ctx.author.mention}, that is not a valid role/game."
        await ctx.send(reply)
        return
    if role.name in config['roles']['forbidden'] or role.color not in role_colors:
        reply = f"{ctx.author.mention}, this is a Forbidden Role:tm:. If you can't figure this out a different way, " \
                f"you don't deserve to know. "
        await ctx.send(reply)
        return
    if role.color in [discord.Color.orange(), discord.Color.from_rgb(54, 57, 63)]:
        member_type = "members"
    else:
        member_type = "players"
    title = f"**{member_type.upper()} OF {role.name.upper()}**"
    description = ""
    for member in role.members:
        description = description + f"{member.mention}\n"
    if description == "":
        description = f"No {member_type.lower()} found."
    color = role.color
    pages = paginate(description)
    for index, page in enumerate(pages):
        if index == 0:
            embed = discord.Embed(title=title, description=page, color=color)
        else:
            embed.add_field(name="Continued", value=page, inline=False)
    await ctx.send(embed=embed)
    return


@bot.command()
@commands.check(is_silly_channel)
@commands.guild_only()
async def magic8ball(ctx, question: str):
    """Ask the magic 8 ball a question."""
    answer = random.choice(strings['eight_ball'])
    reply = f"{ctx.author.mention}, the magic 8 ball has spoken: \"{answer}\"."
    await ctx.send(reply)
    return


@bot.command(name="color")
@commands.guild_only()
async def _color(ctx):
    """Get the hex and RGB values for Waifu Pink:tm:."""
    if get_role("colorblind_fucks") in ctx.author.roles:
        reply = f"{ctx.author.mention}, you're not authorized to see in color."
        await ctx.send(reply)
        return
    reply = f"{ctx.author.mention}, Waifu Pink:tm: is hex: `#ff3fb4`, RGB: `(255, 63, 180)`."
    await ctx.send(reply)
    return


@bot.command(name="random")
@commands.guild_only()
async def _random(ctx):
    """Request a random number, chosen by fair dice roll."""
    await ctx.send(f"{ctx.author.mention}: 4")

    def check(answer):
        if answer.channel == ctx.channel:
            if answer.author == bot.user:
                return False
            is_not = ["n't", "not", "no", "crypto"]
            for word in is_not:
                if (word in answer.content.lower() and "random" in answer.content.lower()) \
                        or answer.content.lower().startswith("!random"):
                    return True
        return False

    try:
        answer = await bot.wait_for("message", timeout=300, check=check)
        if answer.content.lower().startswith("!random"):
            return
        reply = f"{answer.author.mention}, I disagree:\nhttps://xkcd.com/221/"
        await ctx.send(reply)
        return
    except asyncio.TimeoutError:
        return


@bot.command()
@commands.guild_only()
async def rand(ctx, start, end):
    """Request a random number between two numbers, inclusive"""
    number = random.randint(int(start), int(end))
    await ctx.send(f"{ctx.author.mention}: {number}")

# TODO: Fix plural replacements to use proper regex


@bot.command()
@commands.check(is_silly_channel)
@commands.guild_only()
async def catfact(ctx):
    """Kinda self-explanatory."""
    async with aiohttp.ClientSession() as session:
        async with session.get('https://catfact.ninja/fact') as resp:
            if resp.status != 200:
                reply = f"Error {resp.status}: I cannot read the sacred texts."
                await ctx.send(reply)
                return
            fact = (await resp.json())['fact']
            if chance(config['chance']['catfact']):
                guild = get_guild()
                name = random.choice(guild.members).display_name
                fact = replace_ignore_case(fact, " cat ", " " + name + " ")
                fact = replace_ignore_case(fact, " cats ", " " + name + "s ")
                fact = replace_ignore_case(fact, " cat's ", " " + name + "'s ")
                namess = name.lower() + "s"
                if namess[-2:] == "ss":
                    fact = replace_ignore_case(fact, namess, name)
                fact = fact.replace("s's", "s'")
            await ctx.send(fact)
    return


@bot.command()
@commands.check(is_silly_channel)
@commands.guild_only()
async def sponge(ctx, target: typing.Optional[typing.Union[discord.Member, discord.Message, str]]):
    """Mock a fellow member even though you're not clever."""
    messages = []
    async for message in ctx.channel.history(limit=20):
        messages.append(message)
    messages.pop(0)
    if target == None:
        for message in messages:
            if len(message.content) != 0:
                target = message
                break
    elif isinstance(target, discord.Member):
        for message in messages:
            if (message.author == target) and len(message.content) != 0:
                target = message
                break
    if not isinstance(target, discord.Message):
        reply = f"{ctx.author.mention}, I don't see any matching messages in this channel."
        await ctx.send(reply)
        return
    pending = await ctx.send("Drawing some dumb shit...")
    image = draw.spongebob(ctx, target)
    await pending.edit(content="Drawing is done. Sending now...")
    file = discord.File(image)
    await ctx.send(file=file)
    image.close()
    file.close()
    await pending.delete()
    return


@bot.command()
@commands.check(is_silly_channel)
@commands.guild_only()
async def quoth(ctx, target: typing.Optional[typing.Union[discord.Member, discord.Message, str]]):
    """Save message to inspirational quotes database."""
    messages = []
    async for message in ctx.channel.history(limit=20):
        messages.append(message)
    messages.pop(0)
    if target == None:
        for message in messages:
            if len(message.content) != 0:
                target = message
                break
    elif isinstance(target, discord.Member):
        for message in messages:
            if (message.author == target) and len(message.content) != 0:
                target = message
                break
    if not isinstance(target, discord.Message):
        reply = f"{ctx.author.mention}, I don't see any matching messages in this channel."
        await ctx.send(reply)
        return
    if target.author == ctx.author:
        reply = f"Nice try {ctx.author.mention}, you cannot quote yourself. Just how conceited are you?"
        await ctx.send(reply)
        return
    nevermore = get_role('nevermore')
    if nevermore in target.author.roles:
        image_path = os.path.join(sys.path[0], "images", "raven.gif")
        file = discord.File(image_path)
        reply = f"{ctx.author.mention}, try tapping on someone else's chamber door."
        await ctx.send(reply, file=file)
        return
    if len(target.content) == 0:
        reply = f"{ctx.author.mention}, that quote is too short."
        await ctx.send(reply)
        return
    if quote_exists(target.id):
        reply = f"Can't do that, {ctx.author.mention}. That would be a duplicate quote."
        await ctx.send(reply)
        return
    if ctx.channel.name in config["channels"]["sensitive"]:
        reply = f"Hey uh, {ctx.author.mention}, this is a sensitive_channel™.\nAre you sure you want to do this?"
        answer = await yes_no_timeout(ctx, reply)
        if answer is False or answer is None:
            return
    if ctx.channel != target.channel:
        reply = f"Nice try {ctx.author.mention}. Though you are being a dick."
        await ctx.send(reply)
        reply = f"{ctx.author.mention} tried to cross-quoth. Pretty dickish if you ask me."
        await get_channel("super_waifu_chat").send(reply)
        return
    clean_content = store_quote(target, ctx)
    title = "**QUOTE STORED :floppy_disk:**"
    description = f"Author: {target.author.mention}\nStored by: {ctx.author.mention}\n"
    embed = discord.Embed(
        title=title, description=description, color=waifu_pink)
    value = f"\"{clean_content}\""
    embed.add_field(name="Quote", value=value, inline=False)
    await ctx.send(embed=embed)
    return


@bot.command()
@commands.check(is_silly_channel)
@commands.guild_only()
async def inspire(ctx, *, phrase: typing.Optional[str]):
    """Request a random inspirational work of art."""
    if ctx.author.id == 247943708371189761:
        phrase = None
    quote = get_quote(ctx.channel, phrase)
    if quote is None:
        quote = get_quote(ctx.channel, None)
    if quote is None:
        reply = "No quotes found for this channel."
        await ctx.send(reply)
        return
    id = quote[0]
    member = ctx.guild.get_member(quote[3])
    if member:
        name = member.display_name
    else:
        name = quote[4]
    text = quote[7]
    query = None
    if phrase is not None:
        phrase = phrase.split(" ")
        query = random.choice(phrase).lower()
    pending = await ctx.send("Drawing some dumb shit...")
    comical = has_role(ctx.author, "comical")
    image = draw.inspiration(id, text, name, query, comical)
    await pending.edit(content="Drawing is done. Sending now...")
    if image is None:
        reply = "I seem to be unable to draw today."
        await ctx.send(reply)
        await pending.delete()
        return
    file = discord.File(image)
    await ctx.send(file=file)
    image.close()
    file.close()
    await pending.delete()
    return


@bot.command()
@commands.check(is_silly_channel)
@commands.guild_only()
async def shake(ctx, *, target: typing.Optional[typing.Union[discord.Member, discord.Message, str]]):
    """Create a shaky GIF or GIF of text or image attachments."""
    text = ""
    attachments = []
    messages = []
    async for message in ctx.channel.history(limit=20):
        messages.append(message)
    messages.pop(0)
    if target is None and len(ctx.message.attachments) == 0:
        text = messages[0].clean_content
        attachments = messages[0].attachments
    elif isinstance(target, discord.Member):
        for message in messages:
            if message.author == target:
                text = message.clean_content
                attachments = message.attachments
                break
    elif isinstance(target, discord.Message):
        text = target.clean_content
        attachments = target.attachments
    else:
        text = target
        attachments = ctx.message.attachments
    pending = await ctx.send("Drawing some dumb shit...")
    if text != 0 and text is not None:
        image = draw.shaky_text(text)
        file = discord.File(image)
        await ctx.send(file=file)
        image.close()
        file.close()
    for attachment in attachments:
        file = io.BytesIO()
        await attachment.save(file)
        image = draw.shaky_image(file)
        if image == "format":
            reply = f"{ctx.author.mention}, attachment '{attachment.filename}' isn't in a valid format."\
                    f" How would you like it if I force-fed you garbage? "
            await ctx.send(reply)
            continue
        if image == "memory":
            reply = f"{ctx.author.mention}, attachment '{attachment.filename}' is way too big. I ran out of memory!"
            await ctx.send(reply)
            continue
        actual_size = image.getbuffer().nbytes
        if actual_size > 8000000:
            reply = f"{ctx.author.mention}, attachment '{attachment.filename}' is too big."
            await ctx.send(reply)
            image.close()
            file.close()
        else:
            file = discord.File(image)
            try:
                await ctx.send(file=file)
            except discord.errors.HTTPException:
                reply = f"{ctx.author.mention}, attachment '{attachment.filename}' failed and it's your fault."
                await ctx.send(reply)
            finally:
                image.close()
                file.close()
    await pending.delete()
    return


@bot.command(hidden=True)
@commands.has_role("super_waifu")
@commands.guild_only()
async def createkey(ctx, member: discord.Member, key_type: str):
    """Create a webhook key for a member."""
    member_id = member.id
    member_name = member.display_name
    active = True
    key = get_key(member_id, key_type, active)
    if len(key) > 0:
        msg = f"{member_name} already has an active {key_type} key."
        await ctx.send(msg)
        return
    key = create_key(member_id, member_name, key_type)
    title = f"**KEY CREATED :key:**"
    description = f"Key: {key}\nType: {key_type}\nMember: {member.mention}\nCreated by: {ctx.author.mention}\n\n*\"With great power, yada yada.\"*\n- Abraham Lincoln"
    embed = discord.Embed(
        title=title, description=description, color=waifu_pink)
    await member.send(embed=embed)
    embed.description = f"Key: [REDACTED]\nType: {key_type}\nMember: {member.mention}\nCreated by: {ctx.author.mention}\n\n*\"With great power, yada yada.\"*\n- Abraham Lincoln"
    await ctx.send(embed=embed)
    return


@bot.command(hidden=True)
@commands.has_role("super_waifu")
@commands.guild_only()
async def deletekey(ctx, member: discord.Member, key_type: str):
    """Delete a member's webhook key."""
    member_id = member.id
    member_name = member.display_name
    active = True
    key = get_key(member_id, key_type, active)
    if len(key) < 1:
        msg = f"{member_name} does not have an active {key_type} key."
        await ctx.send(msg)
        return
    key = key[0][3]
    delete_key(member_id, key_type)
    title = f"**KEY DELETED :lock:**"
    description = f"Key: {key}\nType: {key_type}\nMember: {member.mention}\nDeleted by: {ctx.author.mention}\n"
    embed = discord.Embed(
        title=title, description=description, color=waifu_pink)
    await ctx.send(embed=embed)
    return


@bot.command(hidden=True)
@commands.has_role("super_waifu")
@commands.guild_only()
async def resetroles(ctx):
    """Use in #role_call to reset the channel"""
    channel = get_channel('role_call')
    await channel.purge(limit=300)
    msg = f'Right-click your name in the member list to see your roles.'
    await channel.send(msg)
    guild = get_guild()
    roles = []
    games = []
    role_colors = [discord.Color.orange(), discord.Color.from_rgb(54, 57, 63)]
    game_colors = [discord.Color.blue()]
    for role in guild.roles:
        if role.name not in config["roles"]["forbidden"]:
            if role.color in role_colors:
                roles.append(role)
            elif role.color in game_colors:
                games.append(role)
    msg = '**ROLES:**'
    await channel.send(msg)
    roles.sort(key=lambda x: x.name.lower())
    for role in roles:
        description = get_description(role.name)
        msg = role.name
        if description:
            msg = f"{msg} - *{description[0]}*"
        msg = await channel.send(msg)
        await asyncio.sleep(1)
        await msg.add_reaction('👍')
        await asyncio.sleep(1)
        await msg.add_reaction('👎')
        await asyncio.sleep(1)
    msg = '**GAMES:**'
    await channel.send(msg)
    games.sort(key=lambda x: x.name.lower())
    for role in games:
        description = get_description(role.name)
        msg = role.name
        if description:
            msg = f"{msg} - *{description[0]}*"
        msg = await channel.send(msg)
        await asyncio.sleep(1)
        await msg.add_reaction('👍')
        await asyncio.sleep(1)
        await msg.add_reaction('👎')
        await asyncio.sleep(1)


@bot.command(hidden=True, aliases=['creategame'])
@commands.has_role("super_waifu")
@commands.check(is_super_channel)
@commands.guild_only()
async def createrole(ctx, role, *, description: typing.Optional[str]):
    """Create a mentionable role."""
    role_colors = [discord.Color.orange(), discord.Color.from_rgb(54, 57, 63)]
    guild = get_guild()
    role_name = ascii_only(role).lower().replace(" ", "_")
    role = get_role(role_name)
    if role is not None:
        if role.color in role_colors:
            role_type = "game"
        else:
            role_type = "role"
        reply = f"{ctx.author.mention}, that {role_type} already exists."
        await ctx.send(reply)
        return
    if ctx.invoked_with.lower() == "createrole":
        role_type = "role"
        emoji = ":passport_control:"
        color = discord.Color.orange()
    else:
        role_type = "game"
        emoji = ":video_game:"
        color = discord.Color.blue()
    role = await guild.create_role(name=role_name, color=color, mentionable=True)
    store_description(role_name=role_name, role_description=description)
    title = f"**{role_type.upper()} CREATED {emoji}**"
    description = f"{role_type.capitalize()}: {role.mention}\nCreated by: {ctx.author.mention}\n"
    embed = discord.Embed(title=title, description=description, color=color)
    await ctx.send(embed=embed)
    return


@bot.command(hidden=True, aliases=['editgame'])
@commands.has_role("super_waifu")
@commands.check(is_super_channel)
@commands.guild_only()
async def editrole(ctx, role: discord.Role, *, description: typing.Optional[str]):
    """Edit a mentionable role."""
    if role.name in config['roles']['forbidden'] or role.color not in [discord.Color.orange(), discord.Color.blue()]:
        reply = f"{ctx.author.mention}, that is a Forbidden Role:tm:."
        await ctx.send(reply)
        return
    old_description = get_description(role.name)
    new_description = description
    store_description(role_name=role.name, role_description=new_description)
    if role.color == discord.Color.orange():
        role_type = "role"
        emoji = ":passport_control:"
        color = discord.Color.orange()
    else:
        role_type = "game"
        emoji = ":video_game:"
        color = discord.Color.blue()
    title = f"**{role_type.upper()} UPDATED {emoji}**"
    description = f"{role_type.capitalize()}: {role.mention}\n"\
                  f"Old description: {old_description}\n"\
                  f"New description: {new_description}\n"\
                  f"Edited by: {ctx.author.mention}\n"
    embed = discord.Embed(title=title, description=description, color=color)
    await ctx.send(embed=embed)
    return


@bot.command(hidden=True, aliases=['deletegame'])
@commands.has_role("super_waifu")
@commands.check(is_super_channel)
@commands.guild_only()
async def deleterole(ctx, role: discord.Role):
    """Delete a mentionable role."""
    if role.name in config['roles']['forbidden'] or role.color not in [discord.Color.orange(), discord.Color.blue()]:
        reply = f"{ctx.author.mention}, that is a Forbidden Role:tm:."
        await ctx.send(reply)
        return
    if role.color == discord.Color.orange():
        role_type = "role"
    else:
        role_type = "game"
    title = f"**{role_type.upper()} DELETED :fire:**"
    description = f"{role_type.capitalize()}: {role.name}\nDeleted by: {ctx.author.mention}\n"
    embed = discord.Embed(
        title=title, description=description, color=role.color)
    await role.delete()
    await ctx.send(embed=embed)
    return


@bot.command(hidden=True)
@commands.has_role("super_waifu")
@commands.check(is_super_channel)
@commands.guild_only()
async def superwtf(ctx):
    """Display this help message."""
    reply = "Oh shit it's a Super_Waifu, everyone pretend like you aren't fucking shit up!\n\n"
    for command in sorted(bot.commands, key=lambda x: x.name):
        if command.hidden:
            reply = reply + get_command_help(command) + "\n"
    reply = reply + "\nIf I'm not working correctly, go fuck yourself, you aren't my boss."
    await ctx.send(reply)
    return


@bot.command(hidden=True)
@commands.has_role("super_waifu")
@commands.check(is_super_channel)
@commands.guild_only()
async def invite(ctx, *, reason: typing.Union[discord.CategoryChannel, str]):
    """Create an invite for the specified reason."""
    if isinstance(reason, str):
        event_name = reason
        event = get_category(event_name)
    else:
        event_name = reason.name
        event = reason
    event_role = get_role(event_name)
    if event_name in config["roles"]["forbidden"]:
        reply = f"{ctx.author.mention}, that is not a valid event/role."
        await ctx.send(reply)
        return
    channel = get_channel("welcome_and_rules")
    if event is None or event_role is None:
        type = "USER"
        event_name = None
        invite = await channel.create_invite(max_age=86400, max_uses=2, temporary=False, unique=True, reason=reason)
    else:
        type = "EVENT"
        reason = None
        invite = await channel.create_invite(max_uses=100, temporary=False, unique=True, reason=reason)
    store_invite_details(invite, ctx.author, reason, event_name)
    title = f"**{type} INVITE CREATED :love_letter:**"
    description = f"Created by: {ctx.author.mention}\nChannel: {channel.mention}\nReason: {reason}\n"
    embed = discord.Embed(
        title=title, description=description, color=waifu_pink)
    value = f"URL: {invite.url}"
    embed.add_field(name="Invite", value=value, inline=False)
    await ctx.send(embed=embed)
    return


@bot.command(hidden=True)
@commands.has_role("super_waifu")
@commands.check(is_super_channel)
@commands.guild_only()
async def deletequote(ctx, id: typing.Optional[typing.Union[int, str]]):
    """Delete a quote by ID or URL"""
    guild = get_guild()
    if id is None:
        history = await ctx.channel.history(limit=25).flatten()
        for message in history:
            if len(message.attachments) == 1:
                id = message.attachments[0].url
                break
    if isinstance(id, str):
        try:
            id = id.split("_")[-1]
            id = id.split(".")[0]
            id = int(id)
        except:
            raise commands.UserInputError
    if not quote_exists(id):
        reply = "I can't find that quote in the database."
        await ctx.send(reply)
        return
    quote = delete_quote(id)
    try:
        author_mention = guild.get_member(int(quote[3])).mention
    except:
        author_mention = quote[4]
    try:
        stored_by_mention = guild.get_member(int(quote[5])).mention
    except:
        stored_by_mention = quote[6]
    text = quote[7]
    if not quote_exists(id):
        title = "**QUOTE DELETED :fire:**"
        description = f"Author: {author_mention}\nStored by: {stored_by_mention}\nDeleted by: {ctx.author.mention}\n"
        embed = discord.Embed(
            title=title, description=description, color=waifu_pink)
        value = f"\"{text}\""
        embed.add_field(name="Quote", value=value, inline=False)
        await ctx.send(embed=embed)
    return


@bot.command(hidden=True)
@commands.has_role("admin")
@commands.guild_only()
async def notice(ctx):
    members = get_members_by_role("secret_senpai")
    guild = get_guild()
    if len(members) < 2:
        reply = "YOU MUST CONSTRUCT ADDITIONAL WEEBS"
        await ctx.send(reply)
    else:
        for i in range(100):
            mismatch = False
            senpai = members.copy()
            kohai = members.copy()

            random.shuffle(senpai)
            random.shuffle(kohai)

            for i in range(len(members)):
                if senpai[i] == kohai[i]:
                    mismatch = True
                if senpai[i].id in config["secret_senpai_exclusions"]:
                    if config["secret_senpai_exclusions"][senpai[i].id] == kohai[i].id:
                        mismatch = True

            if not mismatch:
                for i in range(len(members)):
                    message = f"{senpai[i].display_name}, your covert kohai is {kohai[i].display_name}"\
                              f" ({kohai[i].name}). Get to noticing!"
                    try:
                        await senpai[i].send(message)
                    except:
                        log.error(f"Unable to send message to {senpai[i]}")
                        bot_testing = get_channel("bot_testing")
                        warning = f"{senpai[i]} won't accept DM's. SPOILER: ||'{message}'||"
                        await bot_testing.send(warning)
                    log.info(message)
                secret_senpai = get_role("secret_senpai")
                message = f"{secret_senpai.mention}, check your DMs."
                await ctx.send(message)
                return

        reply = "Unable to match members. Please check exclusions and try again."
        await ctx.send(reply)
        return


@bot.command(hidden=True)
@commands.has_role("admin")
@commands.check(is_super_channel)
@commands.guild_only()
async def createevent(ctx, event: typing.Union[discord.CategoryChannel, str], *, YYYYMMDDHHMMSS: typing.Optional[str]):
    """Create an event category with channels and optional countdown."""
    if isinstance(event, str):
        event_name = event
        event = get_category(event_name)
    else:
        event_name = event.name
    event_role = get_role(event_name)
    if event is not None or event_role is not None:
        reply = f"{ctx.author.mention}, that event/role already exists."
        await ctx.send(reply)
        return
    if YYYYMMDDHHMMSS is not None:
        try:
            date_time_from_str(YYYYMMDDHHMMSS)
        except:
            reply = f"{ctx.author.mention}, '{YYYYMMDDHHMMSS}' is an invalid date format. Try: 'YYYYMMDDHHMMSS'"
            await ctx.send(reply)
            return
    name = ascii_only(event_name).replace(" ", "_").upper()
    guild = get_guild()
    noob_role = get_role("noob")
    quarantine_role = get_role("quarantine")
    event_role = await guild.create_role(name=name.lower(), mentionable=True, color=discord.Color.orange())
    countdown = {
        noob_role: discord.PermissionOverwrite(read_messages=False, send_messages=False, connect=False),
        guild.default_role: discord.PermissionOverwrite(
            send_messages=False, connect=False)
    }
    general = {
        noob_role: discord.PermissionOverwrite(read_messages=False, send_messages=False, connect=False),
        quarantine_role: discord.PermissionOverwrite(read_messages=False, send_messages=False, connect=False),
        event_role: discord.PermissionOverwrite(send_messages=True, connect=True),
        guild.default_role: discord.PermissionOverwrite(
            send_messages=False, connect=False)
    }
    quarantine = {
        noob_role: discord.PermissionOverwrite(read_messages=False, send_messages=False, connect=False),
        event_role: discord.PermissionOverwrite(send_messages=True, connect=True),
        guild.default_role: discord.PermissionOverwrite(
            send_messages=False, connect=False)
    }
    category = await guild.create_category_channel(name=name, overwrites=general)
    if YYYYMMDDHHMMSS is not None:
        topic = f"countdown to {YYYYMMDDHHMMSS}"
        await category.create_text_channel(name="countdown", overwrites=countdown, topic=topic)
    primary_channel = await category.create_text_channel(name=f"{name.lower()}_chat", overwrites=general)
    await category.create_voice_channel(name=f"{name.lower()}_voice", overwrites=general)
    await category.create_text_channel(name="questions", overwrites=general, slowmode_delay=300)
    await category.create_text_channel(name="looking_for_room", overwrites=general)
    await category.create_text_channel(name="quarantine_chat", overwrites=quarantine, slowmode_delay=10)
    await category.create_voice_channel(name="quarantine_voice", overwrites=quarantine)
    title = "**EVENT CREATED :confetti_ball:**"
    description = f"Event: {category.name}\n"\
                  f"Created by: {ctx.author.mention}\n"\
                  f"Primary channel: {primary_channel.mention}\n"\
                  f"Countdown to: {YYYYMMDDHHMMSS}\n"
    embed = discord.Embed(
        title=title, description=description, color=waifu_pink)
    value = f"!invite {category.name} - Create 100 use event invite.\n"\
            f"!deleteevent {category.name} - Pretty self-explanatory.\n"
    embed.add_field(name="Commands", value=value, inline=False)
    await ctx.send(embed=embed)
    return


@bot.command(hidden=True)
@commands.has_role("admin")
@commands.check(is_super_channel)
@commands.guild_only()
async def deleteevent(ctx, *, event: typing.Union[discord.CategoryChannel, str]):
    """Delete an event category and channels."""
    if isinstance(event, str):
        event_name = event.lower()
        event = get_category(event_name)
    else:
        event_name = event.name.lower()
    event_role = get_role(event_name)
    if event is None or event_role is None or event_name in config["roles"]["forbidden"]:
        reply = f"{ctx.author.mention}, that is not a valid event/role."
        await ctx.send(reply)
        return
    for channel in event.channels:
        await channel.delete()
    await event.delete()
    title = "**EVENT DELETED :cry:**"
    description = f"Event: {event.name}\nDeleted by: {ctx.author.mention}\n"
    embed = discord.Embed(
        title=title, description=description, color=waifu_pink)
    quarantined = get_members_by_role("quarantine")
    value = ""
    for member in quarantined:
        if event_role in member.roles:
            value = value + f"{member.mention}\n"
    if value != "":
        embed.add_field(name="Quarantined users", value=value, inline=False)
    await ctx.send(embed=embed)
    await event_role.delete()
    return


@bot.command(hidden=True)
@commands.has_role("admin")
@commands.check(is_super_channel)
@commands.guild_only()
async def say(ctx, channel: discord.TextChannel, *, text: typing.Optional[str]):
    """Make me say something and/or post attachments."""
    if text is None and len(ctx.message.attachments) == 0:
        raise commands.UserInputError
    files = []
    file_paths = []
    for attachment in ctx.message.attachments:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = "{}_{}".format(timestamp, attachment.filename)
        file_path = os.path.join(sys.path[0], "tmp", file_name)
        await attachment.save(file_path)
        file = discord.File(
            file_path, filename=attachment.filename, spoiler=attachment.is_spoiler())
        files.append(file)
        file_paths.append(file_path)
    await channel.send(content=text, files=files)
    for file in files:
        file.close()
    for file_path in file_paths:
        os.remove(file_path)
    super_waifu_chat = get_channel("super_waifu_chat")
    reply = f"{ctx.author.mention} made me say something in {channel.mention}."
    await super_waifu_chat.send(reply)
    return


@bot.command(hidden=True)
@commands.has_role("admin")
@commands.check(is_super_channel)
@commands.guild_only()
async def archive(ctx, channel: discord.TextChannel):
    """Archive a text channel."""
    message_count = 0
    file_count = 0
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    messages = await channel.history(limit=None).flatten()
    tmp_dir = os.path.join(sys.path[0], "tmp", channel.name)
    log_path = os.path.join(tmp_dir, "log.csv")
    archive_path = os.path.join(
        sys.path[0], "archive", f"{channel.name}-{timestamp}")
    os.mkdir(tmp_dir)
    with open(log_path, "w", newline='') as csv_file:
        csv_file = csv.writer(csv_file, delimiter=',',
                              quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for message in messages:
            csv_line = [
                message.created_at.strftime("%Y%m%d%H%M%S"),
                str(message.id),
                str(message.author.id),
                str(ascii_only(message.author.name)),
                str(ascii_only(message.author.display_name)),
                str(ascii_only(message.clean_content)),
                str(len(message.attachments))
            ]
            message_count += 1
            for index, attachment in enumerate(message.attachments):
                filename = f"{message.id}_{index}_{attachment.filename}"
                await attachment.save(os.path.join(tmp_dir, filename))
                file_count += 1
            csv_file.writerow(csv_line)
    shutil.make_archive(archive_path, 'zip', tmp_dir)
    shutil.rmtree(tmp_dir)
    reply = f"{message_count} messages and {file_count} attachments archived to {channel.name}-{timestamp}.zip"
    await ctx.send(reply)
    return


@bot.command(hidden=True)
@commands.has_role("admin")
@commands.check(is_super_channel)
@commands.guild_only()
async def die(ctx):
    """Kill my currently running instance. I won't forget this."""
    reply = random.choice(strings['last_words'])
    await ctx.send(reply)
    exit(0)
    return

@bot.command()
@commands.check(is_silly_channel)
@commands.guild_only()
async def image(ctx, *, query):
    """Finds an image using Google Images (safesearch off)"""
    api_key = config["api"]["google"]
    url = ("https://www.googleapis.com/customsearch/v1?cx=012763604623577894851:r8w2tzy60qx"
            "&fields=items(title,link,snippet)&safe=off&nfpr=1&searchType=image")
    r = requests.get(url, params={"key": api_key, "q": query, "num": 10})
    data = r.json()
    items = data["items"]
    choice = random.choice(items)
    title = choice["title"]
    link = choice["link"]
    embed=discord.Embed(title=title, url=link, color=0xff3fb4)
    embed.set_image(url=link)
    await ctx.send(embed=embed)
    return

global block_noobs
block_noobs = False
create_database()
token = config["discord"]["token"]
bot.run(token)
