from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    # ข้อความที่จะแสดงเมื่อเปิดหน้าเว็บ
    return "✅ Bot is running properly!"

def run():
    # ให้ Flask รันบนพอร์ต 8080 (หรือพอร์ตที่ Render กำหนด)
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    # สร้าง Thread เพื่อให้เว็บเซิร์ฟเวอร์ทำงานพร้อมกับบอทได้โดยไม่บล็อกการทำงานกัน
    t = Thread(target=run)
    t.start()