# bot.py
import os
import random
import json
import asyncio

import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv
import datetime as dt

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')


intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
emptyfiletxt = "No questions available. Please add more using the /addq command!"
# https://leovoel.github.io/embed-visualizer


def getrandomline(remove:bool, id:str):
    with open('./files/'+id+'.txt') as infile:
            lines = infile.readlines()
    random_line = random.choice(lines)
    if remove:
        with open('./files/'+id+'.txt', "w") as open_file:
            for line in lines:
                if line.strip("\n") != random_line.strip("\n"):
                    open_file.write(line)
            open_file.seek(0, os.SEEK_END)
            file_size = open_file.tell()
            if (file_size == 0):
                open_file.write(emptyfiletxt)
        if random_line.strip("\n") != emptyfiletxt.strip("\n"):
            with open('./files/'+id+'a.txt', "a") as open_file:
                open_file.write(random_line)
    return random_line

def groupid(guild:int, groupname:str):
    with open('data.json') as f:
        data = json.load(f)
    for i in data:
        if i['guildid'] == guild:
            for j in i['groups']:
                if j['groupname'] == groupname:
                    return j['groupid']
            break
    return 0

def listgroups(guildid:int):
    with open('data.json') as f:
        data = json.load(f)
    allgroups = ""
    for i in data:
        if i['guildid'] == guildid:
            allgroups = "Current groups in this server:\n"
            if not i['groups']:
                return
            for j in i['groups']:
                allgroups = allgroups + "**Group name:** " + j['groupname'] + "\n"
                if j['description'] != "":
                    allgroups = allgroups + "- Description: " + j['description'] + "\n"
                print ("\n")
            break
    if not allgroups:
        allgroups = "This server has no groups."
    return allgroups

# ---------- LOOPED TASKS -----------

@tasks.loop(hours=24)  # every 24 hours
async def question():
    with open('data.json') as f:
        data = json.load(f)
    for guild in client.guilds:
        for i in data:
            if i['guildid'] == guild.id:
                for j in i['groups']:
                    channel = client.get_channel(int(j['channelid']))
                    randomline = getrandomline(True, j['groupid'])
                    if j['roleid'] == "0":
                        print("Sent without role to: (" + i['guildname'] + ", " + j['description'] + ")")
                        await channel.send("**QOTD:** " + randomline)
                    else:
                        role = discord.utils.get(guild.roles, id=int(j['roleid']))
                        print("Sent with role to: (" + i['guildname'] + ", " + j['description'] + ")")
                        await channel.send("**QOTD:** " + randomline + role.mention)
                break
    print("\n")
@question.before_loop
async def wait_until():
    print('waiting...')
    now = dt.datetime.now()
    target_time = dt.datetime(now.year, now.month, now.day, 13)
    if now.hour >= 13:
        target_time += dt.timedelta(days=1)  # If it's already past target hour, wait until the next day
    delta = (target_time - now).total_seconds()
    await asyncio.sleep(delta)

# ---------- COMMANDS -----------

@tree.command(
    name="feed",
    description="Give the pigeon some bread"
    )
async def feed(interaction):
    await interaction.response.send_message("Om nom")

#ADDQ
@tree.command(
    name="addq",
    description="Add a question. Usage: /addq [question] [group]"
    )
async def add_question(interaction, question: str, group: str):
    guild = interaction.guild.id
    id = groupid(guild, group)
    if id == 0:
        await interaction.response.send_message("The given group does not exist.", delete_after=5)
        return    
    else:
        with open('./files/'+id+'.txt', 'r') as cf:
            firstline = cf.readline()
        if firstline == emptyfiletxt:
            open('./files/'+id+'.txt', 'w').close()
        with open('./files/'+id+'.txt', 'a') as open_file:
            open_file.write(question+'\n')
        await interaction.response.send_message("The question has been added.", delete_after=5)

#QOTD
@tree.command(
    name="qotd",
    description="Get a random question. Usage: /qotd [groupname]"
    )
async def manualquestion(interaction, groupname:str):
    guild = interaction.guild.id
    id = groupid(guild, groupname)
    if id == 0:
        await interaction.response.send_message("The given group does not exist.", delete_after=5)
        return
    randomline = getrandomline(False, id)
    await interaction.response.send_message(randomline)

# SETROLE
@tree.command(
    name="setrole",
    description="Set the QOTD role. Usage: /setrole [groupname] [roleid]"
    )
async def set_channel(interaction, groupname:str, roleid: str):
    guild = interaction.guild.id
    with open('data.json') as f:
        found = False
        data = json.load(f)
    for i in data:
        if i['guildid'] == guild:
            for j in i['groups']:
                if j['groupname'] == groupname:
                    found = True
                    j['roleid'] = roleid
                    break
            break
    if not found:
        await interaction.response.send_message("The given group does not exist.", delete_after=5)
    else:
    	with open('data.json', 'w') as fw:
            json.dump(data, fw, indent=4, separators=(',',': '))
            await interaction.response.send_message("Group role has been changed.", delete_after=5)

# ---------- (NEW) MOD COMMANDS -----------

#REMOVE
@tree.command(
    name="removeq",
    description="Remove question. Usage: /removeq [questionnr] [groupname]"
    )
# @app_commands.checks.has_permissions(manage_messages=True)
async def removequestion(interaction, questionnr: int, groupname:str):
    guild = interaction.guild.id
    id = groupid(guild, groupname)
    if id == 0:
        await interaction.response.send_message("The given group does not exist.", delete_after=5)
    with open('./files/'+id+'.txt', "r") as infile:
            lines = infile.readlines()
            remove = infile.readline(questionnr) 
    with open('./files/'+id+'.txt', "w") as open_file:
        for line in lines:
            if line.strip("\n") != remove.strip("\n"):
                open_file.write(line)
    await interaction.response.send_message("Question removed.", delete_after=5)

#ALLQ
@tree.command(
    name="allq",
    description="Show ALL current saved questions. Usage: /allq [groupname]"
    )
# @app_commands.checks.has_permissions(manage_messages=True)
async def all_questions(interaction, groupname:str):
    guild = interaction.guild.id
    id = groupid(guild, groupname)
    if id == 0:
        await interaction.response.send_message("The given group does not exist.", delete_after=5)
    allquestions = "Current saved questions for group " + groupname + ":\n"
    with open('./files/'+id+'.txt') as open_file:
        i = 0
        for line in open_file:
            allquestions = allquestions + str(i) +": " + line
            i = i+1
    await interaction.response.send_message(allquestions)


#RESET
@tree.command(
    name="reset",
    description="Reset the 'answered' questions. Usage: /reset [groupname]."
    )
# @app_commands.checks.has_permissions(manage_messages=True)
async def reset(interaction, groupname: str):
    guild = interaction.guild.id
    id = groupid(guild, groupname)
    if id == 0:
        await interaction.response.send_message("The given group does not exist.", delete_after=5)

    with open('./files/'+id+'a.txt') as f2:
        with open('./files/'+id+'.txt', 'a') as f1:
            f1.write("\n"+ f2.read())
    open('./files/'+id+'a.txt', 'w').close()
    await interaction.response.send_message("Reset done.", delete_after=5)

#ALLGROUPS
@tree.command(
    name="allgroups",
    description="Show all groups in current server. Usage: /allgroups"
    )
async def remove_group(interaction):
    guild = interaction.guild.id
    allgroups = listgroups(guild)
    if not allgroups:
        await interaction.response.send_message("This server currently has no groups.", delete_after=5)
        return
    await interaction.response.send_message(allgroups)

# REMOVEGROUP
@tree.command(
    name="removegroup",
    description="Remove a QOTD group. Usage: /removegroup [groupname]"
    )
# @app_commands.checks.has_permissions(manage_messages=True)
async def remove_group(interaction, groupname: str):

    user = interaction.user
    user.roles 
    guild = interaction.guild.id
    with open('data.json') as f:
        found = False
        data = json.load(f)
    for i in data:
        if i['guildid'] == guild:
            n = 0
            for j in i['groups']:
                if j['groupname'] == groupname:
                    found = True
                    id = j['groupid']
                    del i['groups'][n]
                    break
                n = n+1
            break
    if not found:
        await interaction.response.send_message("The given group does not exist.", delete_after=5)
    else:
        with open('data.json', 'w') as fw:
            json.dump(data, fw, indent=4, separators=(',',': '))
        if os.path.exists('./files/'+id+".txt"):
            os.remove('./files/'+id+".txt")
        if os.path.exists('./files/'+id+"a.txt"):
            os.remove('./files/'+id+"a.txt")
        await interaction.response.send_message("The group has been deleted.", delete_after=5)

#ADDGROUP
@tree.command(
    name="addgroup",
    description="Make a new QOTD group. Usage: /addgroup [groupname] [channelid] [description(optional)]"
    )
async def add_group(interaction, groupname: str, channelid: str, description: str = ""):
    guild = interaction.guild.id
    with open('data.json') as f:
        found = False
        data = json.load(f)
    new_group = {
        "groupid": channelid,
        "channelid": channelid,
        "groupname": groupname,
        "roleid": "0",
        "description": description
        }
    for i in data:
        if i['guildid'] == guild:
            for j in i['groups']:
                if j['groupid'] == channelid:
                    new_group['groupid'] = '%010d' % (int(new_group['groupid']) + 1) 
                    if j['groupname'] == groupname:
                        await interaction.response.send_message("This group already exists.", delete_after=5)
                        return
            found = True
            i['groups'].append(new_group)
            break
    if not found:
        new_guild = {
            "guildid": guild, 
            "guildname": interaction.guild.name,
            "groups": [new_group]
        }
        data.append(new_guild)
    with open('data.json', 'w') as fw:
        json.dump(data, fw, indent=4, separators=(',',': '))
    with open('./files/'+new_group['groupid']+".txt", "w+") as f:
        f.write(emptyfiletxt)
    open('./files/'+new_group['groupid']+"a.txt", "w+")
    await interaction.response.send_message("New QOTD group with name '"+groupname+"' has been made!", delete_after=5)

@tree.command(
    name="help",
    description="Get a summary of the bot's commands.",
    )
async def help(interaction, command: str=None):
    if command is None:
        with open('helpbox.json', 'r') as help_file:
            help_commands = json.load(help_file)
            help_embed = discord.Embed.from_dict(help_commands)

    else:
        help_embed = discord.Embed(title= "/help " + command,
                                    description="Caw! I apologize, I cannot provide any further information :(",
                                    colour=0x00b0f4)
        help_embed.set_footer(text="Use /help [command] to get more info about a specific command!")
    await interaction.channel.send(embed=help_embed)
    await interaction.response.send_message("Help block sent.", delete_after=5)

# ---------- ADMIN COMMANDS -----------

@tree.command(
        name="sync", 
        description="Sync slash commands",
        guild=discord.Object(id=GUILD))
async def sync(interaction):
    if interaction.user.id == 414418635562418179:
        await interaction.response.send_message("Syncing...", delete_after=5)
        await tree.sync()
        print("Command tree synced.")
    else:
        await interaction.response.send_message("You must be the owner to use this command!", delete_after=5)

# ---------- LAUNCH -----------

@client.event
async def on_ready():
    await client.wait_until_ready()
    print(f'{client.user} is connected to the following guilds:')
    for guild in client.guilds:
        if(guild.id == int(GUILD)):
            tree.copy_global_to(guild=discord.Object(id = GUILD))
            await tree.sync(guild=discord.Object(id = GUILD))
            print(f'Synced: {guild.name}(id: {guild.id})')
        else:
            print(f'Non-synced: {guild.name}(id: {guild.id})')
    print("\n")
    question.start()

client.run(TOKEN)