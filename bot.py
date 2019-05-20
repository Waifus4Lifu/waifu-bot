#!/usr/bin/python3.6
import io
import os
import re
import sys
import draw
import random
import typing
import asyncio
import aiohttp
import discord
import textwrap
from functions import *
from discord.ext import commands
from datetime import datetime

bot = commands.Bot(command_prefix="!", help_command=None)

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

def get_members_by_role(name):
    return get_role(name).members

async def detect_reposts(message):
    if message.channel.name in config['channels']['ignore_reposts']:
        return
    guild = get_guild()
    title = "**REPOST DETECTED :recycle:**"
    author = message.author
    description = f"Reposter: {author.mention}"
    embed = discord.Embed(title=title, description=description, color=waifu_pink)
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
        description = description + "You're not breaking the rules, but you are being a scumbag."
        embed = discord.Embed(title=title, description=description, color=waifu_pink)
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
    if message.channel.topic != str(message.author.id):
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
        reply = f"Hey everyone, {message.author.mention} just joined. {message.author.mention}, please introduce yourself. Thanks!"
        await general_chat.send(reply)
    else:
        reply = "Not quite. Try again."
        await message.channel.send(reply)
    return

async def always_sunny(message):
    text = message.clean_content.replace("*", "")
    text = message.clean_content.replace("_", "")
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

@asyncio.coroutine
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

@asyncio.coroutine
async def monitor_noobs():
    global block_noobs
    guild = get_guild()
    noob_role = get_role("noob")
    super_waifu_chat = get_channel("super_waifu_chat")
    while True:
        for member in get_members_by_role("noob"):
            if get_channel_by_topic(str(member.id)) == None:
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
                if member == None or member not in noobs:
                    if block_noobs:
                        await asyncio.sleep(5)
                    else:
                        await channel.delete()
                        reply = f"<@{id}> no longer has the noob role. Removing welcome_noob channel."
                        await super_waifu_chat.send(reply)
        await asyncio.sleep(1)

@asyncio.coroutine
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
            reply = f"Hey {deleted_by.mention}, it's best if you don't delete messages from {message.channel.mention}. Unless of course they're really bad."
            await super_waifu_chat.send(reply)
            continue
        timestamp = message.created_at.strftime("%m/%d/%Y %H:%M")
        title = f"ID: {message.id}"
        description = f"Author: {author.mention}\nDeleted by: {deleted_by.mention}*\nChannel: {message.channel.mention}\nUTC: {timestamp}"
        embed = discord.Embed(title=title, description=description, color=discord.Color.red())
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

@asyncio.coroutine
async def monitor_joins():
    global block_noobs
    guild = get_guild()
    super_waifu_chat = get_channel("super_waifu_chat")
    title = f"**NOOB DETECTED :joyfuljigo:**"
    previous_invites = await guild.invites()
    while True:
        try:
            member = await bot.wait_for("member_join", timeout=3)
        except asyncio.TimeoutError:
            previous_invites = await guild.invites()
            continue
        description = f"Noob: {member.mention}\n"
        embed = discord.Embed(title=title, description=description, color=waifu_pink)
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
            channel = invite_found.channel
            url = invite_found.url
            if invite_found.max_uses == 2 and invite_found.uses == 1 and invite_details is not None:
                invite_type = "USER"
                invited_by = guild.get_member(int(invite_details[3])).mention
                reason = invite_details[7]
                await invite_found.delete()
            elif invite_found.max_uses == 100 and invite_details is not None:
                invite_type = "EVENT"
                invited_by = guild.get_member(int(invite_details[3])).mention
                reason = invite_details[7]
                await member.add_roles(get_role("quarantine"))
            else:
                invite_type = "UNOFFICIAL"
                invited_by = invite_found.inviter.mention
                reason = f"Fuck if I know. Ask {invited_by}."
            value = f"Type: {invite_type}\nCreated by: {invited_by}\nChannel: {channel.mention}\nReason: {reason}\nURL: {url}\n"
        else:
            value = "ERROR: NO MATCHING INVITE FOUND"
        embed.add_field(name="Invite", value=value, inline=False)
        await super_waifu_chat.send(embed=embed)
        super_waifu = get_role("super_waifu")
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True),
            super_waifu: discord.PermissionOverwrite(read_messages=True),
            member: discord.PermissionOverwrite(read_messages=True)
        }
        block_noobs = True
        await member.add_roles(get_role("noob"))
        channel = await guild.create_text_channel("welcome_noob", topic=str(member.id), overwrites=overwrites)
        block_noobs = False
        reply = f"Hey {member.mention}, welcome to Waifus_4_Lifu! I'm WaifuBot, I manage various things here. Here is a basic outline of our rules:"
        await channel.send(reply)
        reply = "1. Don't be a dick. We all like to have fun and mess around but let's try and keep it playful! On that note, please try and keep negativity to a minimum. All it does is bring everyone else down and we don't want that! This is intended to be a fun environment.\n\n"
        reply = reply + "2. Introduce yourself before you start posting! Everybody is welcome, we just want to know who you are and what you are into!\n\n"
        reply = reply + "3. If you want to post something NSFW (or just shitpost memes) then we have a channel for that! Just remember if its illegal we don't want to see it and you will be immediately banned without question. The shitposting channel has it's own special rules, please read them if you decide to join it. To gain access to the channel just type `!join shitty_people` in general and WaifuBot will grant you access!\n\n"
        reply = reply + "4. Speaking of, we have a bot! If you want a list of commands just type `!wtf` or `!help` and WaifuBot will explain!\n\n"
        reply = reply + "5. If you have a problem of some sort, tag a Super Waifu. They are here to help!\n\n"
        reply = reply + "6. We have voice channels for specific games and for general conversation! Please try and use the appropriate channel based on what you are playing or doing.\n\n"
        reply = reply + "7. We don't have rules for all types of behaviors and actions. That being said, if a Super Waifu or Admin contacts you regarding something you have said or done, please be willing to comply. We try our hardest to make sure everybody here is having a good time. On that same note, if you have some sort of issue or concern with something that has been said or done then please bring it to a Super Waifu or Admin's attention. Your concern will be reviewed and addressed appropriately.\n\n"
        reply = reply + "8. Have fun! That is why we made this server!\n\n**Before we continue, what's rule #1?**"
        await channel.send(reply)

@bot.event
async def on_ready():
    log.info(f"Logged on as {bot.user}")
    loop = asyncio.get_event_loop()
    change_status_task = loop.create_task(change_status())
    monitor_noobs_task = loop.create_task(monitor_noobs())
    monitor_deletions_task = loop.create_task(monitor_deletions())
    monitor_joins_task = loop.create_task(monitor_joins())

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
        reply = f"Fucking what? {ctx.author.mention}, just who do you think you are?"
        await ctx.send(reply)
    elif isinstance(error, commands.NoPrivateMessage):
        reply = f"Say, uh {ctx.author.mention}, let's find a better channel for this."
        await ctx.send(reply)
    elif isinstance(error, commands.errors.CommandNotFound):
        reply = f"{ctx.author.mention}, that's not a valid command. Maybe try `!wtf`."
        await ctx.send(reply)
    elif isinstance(error, commands.errors.CommandInvokeError):
        raise error.original
    log_msg = f"[{ctx.author}] - [{ctx.channel}]\n[{error.__class__}]\n{ctx.message.content}"
    log.error(log_msg)
    return

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return
    lower = message.clean_content.lower()
    if isinstance(message.channel, discord.TextChannel):
        if message.channel.name == "welcome_noob":
            await reply_noob(message)
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
            file = discord.File(os.path.join(sys.path[0], 'images', 'dennis.gif'))
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
async def members(ctx, role: discord.Role):
    """Show a list of members who have signed up for a role/game."""
    if role.name in config['roles']['forbidden']:
        reply = f"{ctx.author.mention}, this is a Forbidden Role:tm:. If you can't figure this out a different way, you don't deserve to know."
        await ctx.send(reply)
        return
    if len(role.members) == 0:
        reply = f"No members are signed up for '{role.name}'. It's probably a Stupid Role:tm:."
        await ctx.send(reply)
        return
    length = 0
    for member in role.members:
        if len(member.display_name) > length:
            length = len(member.display_name)
    reply = f"The following members have signed up for '{role.name}':\n\n"
    for member in role.members:
        reply = reply + f"`{member.display_name.ljust(length)}{member.status.name.rjust(10)}`\n"
    for page in paginate(reply):
        await ctx.send(page)
        await asyncio.sleep(1)
    return

@bot.command(aliases=["games"])
@commands.guild_only()
async def roles(ctx):
    """Show a list of mentionable roles/games you can join."""
    guild = get_guild()
    length = 0
    roles = []
    for role in guild.roles:
        if role.name not in config["roles"]["forbidden"]:
            if ctx.invoked_with == "roles" and role.name == role.name.lower():
                roles.append(role)
                if len(role.name) > length:
                    length = len(role.name)
            elif ctx.invoked_with == "games" and role.name == role.name.upper():
                roles.append(role)
                if len(role.name) > length:
                    length = len(role.name)
    reply = f"The following {ctx.invoked_with} are joinable:\n\n"
    for role in roles:
        role_name = role.name.ljust(length)
        count = str(len(role.members)).rjust(6)
        reply = reply + f"`{role_name}{count}`\n"
    for page in paginate(reply):
        await ctx.send(page)
        await asyncio.sleep(1)
    return

@bot.command()
@commands.guild_only()
async def join(ctx, role: discord.Role):
    """Join a mentionable role/game."""
    if role.name in config['roles']['forbidden']:
        reply = f"{ctx.author.mention}, you can't join a Forbidden Role:tm:."
        await ctx.send(reply)
        return
    if role in ctx.author.roles:
        reply = f"{ctx.author.mention}, you already have that role."
        await ctx.send(reply)
        return
    await ctx.author.add_roles(role)
    reply = f"{ctx.author.mention}, you now have the '{role.name}' role"
    await ctx.send(reply)
    return

@bot.command()
@commands.guild_only()
async def leave(ctx, role: discord.Role):
    """Leave a mentionable role/game."""
    if role.name in config['roles']['forbidden']:
        reply = f"{ctx.author.mention}, you can't leave a Forbidden Role:tm:."
        await ctx.send(reply)
        return
    if role not in ctx.author.roles:
        reply = f"{ctx.author.mention}, you don't have that role."
        await ctx.send(reply)
        return
    await ctx.author.remove_roles(role)
    reply = f"{ctx.author.mention}, you no longer have the '{role.name}' role"
    await ctx.send(reply)
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
            is_not = ["n't", "not", "no", "crypto"]
            for word in is_not:
                if (word in answer.content.lower() and "random" in answer.content.lower()) or answer.content.lower().startswith("!random"):
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
        if answer == False or answer == None:
            return
    clean_content = store_quote(target, ctx)
    title = "**QUOTE STORED :floppy_disk:**"
    description = f"Author: {target.author.mention}\nStored by: {ctx.author.mention}\n"
    embed = discord.Embed(title=title, description=description, color=waifu_pink)
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
    if quote == None:
        quote = get_quote(ctx.channel, None)
    id = quote[0]
    name = quote[4]
    text = quote[7]
    query = None
    if phrase != None:
        phrase = phrase.split(" ")
        query = random.choice(phrase).lower()
    pending = await ctx.send("Drawing some dumb shit...")
    comical = has_role(ctx.author, "comical")
    image = draw.inspiration(id, text, name, query, comical)
    await pending.edit(content="Drawing is done. Sending now...")
    if image == None:
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
    if target == None and len(ctx.message.attachments) == 0:
        text = messages[0].clean_content
        attachments = messages[0].attachments
    elif isinstance(target, discord.Member):
        for message in messages:
            if (message.author == target):
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
    if text != 0 and text != None:
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
            reply = f"{ctx.author.mention}, attachment '{attachment.filename}' isn't in a valid format. How would you like it if I force-fed you garbage?"
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

@bot.command(hidden=True, aliases=['creategame'])
@commands.has_role("super_waifu")
@commands.check(is_super_channel)
@commands.guild_only()
async def createrole(ctx, role: str):
    """Add a mentionable role. Required format: `WAIFUS_4_LIFU`."""
    guild = get_guild()
    super_waifu_chat = get_channel("super_waifu_chat")
    if ctx.invoked_with == "createrole":
        if role != role.lower():
            reply = "Roles must be lowercase."
            await ctx.send(reply)
            return
        convention = "`waifus_4_lifu`"
    else:
        if role != role.upper():
            reply = "Games must be uppercase."
            await ctx.send(reply)
            return
        convention = "`WAIFUS_4_LIFU`"
    if get_role(role) != None:
        reply = "That role already exists, dummy."
        await ctx.send(reply)
        return
    if "_" not in role:
        reply = f"I don't see any underscores. Are you sure you're following the '{convention}' convention?"
        if not await yes_no_timeout(ctx, reply):
            return
    role = await guild.create_role(name=role, mentionable=True)
    reply = f"{ctx.author.mention} has created the {role.mention} role.\nBerate them if they didn't follow the '{convention}' convention"
    await super_waifu_chat.send(reply)
    return

@bot.command(hidden=True, aliases=['deletegame'])
@commands.has_role("super_waifu")
@commands.check(is_super_channel)
@commands.guild_only()
async def deleterole(ctx, role: discord.Role):
    """Delete a mentionable role."""
    if role.name in config['roles']['forbidden']:
        reply = f"{ctx.author.mention}, that is a Forbidden Role:tm:."
        await ctx.send(reply)
        return
    if ctx.invoked_with == "deleterole" and role.name == role.name.upper():
        reply = f"{ctx.author.mention} that is a game."
        await ctx.send(reply)
        return
    if ctx.invoked_with == "deletegame" and role.name == role.name.lower():
        reply = f"{ctx.author.mention} that is not a game."
        await ctx.send(reply)
        return
    guild = get_guild()
    super_waifu_chat = get_channel("super_waifu_chat")
    reply = f"{ctx.author.mention} has deleted the '{role.name}' role."
    await role.delete()
    await super_waifu_chat.send(reply)
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
async def invite(ctx, channel: typing.Optional[discord.TextChannel], *, reason):
    """Create an invite for the specified person/channel and reason."""
    if channel == None:
        channel = get_channel("welcome_and_rules")
        type = "USER"
        invite = await channel.create_invite(max_age=86400, max_uses=2, temporary=False, unique=True, reason=reason)
    else:
        type = "EVENT"
        invite = await channel.create_invite(max_uses=100, temporary=False, unique=True, reason=reason)
    super_waifu_chat = get_channel("super_waifu_chat")
    store_invite_details(invite, ctx.author, reason)
    title = f"**{type} INVITE CREATED :love_letter:**"
    description = f"Created by: {ctx.author.mention}\nChannel: {channel.mention}\nReason: {reason}\n"
    embed = discord.Embed(title=title, description=description, color=waifu_pink)
    value = f"URL: {invite.url}"
    embed.add_field(name="Invite", value=value, inline=False)
    await super_waifu_chat.send(embed=embed)
    return

@bot.command(hidden=True)
@commands.has_role("super_waifu")
@commands.check(is_super_channel)
@commands.guild_only()
async def deletequote(ctx, id: typing.Optional[typing.Union[int, str]]):
    """Delete a quote by ID or URL"""
    guild = get_guild()
    if id == None:
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
        embed = discord.Embed(title=title, description=description, color=waifu_pink)
        value = f"\"{text}\""
        embed.add_field(name="Quote", value=value, inline=False)
        await ctx.send(embed=embed)
    return

@bot.command(hidden=True)
@commands.has_role("admin")
@commands.check(is_super_channel)
@commands.guild_only()
async def createevent(ctx, *, name):
    """Create an event category with text and voice channels."""
    name = ascii_only(name).replace(" ", "_").upper()
    general = get_category("GENERAL")
    category = await general.clone(name=name)
    quarantine_role = get_role("quarantine")
    noob_role = get_role("noob")
    overwrites = {
        noob_role: discord.PermissionOverwrite(read_messages=False, send_messages=False, connect=False, speak=False),
        quarantine_role: discord.PermissionOverwrite(read_messages=None, send_messages=None, connect=None, speak=None)
    }
    primary_channel = await category.create_text_channel(name=f"{name.lower()}_chat")
    await category.create_voice_channel(name=f"{name.lower()}_voice")
    await category.create_text_channel(name="questions", slowmode_delay=300)
    await category.create_text_channel(name="looking_for_room")
    await category.create_text_channel(name="quarantine_chat", overwrites=overwrites, slowmode_delay=10)
    await category.create_voice_channel(name="quarantine_voice", overwrites=overwrites)
    super_waifu_chat = get_channel("super_waifu_chat")
    title = "**EVENT CREATED :confetti_ball:**"
    description = f"Event: {category.name}\nCreated by: {ctx.author.mention}\nPrimary channel: {primary_channel.mention}\n"
    embed = discord.Embed(title=title, description=description, color=waifu_pink)
    value = f"`!invite {primary_channel.name} <reason>` - Create 100 use event invite.\n`!deleteevent {category.name}` - Pretty self-explanatory.\n"
    embed.add_field(name="Commands", value=value, inline=False)
    await super_waifu_chat.send(embed=embed)
    return

@bot.command(hidden=True)
@commands.has_role("admin")
@commands.check(is_super_channel)
@commands.guild_only()
async def deleteevent(ctx, event: discord.CategoryChannel):
    for channel in event.channels:
        await channel.delete()
    await event.delete()
    super_waifu_chat = get_channel("super_waifu_chat")
    title = "**EVENT DELETED :cry:**"
    description = f"Event: {event.name}\nDeleted by: {ctx.author.mention}\n"
    embed = discord.Embed(title=title, description=description, color=waifu_pink)
    quarantined = get_members_by_role("quarantine")
    if len(quarantined) > 0:
        value = ""
        for member in quarantined:
            value = value + f"{member.mention}\n"
        embed.add_field(name="Quarantined users", value=value, inline=False)
    await super_waifu_chat.send(embed=embed)
    return

@bot.command(hidden=True)
@commands.has_role("admin")
@commands.check(is_super_channel)
@commands.guild_only()
async def say(ctx, channel: discord.TextChannel, *, text: typing.Optional[str]):
    """Make me say something and/or post attachments."""
    if text == None and len(ctx.message.attachments) == 0:
        raise commands.UserInputError
    files = []
    file_paths = []
    for attachment in ctx.message.attachments:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = "{}_{}".format(timestamp, attachment.filename)
        file_path = os.path.join(sys.path[0], "tmp", file_name)
        await attachment.save(file_path)
        file = discord.File(file_path, filename=attachment.filename, spoiler=attachment.is_spoiler())
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
async def die(ctx):
    """Kill my currently running instance. I won't forget this."""
    reply = random.choice(strings['last_words'])
    await ctx.send(reply)
    exit(0)
    return

global block_noobs
block_noobs = False
create_database()
token = config["discord"]["token"]
bot.run(token)
