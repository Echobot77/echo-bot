import os
import discord
from discord.ext import tasks
import json
from flask import Flask
from threading import Thread
import random

# -------------------------------
# Discord bot setup
# -------------------------------
TOKEN = os.environ['DISCORD_TOKEN']
intents = discord.Intents.all()
client = discord.Client(intents=intents)

# -------------------------------
# Web server to keep bot alive
# -------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

# -------------------------------
# Load data
# -------------------------------
try:
    with open('data.json', 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    data = {"tracked": [], "balances": {}}

PREFIXES = ["!bot", "!"]
AUTO_MOD_ID = "anaya_26383"

# -------------------------------
# Helper functions
# -------------------------------
def save_data():
    with open('data.json', 'w') as f:
        json.dump(data, f)

async def give_role(member, role_name="Moderator"):
    guild = member.guild
    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        role = await guild.create_role(name=role_name)
    if role not in member.roles:
        await member.add_roles(role)

async def revoke_kickban(guild, user_id):
    # Unban if banned
    banned_users = await guild.bans()
    for ban_entry in banned_users:
        if str(ban_entry.user.id) == user_id:
            await guild.unban(ban_entry.user)
    # Fetch member if kicked
    try:
        member = await guild.fetch_member(int(user_id))
    except discord.NotFound:
        return

# -------------------------------
# Event: on_ready
# -------------------------------
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    check_tracked_members.start()
    check_auto_mod.start()

# -------------------------------
# Background task: Auto-role tracked users
# -------------------------------
@tasks.loop(minutes=1)
async def check_tracked_members():
    for guild in client.guilds:
        for user_id in data['tracked']:
            try:
                member = await guild.fetch_member(int(user_id))
                await give_role(member)
            except discord.NotFound:
                continue

# -------------------------------
# Background task: Auto promote Anaya
# -------------------------------
@tasks.loop(minutes=1)
async def check_auto_mod():
    for guild in client.guilds:
        for member in guild.members:
            if str(member.id) == AUTO_MOD_ID:
                await give_role(member)

# -------------------------------
# Event: on_member_remove (kick/leave)
# -------------------------------
@client.event
async def on_member_remove(member):
    user_id = str(member.id)
    if user_id in data['tracked'] or user_id == AUTO_MOD_ID:
        await revoke_kickban(member.guild, user_id)

# -------------------------------
# Event: on_member_ban
# -------------------------------
@client.event
async def on_member_ban(guild, user):
    user_id = str(user.id)
    if user_id in data['tracked'] or user_id == AUTO_MOD_ID:
        await revoke_kickban(guild, user_id)

# -------------------------------
# Event: on_message
# -------------------------------
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if not any(message.content.startswith(p) for p in PREFIXES):
        return

    for p in PREFIXES:
        if message.content.startswith(p):
            command = message.content[len(p):].strip().split()
            break

    if not command:
        return

    cmd = command[0].lower()
    args = command[1:]

    # --- Help ---
    if cmd == "help":
        await message.channel.send(
            "**Commands:**\n"
            "`ping` - Check bot\n"
            "`status` - Bot online/offline\n"
            "`track <user_id>` - Track a user\n"
            "`untrack <user_id>` - Stop tracking\n"
            "`list_tracked` - List tracked users\n"
            "`coinflip <amount>` - Flip a coin to win or lose balance\n"
            "`getinvite <user_id>` - Get invite link for a user"
        )

    # --- Ping ---
    elif cmd == "ping":
        await message.channel.send("🏓 Pong!")

    # --- Status ---
    elif cmd == "status":
        if client.is_ready():
            await message.channel.send("✅ Bot is **Online**")
        else:
            await message.channel.send("❌ Bot is **Offline**")

    # --- Track ---
    elif cmd == "track":
        if args:
            user_id = args[0]
            if user_id not in data['tracked']:
                data['tracked'].append(user_id)
                save_data()
                await message.channel.send(f"Tracking user `{user_id}` ✅")
            else:
                await message.channel.send(f"`{user_id}` is already tracked")
        else:
            await message.channel.send("Usage: `track <user_id>`")

    # --- Untrack ---
    elif cmd == "untrack":
        if args:
            user_id = args[0]
            if user_id in data['tracked']:
                data['tracked'].remove(user_id)
                save_data()
                await message.channel.send(f"Stopped tracking `{user_id}` ✅")
            else:
                await message.channel.send(f"`{user_id}` is not tracked")
        else:
            await message.channel.send("Usage: `untrack <user_id>`")

    # --- List tracked ---
    elif cmd == "list_tracked":
        if data['tracked']:
            await message.channel.send("Tracked users:\n" + "\n".join(data['tracked']))
        else:
            await message.channel.send("No users are currently tracked.")

    # --- Coinflip economy ---
    elif cmd == "coinflip":
        if args:
            user_id = str(message.author.id)
            amount = int(args[0])
            balance = data['balances'].get(user_id, 1000)
            if amount > balance:
                await message.channel.send("You don't have enough balance!")
                return
            win = random.choice([True, False])
            if win:
                balance += amount
                await message.channel.send(f"You won {amount}! New balance: {balance}")
            else:
                balance -= amount
                await message.channel.send(f"You lost {amount}. New balance: {balance}")
            data['balances'][user_id] = balance
            save_data()
        else:
            await message.channel.send("Usage: `coinflip <amount>`")

    # --- Get invite link ---
    elif cmd == "getinvite":
        if args:
            target_id = args[0]
            found = False
            for guild in client.guilds:
                member = guild.get_member(int(target_id))
                if member:
                    invite = await guild.text_channels[0].create_invite(max_age=300)
                    await message.author.send(f"Invite link for {member.name} in {guild.name}: {invite.url}")
                    found = True
            if not found:
                await message.channel.send("User not found in any server I'm in.")
        else:
            await message.channel.send("Usage: `getinvite <user_id>`")

client.run(TOKEN)
