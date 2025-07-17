import os
import random
import json
import time
import discord
from discord.ext import commands
from discord import app_commands

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = discord.Object(id=1328299328225148969)  # ← あなたのサーバーID
IMAGE_FOLDER = "./images"
POINT_FILE = "./data/points.json"
ITEM_FILE = "./data/items.json"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# データ読み書き
def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# 起動時コマンド同期
@bot.event
async def on_ready():
    await bot.tree.sync(guild=GUILD_ID)
    print(f"✅ Bot is ready: {bot.user}")

# /login（12時間に1回、500ポイント）
@bot.tree.command(name="login", description="12時間に1回500ポイント獲得", guild=GUILD_ID)
async def login(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    points = load_json(POINT_FILE)
    now = time.time()
    last_time = points.get(user_id, {}).get("last_login", 0)

    if now - last_time < 43200:  # 12時間
        remaining = int((43200 - (now - last_time)) // 60)
        await interaction.response.send_message(f"🕒 まだログインできません。あと {remaining} 分後に再試行できます。", ephemeral=True)
        return

    points.setdefault(user_id, {"point": 0})
    points[user_id]["point"] += 500
    points[user_id]["last_login"] = now
    save_json(POINT_FILE, points)

    await interaction.response.send_message("✅ 500ポイントを獲得しました！", ephemeral=True)

# /gacha（1000ポイント消費）
@bot.tree.command(name="gacha", description="1000ポイントでガチャを引く", guild=GUILD_ID)
async def gacha(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    points = load_json(POINT_FILE)
    items = load_json(ITEM_FILE)

    points.setdefault(user_id, {"point": 0})
    if points[user_id]["point"] < 1000:
        await interaction.response.send_message("❌ ポイントが足りません（1000必要）", ephemeral=True)
        return

    image_files = [f for f in os.listdir(IMAGE_FOLDER) if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))]
    if not image_files:
        await interaction.response.send_message("❌ 画像ファイルが見つかりません", ephemeral=True)
        return

    chosen = random.choice(image_files)
    image_path = os.path.join(IMAGE_FOLDER, chosen)

    # ポイント減算
    points[user_id]["point"] -= 1000
    save_json(POINT_FILE, points)

    # アイテム履歴に記録
    items.setdefault(user_id, [])
    items[user_id].append(chosen)
    save_json(ITEM_FILE, items)

    await interaction.response.send_message(f"🎉 ガチャ結果: `{chosen}`", file=discord.File(image_path))

# /addpoint（管理者のみ）
@bot.tree.command(name="addpoint", description="ポイントを付与します（管理者専用）", guild=GUILD_ID)
@app_commands.describe(user="対象ユーザー", amount="付与ポイント")
async def addpoint(interaction: discord.Interaction, user: discord.User, amount: int):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("🚫 あなたにはこのコマンドを使う権限がありません", ephemeral=True)
        return

    points = load_json(POINT_FILE)
    uid = str(user.id)
    points.setdefault(uid, {"point": 0})
    points[uid]["point"] += amount
    save_json(POINT_FILE, points)

    await interaction.response.send_message(f"✅ {user.name} に {amount} ポイントを付与しました！")

# /item（引いた画像一覧表示）
@bot.tree.command(name="item", description="これまで引いたアイテムを確認", guild=GUILD_ID)
async def item(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    items = load_json(ITEM_FILE)
    owned = items.get(user_id, [])

    if not owned:
        await interaction.response.send_message("🎒 所持アイテムがありません。まずはガチャを引こう！", ephemeral=True)
        return

    latest_items = owned[-10:]  # 最新10件

    class ItemButton(discord.ui.Button):
        def __init__(self, file_name: str):
            super().__init__(
                label=file_name,
                style=discord.ButtonStyle.primary,
                custom_id=f"{file_name}-{random.randint(1000, 9999)}"
            )
            self.file_name = file_name

        async def callback(self, interaction: discord.Interaction):
            image_path = os.path.join(IMAGE_FOLDER, self.file_name)
            if os.path.exists(image_path):
                await interaction.response.send_message(
                    content=f"🖼️ `{self.file_name}` を表示します",
                    file=discord.File(image_path),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message("❌ ファイルが見つかりませんでした", ephemeral=True)

    class ItemView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            for item in latest_items:
                self.add_item(ItemButton(item))

    await interaction.response.send_message(
        content="🎁 あなたの所持アイテム一覧（最新10件）：\n下のボタンから画像を表示できます",
        view=ItemView(),
        ephemeral=True
    )


# 起動
bot.run(TOKEN)
