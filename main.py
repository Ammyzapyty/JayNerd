import discord
from discord.ext import commands, tasks
from pymongo import MongoClient 
from datetime import datetime, timedelta
import os
import certifi
from keep_alive import keep_alive
from dotenv import load_dotenv
load_dotenv()

# ================= การตั้งค่า ID =================
# แนะนำให้ดึงจาก Environment Variable เพื่อความยืดหยุ่น หรือใส่ตรงๆ แบบเดิมก็ได้ครับ
INPUT_CHANNEL_ID = int(os.environ.get("INPUT_CHANNEL_ID", 1526962068211761304))
ANNOUNCE_CHANNEL_ID = int(os.environ.get("ANNOUNCE_CHANNEL_ID", 1526962139145834586))

# ================= การตั้งค่า MongoDB =================
MONGO_URL = os.environ.get("MONGO_URL")

# ใช้ certifi เพื่อจัดการเรื่อง SSL Certificate บน Cloud 
cluster = MongoClient(MONGO_URL, tlsCAFile=certifi.where())
db = cluster["discord_bot"] 
collection = db["homework"] 
# =================================================

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ ล็อกอินสำเร็จในชื่อ {bot.user}")
    if not check_homework.is_running():
        check_homework.start()

# คำสั่งเพิ่มการบ้าน
@bot.command(name="addhw")
async def add_homework(ctx, subject: str, due_date: str, *, details: str):
    if ctx.channel.id != INPUT_CHANNEL_ID:
        return

    now = datetime.now()
    try:
        parsed_date = datetime.strptime(due_date, "%d/%m")
        due_datetime = parsed_date.replace(year=now.year)
        
        if due_datetime < now - timedelta(days=15):
            due_datetime = due_datetime.replace(year=now.year + 1)
            
        save_format = due_datetime.strftime("%Y-%m-%d")
        display_format = due_datetime.strftime("%d/%m/%Y")
        
    except ValueError:
        embed_error = discord.Embed(
            title="⚠️ รูปแบบวันที่ไม่ถูกต้อง", 
            description="กรุณาใช้ วัน/เดือน (เช่น `20/07`)", 
            color=discord.Color.red()
        )
        await ctx.send(embed=embed_error)
        return

    collection.insert_one({
        "subject": subject,
        "due_date": save_format,
        "display_date": display_format,
        "details": details,
        "notified": False
    })
    
    embed_success = discord.Embed(
        title="✅ บันทึกการบ้านเรียบร้อย!",
        color=discord.Color.green()
    )
    embed_success.add_field(name="📖 วิชา", value=subject, inline=False)
    embed_success.add_field(name="📝 รายละเอียด", value=details, inline=False)
    embed_success.add_field(name="🗓️ กำหนดส่ง", value=display_format, inline=False)
    
    await ctx.send(embed=embed_success)

# ลูปตรวจสอบการบ้าน
@tasks.loop(hours=1) 
async def check_homework():
    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if not channel:
        return

    today = datetime.now()
    pending_hws = collection.find({"notified": False})

    for hw in pending_hws:
        due_date = datetime.strptime(hw["due_date"], "%Y-%m-%d")
        days_left = (due_date - today).days

        if 0 <= days_left <= 2:
            embed = discord.Embed(
                title="⏰ ประกาศเตือน: มีการบ้านใกล้ถึงกำหนดส่ง!", 
                color=discord.Color.red()
            )
            embed.add_field(name="วิชา", value=hw["subject"], inline=False)
            embed.add_field(name="รายละเอียด", value=hw["details"], inline=False)
            show_date = hw.get("display_date", hw["due_date"])
            embed.add_field(name="กำหนดส่ง", value=show_date, inline=False)
            
            await channel.send(embed=embed)
            collection.update_one({"_id": hw["_id"]}, {"$set": {"notified": True}})

# คำสั่งลิสต์การบ้าน
@bot.command(name="listhw", aliases=["hwlist", "การบ้าน"])
async def list_homework(ctx):
    all_hw = list(collection.find())
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) 
    pending_hw = []
    
    for hw in all_hw:
        due_date = datetime.strptime(hw["due_date"], "%Y-%m-%d")
        if due_date >= today:
            pending_hw.append(hw)
            
    if not pending_hw:
        embed_empty = discord.Embed(
            title="🎉 ไม่มีกานบ้านค้างส่ง!",
            description="สวยจัด ตอนนี้ไม่มีการบ้านที่ต้องส่งเลย มาๆเล่นเกม",
            color=discord.Color.from_rgb(46, 204, 113) 
        )
        await ctx.send(embed=embed_empty)
        return
        
    pending_hw.sort(key=lambda x: datetime.strptime(x["due_date"], "%Y-%m-%d"))
    embed = discord.Embed(title="📋 รายการการบ้านที่ยังไม่ถึงกำหนดส่ง", color=discord.Color.blue())
    
    for i, hw in enumerate(pending_hw, start=1):
        show_date = hw.get("display_date", hw["due_date"])
        embed.add_field(name=f"{i}. 📖 {hw['subject']} (ส่ง: {show_date})", value=f"📝 {hw['details']}", inline=False)
        
    await ctx.send(embed=embed)

# คำสั่งลบการบ้าน
@bot.command(name="delhw", aliases=["ลบการบ้าน"])
async def delete_homework(ctx, index: int):
    all_hw = list(collection.find())
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) 
    pending_hw = []
    
    for hw in all_hw:
        due_date = datetime.strptime(hw["due_date"], "%Y-%m-%d")
        if due_date >= today:
            pending_hw.append(hw)
            
    if not pending_hw:
        embed_empty = discord.Embed(
            title="❌ ไม่พบข้อมูลการบ้าน",
            description="ตอนนี้ไม่มีการบ้านในระบบให้ลบ",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed_empty)
        return
        
    pending_hw.sort(key=lambda x: datetime.strptime(x["due_date"], "%Y-%m-%d"))
    
    if index < 1 or index > len(pending_hw):
        embed_error = discord.Embed(
            title="⚠️ ลำดับไม่ถูกต้อง",
            description=f"ไม่พบการบ้านลำดับที่ **{index}** นะ (ตอนนี้มีการบ้านทั้งหมด {len(pending_hw)} งาน)",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed_error)
        return
        
    target_hw = pending_hw[index - 1]
    collection.delete_one({"_id": target_hw["_id"]})
    
    embed_success = discord.Embed(
        title="🗑️ ลบการบ้านเรียบร้อย!",
        description=f"ลบการบ้านวิชา **{target_hw['subject']}** ออกจากระบบแล้ว",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed_success)

bot.remove_command("help")

# คำสั่ง !help
@bot.command(name="help", aliases=["วิธีใช้"])
async def custom_help(ctx):
    embed = discord.Embed(
        title="📚 คู่มือการใช้งานเจย์ให้จดงาน",
        description="รวบรวมคำสั่งทั้งหมดสำหรับจัดการการบ้าน",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="📝 `!addhw <ชื่อวิชา> <วัน/เดือน> <รายละเอียด>`",
        value="**ใช้ทำอะไร:** บันทึกการบ้านใหม่\n**เงื่อนไข:** ต้องพิมพ์ในช่องรับคำสั่งที่ตั้งไว้เท่านั้น",
        inline=False
    )
    embed.add_field(
        name="📋 `!listhw` หรือ `!การบ้าน`",
        value="**ใช้ทำอะไร:** ดูรายการการบ้านทั้งหมดที่ยังไม่ถึงกำหนดส่ง\n**เงื่อนไข:** สามารถพิมพ์ในช่องแชทไหนก็ได้",
        inline=False
    )
    embed.add_field(
        name="🗑️ `!delhw <ลำดับ>` หรือ `!ลบการบ้าน <ลำดับ>`",
        value="**ใช้ทำอะไร:** ลบการบ้านที่พิมพ์ผิดออกจากลิสต์\n**เงื่อนไข:** ดูลำดับที่ได้จากคำสั่ง `!listhw` ก่อน\n**ตัวอย่าง:** `!delhw 1`",
        inline=False
    )
    embed.set_footer(text="💡 เจย์จะแจ้งเตือนอัตโนมัติล่วงหน้า 2 วันก่อนถึงกำหนดส่ง")
    await ctx.send(embed=embed)

# เปิดใช้งานเซิร์ฟเวอร์ Flask เพื่อให้ Render ตรวจสอบสถานะได้
keep_alive() 

TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)
