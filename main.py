# requirements: discord.py==2.3.*
import re
import discord
from discord.ext import commands

TOKEN = "DISCORD_TOKEN"  # Railwayの環境変数で渡すのが安全

INTENTS = discord.Intents.default()
INTENTS.members = True  # ニックネーム編集・取得に必要

bot = commands.Bot(command_prefix="!", intents=INTENTS)

# 「末尾の [123pt]」を見つける正規表現
PT_SUFFIX_RE = re.compile(r"\s*\[(\d+)pt\]\s*$")

INITIAL_POINTS = 500
NICK_MAX = 32  # Discordのニックネーム最大文字数


def extract_points_and_basename(name_or_nick: str) -> tuple[int | None, str]:
    """
    'Akito [500pt]' -> (500, 'Akito')
    'Akito'         -> (None, 'Akito')
    """
    m = PT_SUFFIX_RE.search(name_or_nick)
    if not m:
        return None, name_or_nick
    pts = int(m.group(1))
    base = PT_SUFFIX_RE.sub("", name_or_nick)  # サフィックスを除去
    return pts, base


def build_nickname(base: str, points: int) -> str:
    """
    ベース名 + ' [xxxpt]' を32文字に収まるように組み立て。
    長い場合はベース名をトリム。
    """
    suffix = f" [{points}pt]"
    room = NICK_MAX - len(suffix)
    if room < 1:
        # ありえないほど大きいポイント桁数対策（安全側で末尾だけ）
        return suffix.strip()[:NICK_MAX]
    trimmed_base = base[:room]
    return trimmed_base + suffix


async def get_points(member: discord.Member) -> int:
    """
    メンバーのニックネーム(or名前)からポイントを取得。
    無ければ INITIAL_POINTS を返す（その場では書き換えない）。
    """
    name = member.nick or member.name
    pts, _ = extract_points_and_basename(name)
    return pts if pts is not None else INITIAL_POINTS


async def set_points(member: discord.Member, points: int) -> None:
    """
    メンバーのニックネーム末尾に [xxxpt] を付けて保存（＝永続化）。
    既存の [xxxpt] は置き換える。権限エラーは握りつぶさず知らせる。
    """
    current = member.nick or member.name
    _, base = extract_points_and_basename(current)
    new_nick = build_nickname(base, max(0, points))  # 負数は0で下限カット

    await member.edit(nick=new_nick)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")


@bot.command(name="mypoint")
async def mypoint(ctx: commands.Context):
    p = await get_points(ctx.author)
    await ctx.reply(f"{ctx.author.mention} のポイントは **{p}pt** です！")


@bot.command(name="add")
@commands.has_permissions(manage_nicknames=True)
async def add_points(ctx: commands.Context, member: discord.Member, amount: int):
    """
    例: !add @ユーザー 100  /  !add @ユーザー -50
    """
    try:
        current = await get_points(member)
        newp = current + amount
        await set_points(member, newp)
        await ctx.reply(
            f"{member.mention} に **{amount}pt** 反映しました。合計 **{max(0, newp)}pt**"
        )
    except discord.Forbidden:
        await ctx.reply("⚠️ ニックネームを変更する権限がありません（Botのロール位置/権限を確認）。")
    except discord.HTTPException as e:
        await ctx.reply(f"⚠️ ニックネーム更新に失敗しました: {e}")


@bot.command(name="fixnick")
async def fix_nick(ctx: commands.Context, member: discord.Member = None):
    """
    指定ユーザー（未指定なら自分）のニックネームに [xxxpt] が無い/壊れている場合に修復。
    """
    target = member or ctx.author
    try:
        # 現在値を読み取る（無ければ初期500として付与）
        p = await get_points(target)
        await set_points(target, p)
        if target == ctx.author:
            await ctx.reply("🔧 あなたのニックネームをポイント表記に修復しました。")
        else:
            await ctx.reply(f"🔧 {target.mention} のニックネームを修復しました。")
    except discord.Forbidden:
        await ctx.reply("⚠️ ニックネームを変更する権限がありません。")
    except discord.HTTPException as e:
        await ctx.reply(f"⚠️ ニックネーム更新に失敗しました: {e}")


@bot.command(name="init_here")
@commands.has_permissions(manage_nicknames=True)
async def init_here(ctx: commands.Context):
    """
    現在のチャンネルのギルド内メンバーをざっとスキャンして、
    [xxxpt] が無い人には初期500ptを付与する簡易初期化。
    """
    guild = ctx.guild
    if not guild:
        return await ctx.reply("ギルド内で実行してください。")

    updated = 0
    failed = 0
    async for member in guild.fetch_members(limit=None):
        if member.bot:
            continue
        name = member.nick or member.name
        pts, _ = extract_points_and_basename(name)
        if pts is None:
            try:
                await set_points(member, INITIAL_POINTS)
                updated += 1
            except Exception:
                failed += 1

    await ctx.reply(f"✅ 初期化完了: 付与 {updated} 人 / 失敗 {failed} 人")


bot.run(TOKEN)
