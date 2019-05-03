import os
import re
import sys
import draw
import random
import typing
import asyncio
import aiohttp
import discord
import logging as log
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
    
def is_silly_channel(ctx):
    if ctx.channel.name in config["channels"]["serious"]:
        raise commands.NoPrivateMessage
    return True
    
def get_guild():
    guild_id = config["discord"]["guild_id"]
    return bot.get_guild(guild_id)
    
def get_channel(name):
    for channel in get_guild().channels:
        if channel.name == name:
            return channel
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
    for attachment in message.attachments:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        original_file_name = attachment.url.split("/")[-1]
        file_name = f"{timestamp}_{original_file_name}"
        file_path = os.path.join(sys.path[0], "tmp", file_name)
        await attachment.save(file_path)
        attachment_hash = sha_256(file_path)
        previous_hashes = get_hashes(attachment_hash)
        count = len(previous_hashes)
        if count > 0:
            date_time = previous_hashes[0][2]
            delta = time_since(date_time)
            channel = get_channel(previous_hashes[0][5])
            author = previous_hashes[0][4]
            reply = f"**REPOST ALERT!**\nAttachment '{attachment.filename}' has previously been posted {count} time(s). Most recently {delta} ago in {channel.mention} by {author}."
            await message.channel.send(reply)
        store_hash(attachment_hash, message)
        os.remove(file_path)
    
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
    noobs_role = get_role("noobs")
    super_waifu_chat = get_channel("super_waifu_chat")
    while True:
        for member in get_members_by_role("noobs"):
            if get_channel_by_topic(str(member.id)) == None:
                if block_noobs:
                    await asyncio.sleep(3)
                else:
                    await member.remove_roles(noobs_role)
                    reply = f"No welcome_noob channel found for {member.mention}. Removing noobs role."
                    await super_waifu_chat.send(reply)
        for channel in guild.text_channels:
            if channel.name == "welcome_noob":
                member = guild.get_member(int(channel.topic))
                noobs = get_members_by_role("noobs")
                if member == None or member not in noobs:
                    if block_noobs:
                        await asyncio.sleep(3)
                    else:
                        await channel.delete()
                        reply = f"{member.mention} no longer has the noobs role. Removing welcome_noob channel."
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
        if author == bot.user:
            continue
        timestamp = message.created_at.strftime("%m/%d/%Y %H:%M")
        description = "Author: {}\nDeleted by: {}*\nChannel: {}\nUTC: {}"
        description = description.format(author.mention, deleted_by.mention, message.channel.mention, timestamp)
        embed = discord.Embed(description=description, color=0xff0000)
        if len(message.content) > 0:
            embed.add_field(name="Message", value=message.content, inline=True)
        if len(message.attachments) > 0:
            name = "Attachments"
            value = ""
            for attachment in message.attachments:
                value = value + "<{}>\n".format(attachment.proxy_url)
            embed.add_field(name=name, value=value, inline=True)
        if message.channel.name in config["channels"]["female_only"]:
            channel = get_channel("deleted_thots")
        else:
            channel = get_channel("deleted_text")
        topic = "*The deleted_by value is susceptible to an extremely unlikely race condition."
        if channel.topic != topic:
            await channel.edit(topic=topic)
        await channel.send(embed=embed)

@bot.event
async def on_ready():
    log.info(f"Logged on as {bot.user}")
    loop = asyncio.get_event_loop()
    change_status_task = loop.create_task(change_status())
    monitor_noobs_task = loop.create_task(monitor_noobs())
    monitor_deletions_task = loop.create_task(monitor_deletions())
    
@bot.event
async def on_member_join(member):
    global block_noobs
    official_invite = False
    if member.bot:
        return
    guild = member.guild
    super_waifu_chat = get_channel("super_waifu_chat")
    invites = await get_channel("welcome_and_rules").invites()
    for invite in invites:
        invite_details = get_invite_details(invite)
        if invite.uses == 1 and invite.max_uses == 2 and invite_details != None:
            official_invite = True
            invited_by = guild.get_member(int(invite_details[3]))
            reason = invite_details[7]
            reply = f"{member.mention} joined using an invite created by {invited_by.mention} with reason: '{reason}'"
            await super_waifu_chat.send(reply)
            update_invite_details(invite, member)
            await invite.delete()
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True),
        member: discord.PermissionOverwrite(read_messages=True)
        }
    block_noobs = True
    await member.add_roles(get_role("noobs"))
    channel = await guild.create_text_channel("welcome_noob", topic=str(member.id), overwrites=overwrites)
    block_noobs = False
    reply = "Hey {member.mention}, welcome to Waifus_4_Lifu! I'm WaifuBot, I manage various things here. Here is a basic outline of our rules:"
    await channel.send(reply)
    await asyncio.sleep(3)
    reply = """
        1. Don"t be a dick. We all like to have fun and mess around but let"s try and keep it playful! Nobody likes a salty Sammy. On that note, please try and keep negativity to a minimum. All it does is bring everyone else down and we don"t want that! This is intended to be a fun environment.\n
        2. Introduce yourself before you start posting! Everybody is welcome, we just want to know who you are and what you are into! Tell us your name, what you play, or even who invited you!\n
        3. If you want to post something NSFW (or just shitposting memes) then we have a channel for that! Just remember if its illegal we don"t want to see it and you will be immediately banned without question. The shitposting channel has it"s own special rules, please read them if you decide to join it. To gain access to the channel just type !join shitposting in general and WaifuBot will grant you access!\n
        4. Speaking of, we have a bot! If you want a list of commands just type !wtf or !help and WaifuBot will explain!\n
        5. If you have a problem of some sort, let a Super Waifu know. They are here to help!\n
        6. We have voice channels for specific games and for general conversation! Please try and use the appropriate channel based on what you are playing or doing. If you need some sort of assistance with voice channels or maybe someone is AFK in a non-AFK channel then ping any Super Waifu and they will assist!\n
        7. We don"t have rules for all types of behaviors and actions. That being said, if a Super Waifu or Admin contacts you regarding something you have said or done, please be willing to comply. We try our hardest to make sure everybody here is having a good time. On that same note, if you have some sort of issue or concern with something that has been said or done then please bring it to a Super Waifu or Admins attention. Your concern will be reviewed and addressed appropriately.\n
        8. Have fun! That is why we made this server! **Before we continue, what"s rule #1?**
        """
    await channel.send(reply)
    if not official_invite:
        reply = f"{member.mention} joined using an unofficial invite. See audit log."
        await super_waifu_chat.send(reply)
    return
    
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
    global block_noobs
    if message.author == bot.user:
        return
    if not message.content.startswith("!"):
        if isinstance(message.channel, discord.TextChannel):
            if message.channel.name == "welcome_noob":
                answer = re.sub("[^0-9a-zA-Z]+", "", message.clean_content).lower()
                if answer == "dontbeadick":
                    reply = "Yup. Thanks! I'll grant you access. Just a sec..."
                    await message.channel.send(reply)
                    await asyncio.sleep(1)
                    block_noobs = True
                    await ctx.author.remove_roles(get_role("noobs"))
                    await asyncio.sleep(1)
                    await channel.delete()
                    await asyncio.sleep(1)
                    block_noobs = False
                    general_chat = get_channel("general_chat")
                    reply = f"Hey everyone, {message.author.mention} just joined. {message.author.mention}, please introduce yourself. Thanks!"
                    await general_chat.send(reply)
                else:
                    reply = "Not quite. Try again."
                    await message.channel.send(reply)
        
        if "thank" in message.content.lower() and bot.user in message.mentions:
            reply = random.choice(strings["no_problem"])
            await message.channel.send(reply)
            
        if "hungry" in message.content.lower().replace(" ", ""):
            if chance(config['chance']['hungry']):
                reply = "No, <@221162619497611274> is hungry."
                file = discord.File(os.path.join(sys.path[0], 'images', 'dennis.gif'))
                await message.channel.send(reply, file=file)
                file.close()
                
        if isinstance(message.channel, discord.TextChannel):
            await detect_reposts(message)
            
    await bot.process_commands(message)
    return
    
@bot.command(aliases=["help"])
async def wtf(ctx):
    """Display this help message."""
    reply = "I understand the following commands:\n\n"
    for command in sorted(bot.commands, key=lambda x: x.name):
        if not command.hidden:
            reply = reply + get_command_help(command) + "\n"
    reply = reply + "\nIf I'm not working correctly, go fuck yourself, you aren't my boss."
    await ctx.send(reply)

@bot.command(aliases=["players"])
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
    await ctx.send(reply)
    return
    
@bot.command(aliases=["games"])
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
    await ctx.send(reply)
    return

@bot.command()
async def test(ctx):
    """Test something."""
    
    return
    
@bot.command()
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
async def magic8ball(ctx, question: str):
    """Ask the magic 8 ball a question."""
    answer = random.choice(strings['eight_ball'])
    reply = f"{ctx.author.mention}, the magic 8 ball has spoken: \"{answer}\"."
    await ctx.send(reply)
    return

@bot.command(name="color")
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
    image_path = draw.spongebob(ctx, target)
    await pending.edit(content="Drawing is done. Sending now...")
    file = discord.File(image_path)
    await ctx.send(file=file)
    file.close()
    os.remove(image_path)
    await pending.delete()
    return
        
@bot.command()
@commands.check(is_silly_channel)
async def quoth(ctx, target: typing.Optional[typing.Union[discord.Member, discord.Message]]):
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
    reply = f"{ctx.author.mention} successfully stored the following message:\n\n{target.author}: \"{clean_content}\""
    await ctx.send(reply)
    return
 
@bot.command()
@commands.check(is_silly_channel)
async def inspire(ctx, *, phrase: typing.Optional[str]):
    """Request a random inspirational work of art."""
    quote = get_quote(ctx.channel, phrase)
    if quote == None:
        reply = "I can't find any matching inspiration."
        await ctx.send(reply)
        return
    id = quote[0]
    name = quote[4]
    text = quote[7]
    pending = await ctx.send("Drawing some dumb shit...")
    image_path = draw.inspiration(id, text, name)
    await pending.edit(content="Drawing is done. Sending now...")
    file = discord.File(image_path)
    await ctx.send(file=file)
    file.close()
    os.remove(image_path)
    await pending.delete()
    return
    
@bot.command()
@commands.check(is_silly_channel)
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
        image_path = draw.shaky_text(text)
        file = discord.File(image_path)
        await ctx.send(file = file)
        file.close()
        os.remove(image_path)
    for attachment in attachments:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = "{}_{}".format(timestamp, attachment.filename)
        file_path = os.path.join(sys.path[0], "tmp", file_name)
        await attachment.save(file_path)
        image_path = draw.shaky_image(file_path)
        if image_path == "format":
            reply = f"{ctx.author.mention}, attachment '{attachment.filename}' isn't in a valid format. How would you like it if I force-fed you garbage?"
            await ctx.send(reply)
            continue
        if image_path == "memory":
            reply = f"{ctx.author.mention}, attachment '{attachment.filename}' is way too big. I ran out of memory!"
            await ctx.send(reply)
            continue
        actual_size = os.path.getsize(image_path)
        if actual_size > 8000000:
            reply = f"{ctx.author.mention}, attachment '{attachment.filename}' is too big."
            await ctx.send(reply)
            os.remove(image_path)
        else:
            file = discord.File(image_path)
            try:
                await ctx.send(file=file)
            except discord.errors.HTTPException:
                reply = f"{ctx.author.mention}, attachment '{attachment.file_name}' failed and it's your fault."
                await ctx.send(reply)
            finally:
                file.close()
                os.remove(image_path)
    await pending.delete()
    return
    
@bot.command(hidden=True, aliases=['creategame'])
@commands.has_role("super_waifus")
@commands.check(is_super_channel)
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
@commands.has_role("super_waifus")
@commands.check(is_super_channel)
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
@commands.has_role("super_waifus")
@commands.check(is_super_channel)
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
@commands.has_role("super_waifus")
@commands.check(is_super_channel)
async def invite(ctx, *, reason):
    """Create a one time use invite for the specified person/reason."""
    welcome_channel = get_channel("welcome_and_rules")
    super_waifu_chat = get_channel("super_waifu_chat")
    invite = await welcome_channel.create_invite(max_age=86400, max_uses=2, temporary=False, unique=True, reason=reason)
    store_invite_details(invite, ctx.author, reason)
    reply = f"{ctx.author.mention} created an invite with reason: '{reason}'.\n<{invite.url}>"
    await super_waifu_chat.send(reply)
    return
    
@bot.command(hidden=True)
@commands.has_role("super_waifus")
@commands.check(is_super_channel)
async def deletequote(ctx, id: int):
    """Delete a quote by ID (second half of `!inspire` file name)"""
    guild = get_guild()
    if not quote_exists(id):
        reply = "I can't find that quote in the database."
        await ctx.send(reply)
        return
    quote = delete_quote(id)
    author = guild.get_member(int(quote[3]))
    stored_by = guild.get_member(int(quote[5]))
    text = quote[7]
    if not quote_exists(id):
        reply = f"That quote is history. For the record, it was from {author}, stored by {stored_by}, and said:\n\n\"{text}\""
        await ctx.send(reply)
    return

@bot.command(hidden=True)
@commands.has_role("admins")
@commands.check(is_super_channel)
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
@commands.has_role("admins")
@commands.check(is_super_channel)
async def die(ctx):
    """Kill my currently running instance. I won't forget this."""
    reply = random.choice(strings['last_words'])
    await ctx.send(reply)
    exit(0)                
    return

global block_noobs
block_noobs = False
log.basicConfig(format="[%(asctime)s] [%(levelname)s] %(message)s", level=log.INFO, stream=sys.stdout)                
config = load_yaml("config.yaml")
strings = load_yaml("strings.yaml")
create_database(config, log)
token = config["discord"]["token"]
bot.run(token)