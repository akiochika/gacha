import os
import random
import discord
from discord.ext import commands
from discord import app_commands

# 環境変数からトークン取得（Railwayの環境変数に設定しておくこと）
TOKEN = os.getenv("DISCORD_TOKEN")

# あなたのサーバーID
GUILD_ID = discord.Object(id=1395336553278083143)

# 画像フォルダのパス（ローカル）
IMAGE_FOLDER = "./images"

# Botの基本設定
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# 起動時にコマンドを同期（即反映）
@bot.event
async def on_ready():
    await bot.tree.sync(guild=GUILD_ID)
    print(f"✅ Bot is ready! Logged in as {bot.user}")

# /gacha コマンド定義
@bot.tree.command(name="gacha", description="ローカル画像からガチャを引きます", guild=GUILD_ID)
async def gacha_command(interaction: discord.Interaction):
    # フォルダ内の画像ファイル一覧取得
    image_files = [f for f in os.listdir(IMAGE_FOLDER) if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))]

    if not image_files:
        await interaction.response.send_message("❌ ガチャ画像が見つかりません。")
        return

    # ランダムに1枚選んで送信
    chosen_image = random.choice(image_files)
    image_path = os.path.join(IMAGE_FOLDER, chosen_image)

    await interaction.response.send_message("🎁 ガチャ結果はこちら！", file=discord.File(image_path))

# Bot起動
bot.run(TOKEN)
