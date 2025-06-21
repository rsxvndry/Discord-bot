from dotenv import load_dotenv
import os
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
import requests
from bs4 import BeautifulSoup
from flask import Flask
from threading import Thread
from discord.ext.commands import cooldown, BucketType, CommandOnCooldown
import time  # ✅ Added for small delay before bot start

# Load token from .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# ✅ Flask web server to keep Replit alive
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_webserver():
    app.run(host='0.0.0.0', port=3000)

def keep_alive():
    t = Thread(target=run_webserver)
    t.start()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Constants
OWNER_ROLE_NAME = "Owner"
TICKET_PANEL_CHANNEL_ID = 1385199205248794705
TIKTOK_USERNAME = "rsx.vndry"
TIKTOK_CHANNEL_ID = 1385195617529102377
PING_EVERYONE = "@everyone"
last_video_url = None
message_counts = {}

# Ticket button view
class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="Atidaryti tiketą", style=discord.ButtonStyle.green, custom_id="open_ticket"))

@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
    channel = bot.get_channel(TICKET_PANEL_CHANNEL_ID)
    if channel:
        try:
            await channel.send("Atidaryk tiketą, kad gauti pagalbą.", view=TicketView())
        except Exception as e:
            print(f"Error sending ticket panel message: {e}")
    else:
        print(f"Channel with ID {TICKET_PANEL_CHANNEL_ID} not found")
    check_tiktok_video.start()

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        if interaction.data.get("custom_id") == "open_ticket":
            guild = interaction.guild
            author = interaction.user
            existing = discord.utils.get(guild.channels, name=f"ticket-{author.id}")
            if existing:
                await interaction.response.send_message(f"Jūs jau turite atidarytą tiketą: {existing.mention}", ephemeral=True)
                return
            owner_role = discord.utils.get(guild.roles, name=OWNER_ROLE_NAME)
            if not owner_role:
                await interaction.response.send_message("Owner rolė nerasta. Susisiekite su administratoriumi.", ephemeral=True)
                return
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
            ticket_channel = await guild.create_text_channel(f"ticket-{author.id}", overwrites=overwrites)
            await ticket_channel.send(f"{author.mention} Jūsų tiketas sukurtas! Rašykite čia savo klausimą.")
            await interaction.response.send_message(f'Tiketas sukurtas: {ticket_channel.mention}', ephemeral=True)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    user_id = message.author.id
    message_counts[user_id] = message_counts.get(user_id, 0) + 1
    if bot.user in message.mentions:
        await message.channel.send("Sveikas, kaip tau galėčiau padėti!")
    await bot.process_commands(message)

@bot.command()
async def rules(ctx):
    embed = discord.Embed(title="📜 Taisyklės",
                          description="1. Gerbk kitus.\n2. Jokio spam.\n3. Naudokite bilietų sistemą pagalbai gauti.",
                          color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command()
async def supplier(ctx):
    message = (
        "# 🔥 Best 1:1 suppliers\n\n"
        "**All vendors can be accessed for 30€**\n\n"
        "10€ - Airpod Vendor\n"
        "20€ - Dyson Hair Drier Vendor\n"
        "10€ - Moissanite Watch Vendor\n"
        "… and more!\n\n"
        "📩 Open a ticket to buy <#1385199916187385957>"
    )
    await ctx.send(message)

@bot.command()
async def about(ctx):
    embed = discord.Embed(
        title="💼📦 Apie MarketSupplies",
        description=(
            "Sveikas atvykęs į **MarketSupplies** – vietą, kur susitinka tikrieji perpardavimo entuziastai! 🛍️\n"
            "📩 Nori pirkti? Atidaryk bilietą čia: <#1385199916187385957>\n"
            "📚 Nepamiršk perskaityti taisyklių: <#1385195758013251684>"
        ),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command()
async def membercount(ctx):
    await ctx.send(f"👥 Serveryje yra **{ctx.guild.member_count}** narių.")

@bot.command()
async def messages(ctx):
    count = message_counts.get(ctx.author.id, 0)
    await ctx.send(f"{ctx.author.mention}, jūs parašėte {count} žinučių nuo tada, kai botas įjungtas!")

@bot.command()
@commands.has_role("Owner")
async def say(ctx, *, message):
    await ctx.message.delete()
    await ctx.send(message)

@bot.command()
@commands.has_role("Owner")
async def clear(ctx, amount: int):
    if amount < 1:
        await ctx.send("Please specify a number greater than 0.")
        return
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Išvalyta {len(deleted)-1} žinutės.", delete_after=5)

@bot.command()
@cooldown(1, 86400, BucketType.default)
async def boosters(ctx):
    try:
        boosters = [m.mention for m in ctx.guild.members if m.premium_since]
        if boosters:
            await ctx.send(f"🚀 **Serverio boostintojai:**\n" + "\n".join(boosters))
        else:
            await ctx.send("🚫 Šiuo metu niekas neboostina serverio.")
    except CommandOnCooldown as e:
        h = int(e.retry_after // 3600)
        m = int((e.retry_after % 3600) // 60)
        s = int(e.retry_after % 60)
        await ctx.send(f"⏳ Komanda ribota. Bandyk po {h}h {m}m {s}s.")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandOnCooldown):
        h = int(error.retry_after // 3600)
        m = int((error.retry_after % 3600) // 60)
        s = int(error.retry_after % 60)
        await ctx.send(f"⏳ Ši komanda turi laukimo laiką. Bandyk vėl po {h}h {m}m {s}s.")
    else:
        raise error

@bot.event
async def on_member_join(member):
    role = discord.utils.get(member.guild.roles, name="Member")
    if role:
        await member.add_roles(role)
        print(f"Assigned 'Member' role to {member.name}")

@bot.command()
@commands.has_role("Owner")
async def assign(ctx, member: discord.Member, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send(f"Rolė `{role_name}` nerasta.")
        return
    try:
        await member.add_roles(role)
        await ctx.send(f"Rolė `{role_name}` priskirta vartotojui {member.mention}.")
    except discord.Forbidden:
        await ctx.send("Neturiu teisių priskirti šią rolę.")
    except Exception as e:
        await ctx.send(f"Ivyko klaida: {e}")

@bot.command()
@commands.has_role("Owner")
async def remove(ctx, member: discord.Member, role: discord.Role):
    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"✅ Removed the role **{role.name}** from {member.mention}.")
    else:
        await ctx.send(f"⚠️ {member.mention} does not have the role **{role.name}**.")

@tasks.loop(minutes=5)
async def check_tiktok_video():
    global last_video_url
    channel = bot.get_channel(TIKTOK_CHANNEL_ID)
    if not channel:
        print(f"Discord channel {TIKTOK_CHANNEL_ID} not found")
        return
    try:
        url = f"https://www.tiktok.com/@{TIKTOK_USERNAME}"
        headers = { "User-Agent": "Mozilla/5.0" }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch TikTok page, status code: {response.status_code}")
            return
        soup = BeautifulSoup(response.text, 'html.parser')
        videos = soup.find_all('a', href=True)
        video_links = [a['href'] for a in videos if "/video/" in a['href']]
        if not video_links:
            print("No videos found.")
            return
        newest = video_links[0]
        if newest != last_video_url:
            last_video_url = newest
            await channel.send(f"{PING_EVERYONE} Naujas video! Pažiūrėkite:\n{newest}")
    except Exception as e:
        print(f"TikTok check failed: {e}")

# ✅ Launch web server & bot
if __name__ == "__main__":
    keep_alive()
    time.sleep(1)  # optional small delay
    bot.run(TOKEN)
