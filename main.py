from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from database import init_db, get_player, update_player, nickname_exists, get_connection

app = FastAPI()

ALLOWED_GROUPS = ["الساحة", "قروب الحجر", "قروب الغابة", "قروب الجليد"]
REGISTRATION_GROUP = "الساحة"
KINGDOMS = {
    "الحجر": "قروب الحجر",
    "الغابة": "قروب الغابة",
    "الجليد": "قروب الجليد"
}
FACEBOOK_GROUP_LINK = "^#_=^<=;$<$;&$"

def reply(messages):
    return JSONResponse(content={"replies": [{"message": m} for m in messages]})

def no_reply():
    return JSONResponse(content={"replies": []})

@app.on_event("startup")
async def startup():
    init_db()

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
    except:
        return no_reply()

    query = data.get("query", {})
    sender = query.get("sender", "").strip()
    message = query.get("message", "").strip()
    is_group = query.get("isGroup", False)
    group_participant = query.get("groupParticipant", "").strip()

    if not is_group:
        return no_reply()

    actual_group = sender
    actual_sender = group_participant

    if actual_group not in ALLOWED_GROUPS:
        return no_reply()

    player = get_player(actual_sender)

    if actual_group == REGISTRATION_GROUP:
        return await handle_sahaa(actual_sender, message, player)
    else:
        return await handle_kingdom(actual_sender, message, player, actual_group)


async def handle_sahaa(sender, message, player):
    if player and player["status"] == "active":
        if message == "تسجيل":
            return reply([f"أنت مسجل مسبقاً ✅\nلقبك: {player['nickname']}"])
        if message == "ملفي":
            return reply([
                f"⚔️ الملف الشخصي\n"
                f"━━━━━━━━━━━━━━\n"
                f"اللقب : {player['nickname']}\n"
                f"المملكة : {player['kingdom']}\n"
                f"الكوينز : {player['coins']} 🪙\n"
                f"نقاط الحياة : {player['hp']} ❤️"
            ])
        return no_reply()

    if player and player["status"] in ("pending", "pending_kingdom"):
        return await handle_registration_steps(sender, message, player)

    if message == "تسجيل":
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO players (sender, nickname, status, step) VALUES (?, '', 'pending', 'awaiting_nickname')",
            (sender,)
        )
        conn.commit()
        conn.close()
        return reply(["مرحباً بك في عالم الممالك! ⚔️\nمن فضلك اكتب لقبك:"])

    return no_reply()


async def handle_registration_steps(sender, message, player):
    step = player.get("step")

    if step == "awaiting_nickname":
        nickname = message.strip()
        if len(nickname) < 2:
            return reply(["❌ اللقب قصير جداً! يجب أن يكون حرفين على الأقل."])
        if len(nickname) > 50:
            return reply(["❌ اللقب طويل جداً! يجب أن لا يتجاوز 50 حرفاً."])
        if nickname.count(" ") > 10:
            return reply(["❌ اللقب يحتوي على فراغات كثيرة جداً!"])
        if nickname_exists(nickname):
            return reply([f"❌ اللقب '{nickname}' مستخدم مسبقاً، اختر لقباً آخر:"])

        update_player(sender, nickname=nickname, step="awaiting_confirm")
        return reply([
            f"هل أنت متأكد من استخدام هذا اللقب؟\n\n"
            f"『 {nickname} 』\n\n"
            f"اكتب نعم للمواصلة\n"
            f"اكتب تعديل للتعديل"
        ])

    elif step == "awaiting_confirm":
        if message == "نعم":
            update_player(sender, step="awaiting_group_join")
            return reply([
                f"رجاءاً انضم للمجموعة الرسمية للنظام 👇\n\n"
                f"{FACEBOOK_GROUP_LINK}\n\n"
                f"اكتب تم بعد الانضمام ✅"
            ])
        elif message == "تعديل":
            update_player(sender, nickname="", step="awaiting_nickname")
            return reply(["حسناً! من فضلك اكتب لقبك من جديد:"])
        else:
            return reply(["اكتب نعم للمواصلة أو تعديل للتعديل."])

    elif step == "awaiting_group_join":
        if message == "تم":
            update_player(sender, step="awaiting_kingdom")
            return reply([
                "رجاءاً اختر إحدى الممالك التالية:\n\n"
                "🪨 الحجر\n"
                "🌿 الغابة\n"
                "❄️ الجليد\n\n"
                "اكتب اسم المملكة التي تريدها:"
            ])
        else:
            return reply([
                f"انضم أولاً للمجموعة الرسمية 👇\n\n"
                f"{FACEBOOK_GROUP_LINK}\n\n"
                f"ثم اكتب تم ✅"
            ])

    elif step == "awaiting_kingdom":
        kingdom_name = message.strip()
        if kingdom_name not in KINGDOMS:
            return reply([
                "❌ اسم مملكة غير صحيح!\n\n"
                "اختر من:\n"
                "🪨 الحجر\n"
                "🌿 الغابة\n"
                "❄️ الجليد"
            ])
        update_player(sender, kingdom=kingdom_name, step=None, status="pending_kingdom")
        return reply([
            f"✅ تم اختيار مملكة {kingdom_name}!\n\n"
            f"سيتم إضافتك للمملكة من طرف الإمبراطور قريباً ⚔️\n"
            f"كن على أهبة الاستعداد يا {player['nickname']}!"
        ])

    return no_reply()


async def handle_kingdom(sender, message, player, group_name):
    if not player or player["status"] == "pending":
        return reply([
            "⚠️ تم اكتشاف دخيل غير منتمٍ للنظام!\n\n"
            "عليك الخروج من هذا القروب والدخول للساحة ثم اختيار مملكتك."
        ])

    expected_group = KINGDOMS.get(player.get("kingdom", ""))

    if group_name != expected_group:
        return reply([
            f"⚠️ انذار دخيل!\n\n"
            f"اللقب : {player['nickname']}\n"
            f"مملكته : {player['kingdom']}\n\n"
            f"هذا ليس مكانك! توجه لمملكتك الصحيحة."
        ])

    if player["status"] == "pending_kingdom":
        update_player(sender, status="active")
        player = get_player(sender)

    if message == "تسجيل":
        return reply([f"أنت مسجل مسبقاً ✅\nلقبك: {player['nickname']}"])

    if message == "ملفي":
        return reply([
            f"⚔️ الملف الشخصي\n"
            f"━━━━━━━━━━━━━━\n"
            f"اللقب : {player['nickname']}\n"
            f"المملكة : {player['kingdom']}\n"
            f"الكوينز : {player['coins']} 🪙\n"
            f"نقاط الحياة : {player['hp']} ❤️"
        ])

    return no_reply()
