from __future__ import annotations
import re
import os
import csv
import json
import random
import asyncio
import time
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo
from io import StringIO, BytesIO
from dataclasses import dataclass
from collections import defaultdict
from typing import Optional, Dict, List, Iterable, Set, DefaultDict, Tuple, Union, Sequence

import discord
from discord import app_commands
from discord.ext import commands

# --------------------------------------------------------------------------------------------------------------------
# Bot Config
# --------------------------------------------------------------------------------------------------------------------

DISCORD_BOT_TOKEN = ""
GUILD_ID = "504587323577729024"

DEFAULT_TZ = "Europe/Kiev"  # requires tzdata on some systems (esp. Windows)
DATETIME_FORMAT_HINT = "YYYY-MM-DD HH:MM (e.g., 2026-01-02 13:45)"

# --------------------------------------------------------------------------------------------------------------------
# Game Config
# --------------------------------------------------------------------------------------------------------------------

MONOLITH_FACTIONS = {"Monolith", "Noon"}
TRANSITIONED_FACTIONS = {"Noon"}

# Channel IDs
MONOLITH_LOOT_CHANNELS = {1452622206675976242} # "monolith-prayer-site"
STALKER_LOOT_CHANNELS = {1452623240471122053, 1452623201665548361, 1452623566855082055, 1452623345928372275} # "lesser-zone", "cordon", "yantar", "garbage"

MONOLITH_WEAPONS = {"UDP", "Fora230", "M860Monolith", "G37", "M701", "SPSA", "GP3a", "RPG", "Gauss Rifle"}
MONOLITH_ARMOR = {"Monolith Battle Armor", "Exoskeleton", "Improved Exoskeleton"}
STALKER_WEAPONS = {"PTM", "TOZ-34", "Kora", "AKM-74U", "Fora", "M860", "Rhino", "Dnipro", "SVU"}
STALKER_ARMOR = {"OZK Explorer suit", "PSZ-20W Convoy", "Marauder Suit", "Leather Jacket", "Sunrise Suit", "PSZ-5V Guardian of Freedom", "SEVA suit", "PSZ-7 Military Armor", "Berill-5M Armored Suit"}
ATTACHMENTS = {"Silencer", "Tactical Scope"}
ARTIFACTS = {"Jellyfish", "Weird Bolt", "Weird Flower"}

# all equipment for each faction
MONOLITH_ALL_EQUIPMENT: Set[str] = set()
MONOLITH_ALL_EQUIPMENT |= set(MONOLITH_WEAPONS)
MONOLITH_ALL_EQUIPMENT |= set(MONOLITH_ARMOR)
MONOLITH_ALL_EQUIPMENT |= set(ARTIFACTS)
MONOLITH_ALL_EQUIPMENT |= set(ATTACHMENTS)

STALKERS_ALL_EQUIPMENT: Set[str] = set()
STALKERS_ALL_EQUIPMENT |= set(STALKER_WEAPONS)
STALKERS_ALL_EQUIPMENT |= set(STALKER_ARMOR)
STALKERS_ALL_EQUIPMENT |= set(ARTIFACTS)
STALKERS_ALL_EQUIPMENT |= set(ATTACHMENTS)

ALL_WEAPONS: Set[str] = set()
ALL_WEAPONS |= set(STALKER_WEAPONS)
ALL_WEAPONS |= set(MONOLITH_WEAPONS)
ALL_ARMOR: Set[str] = set()
ALL_ARMOR |= set(STALKER_ARMOR)
ALL_ARMOR |= set(MONOLITH_ARMOR)

MONOLITH_MULTIPLIER = 2

FLAT_EQUIPMENT_BONUSES: Dict[str, int] = {
    "UDP": 3,
    "Fora230": 3,
    "M860Monolith": 3,
    "G37": 4,
    "M701": 4,
    "SPSA": 6,
    "GP3a": 6,
    "RPG": 6,
    "Gauss Rifle": 7,
    "Monolith Battle Armor": 2,
    "Exoskeleton": 4,
    "Improved Exoskeleton": 5,
    "PTM": 2,
    "Kora": 2,
    "AKM-74U": 3,
    "Fora": 5,
    "M860": 6,
    "Rhino": 6,
    "Dnipro": 4,
    "Leather Jacket": 2,
    "Sunrise Suit": 2,
    "PSZ-5V Guardian of Freedom": 2,
    "SEVA suit": 3,
    "PSZ-7 Military Armor": 2,
    "Berill-5M Armored Suit": 4,
    "Silencer": 2,
    "Jellyfish": 3,
}

ODD_ROLL_EQUIPMENT_BONUSES: Dict[str, int] = {
    "TOZ-34": 4,
    "PSZ-7 Military Armor": 3,
    "Tactical Scope": 3,
}

EVEN_ROLL_EQUIPMENT_BONUSES: Dict[str, int] = {
    "M860Monolith": 3,
    "Dnipro": 5,
    "Marauder Suit": 3,
}

MORETHAN_90_EQUIPMENT_BONUSES: Dict[str, int] = {
    "Gauss Rifle": 10,
    "Fora": 2,
    "PSZ-5V Guardian of Freedom": 5,
    "SVU": 3,
}

MORETHAN_85_EQUIPMENT_BONUSES: Dict[str, int] = {
    "RPG": 7,
    "M701": 6,
}

MORETHAN_80_EQUIPMENT_BONUSES: Dict[str, int] = {
    "G37": 3,
    "GP3a": 6,
    "Improved Exoskeleton": 6,
    "Monolith Battle Armor": 3,
    "AKM-74U": 1,
    "Berill-5M Armored Suit": 4,
}

MORETHAN_75_EQUIPMENT_BONUSES: Dict[str, int] = {
    "Exoskeleton": 4,
}

MORETHAN_70_EQUIPMENT_BONUSES: Dict[str, int] = {
    "PSZ-20W Convoy": 5,
    "SVU": 5,
}

ENDSIN_0_EQUIPMENT_BONUSES: Dict[str, int] = {
    "Fora230": 5,
    "Kora": 4,
}

ENDSIN_5_EQUIPMENT_BONUSES: Dict[str, int] = {
    "PTM": 2,
    "Sunrise Suit": 3,
}

ENDSIN_7_EQUIPMENT_BONUSES: Dict[str, int] = {
    "UDP": 3,
}

ENDSIN_9_EQUIPMENT_BONUSES: Dict[str, int] = {
    "SPSA": 4,
    "Rhino": 4,
    "SEVA suit": 2,
}

CONTAINS_9_EQUIPMENT_BONUSES: Dict[str, int] = {
    "OZK Explorer suit": 4,
}

UNLUCKY_100_EQUIPMENT_MINUSES: Dict[str, int] = {
    "Berill-5M Armored Suit": 4,
    "PSZ-20W Convoy": 5,
}

WEIRD_FLOWER_PAIR_ROLL = 96
WEIRD_BOLT_1_2_ROLL = 100
# Weird Artifacts are handled separately

# There are some items that are named differently in roles and messages from loot channels
# This dict converts equipment names from loot messages to roles naming
# Message                   ROLES                     
# Improved  Exoskeleton     Improved Exoskeleton      
# PSZ-7 Millitary           PSZ-7 Military Armor      
# Berill-5M Armored         Berill-5M Armored Suit    
# OZK Explorer Suit         OZK Explorer suit         
# SEVA Suit                 SEVA suit
# M860 Monolith             M860Monolith
WRONG_LOOTED_EQUIPMENT_NAMES: Dict[str, str] = {
    "Improved  Exoskeleton": "Improved Exoskeleton",
    "PSZ-7 Millitary": "PSZ-7 Military Armor",
    "Berill-5M Armored": "Berill-5M Armored Suit",
    "OZK Explorer Suit": "OZK Explorer suit",  
    "SEVA Suit": "SEVA suit",
    "M860 Monolith": "M860Monolith",
}

# There are roles from 2024 Faction Wars which overlap with this year's event roles
FACTION_WARS_24_STALKER_ARMOR = {"Sunrise Suit", "Leather Jacket"}
FACTION_WARS_24_MONOLITH_ARMOR = {"Exoskeleton"}
FACTION_WARS_24_ROLES = {"FactionWars24", "Your Inventory", "AKM", "Sawn-off", "VS Vintar"}
global_faction_wars_24_checks: List[str] = []

# --------------------------------------------------------------------------------------------------------------------
# Bot setup
# --------------------------------------------------------------------------------------------------------------------

intents = discord.Intents.default()
intents.members = True          # recommended for role lookups/fetch_member
intents.message_content = True # not required for mentions[]; enable only if you need msg.content

OWNER_USER_ID = 874038967610265630
bot = commands.Bot(command_prefix="!", intents=intents)

# --------------------------------------------------------------------------------------------------------------------
# Utility functions
# --------------------------------------------------------------------------------------------------------------------

# Matches <@123>, <@!123> (nick mention form)
USER_MENTION_RE = re.compile(r"<@!?(\d{15,25})>")

def extract_user_ids_from_text(text: str) -> Set[int]:
    if not text:
        return set()
    return {int(m.group(1)) for m in USER_MENTION_RE.finditer(text)}

def extract_user_ids_from_embeds(embeds: Iterable[discord.Embed]) -> Set[int]:
    ids: Set[int] = set()
    for e in embeds:
        # title / description
        ids |= extract_user_ids_from_text(e.title or "")
        ids |= extract_user_ids_from_text(e.description or "")

        # fields
        for f in (e.fields or []):
            ids |= extract_user_ids_from_text(f.name or "")
            ids |= extract_user_ids_from_text(f.value or "")

        # footer / author
        if e.footer and e.footer.text:
            ids |= extract_user_ids_from_text(e.footer.text)
        if e.author and e.author.name:
            ids |= extract_user_ids_from_text(e.author.name)

        # some bots also shove IDs into URLs (rare, but cheap to check)
        if e.url:
            ids |= extract_user_ids_from_text(e.url)
    return ids

def _merge_dicts(
    dict_1: Dict[int, Set[str]],
    dict_2: Dict[int, Set[str]],
) -> Dict[int, Set[str]]:
    merged_dict = {k: set(v) for k, v in dict_1.items()} # copy sets
    for k, v in dict_2.items():
        merged_dict.setdefault(k, set()).update(v)
    return merged_dict

def _safe_remove(path: Optional[str]) -> None:
    if not path:
        return
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError as e:
        print(f"Could not delete old cache file {path}: {e}")

def parse_datetime(dt_str: str, tz_name: str) -> datetime:
    """
    Parse "YYYY-MM-DD HH:MM" (or ISO-like "YYYY-MM-DDTHH:MM") in the given timezone.
    Returns an aware datetime in UTC.
    """
    dt_str = dt_str.strip().replace("T", " ")
    try:
        local_naive = datetime.fromisoformat(dt_str)
    except ValueError as e:
        raise ValueError(f"Bad datetime '{dt_str}'. Expected {DATETIME_FORMAT_HINT}.") from e

    tz = ZoneInfo(tz_name)
    if local_naive.tzinfo is None:
        local_aware = local_naive.replace(tzinfo=tz)
    else:
        local_aware = local_naive.astimezone(tz)

    return local_aware.astimezone(ZoneInfo("UTC"))

@dataclass
class MentionedUserInfo:
    user_id: int
    display: str
    mention_count: int
    in_guild: bool
    roles: List[str]

@bot.event
async def on_ready():
    guild_id = os.getenv("GUILD_ID") or GUILD_ID
    if guild_id:
        guild = discord.Object(id=int(guild_id))
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        print(f"[DEBUG] ✅ Logged in as {bot.user} | synced to guild {guild_id}")
    else:
        await bot.tree.sync()
        print(f"[DEBUG] ✅ Logged in as {bot.user} | synced globally (can take time to appear)")


def has_scan_permission(interaction: discord.Interaction) -> bool:
    perms = interaction.user.guild_permissions
    return perms.manage_messages or perms.administrator or interaction.user.id == OWNER_USER_ID

LINK_RE = re.compile(
    r"^https?://(?:ptb\.|canary\.)?discord\.com/channels/(\d+|@me)/(\d+)/(\d+)$"
)

def _short(s: str, n: int = 900) -> str:
    s = (s or "").replace("`", "ˋ")
    return s if len(s) <= n else s[: n - 1] + "…"

# --------------------------------------------------------------------------------------------------------------------
# Parsing equipment from the loot channels
# --------------------------------------------------------------------------------------------------------------------

_LOOT_CACHE_RE = re.compile(r"^(?P<guild>\d+)_(?P<kind>stalkers|monolith)_(?P<ts>\d+)\.json$")

def _loot_cache_path(guild_id: int, faction: str, ts_epoch: int) -> str:
    # faction: "stalkers" or "monolith"
    return f"{guild_id}_{faction}_{ts_epoch}.json"

def _find_latest_loot_cache(guild_id: int, kind: str) -> tuple[Optional[str], Optional[datetime]]:
    """
    Finds the newest cache file for this guild/kind by timestamp embedded in filename.
    Returns (path, timestamp_utc) or (None, None) if not found.
    """
    best_ts: Optional[int] = None
    best_path: Optional[str] = None

    for name in os.listdir("."):
        m = _LOOT_CACHE_RE.match(name)
        if not m:
            continue
        if m.group("guild") != str(guild_id) or m.group("kind") != kind:
            continue

        ts = int(m.group("ts"))
        if best_ts is None or ts > best_ts:
            best_ts = ts
            best_path = name

    if best_ts is None or best_path is None:
        return None, None

    # to make sure there is no new messages from the moment parsing is stopped and timestamp is created, 60 seconds are subtracted
    return best_path, datetime.fromtimestamp(best_ts, tz=ZoneInfo("UTC")) - timedelta(seconds=60)

def _read_loot_cache(path: str) -> Dict[int, Set[str]]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    out: Dict[int, Set[str]] = {}
    for k, v in raw.items():
        try:
            uid = int(k)
        except ValueError:
            continue
        out[uid] = set(v or [])
    return out

def _write_loot_cache(path: str, loot: Dict[int, Set[str]]) -> None:
    serializable = {str(uid): sorted(list(items)) for uid, items in loot.items()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)

def _extract_first_mention_user_id(line: str) -> Optional[int]:
    """
    e.g. userid from <@userid>, Foray Successful/Failed
    """
    m = USER_MENTION_RE.search(line or "")
    return int(m.group(1)) if m else None

def _resolve_channels(
    guild: discord.Guild,
    channels: Iterable[Union[int, discord.TextChannel]]
) -> list[discord.TextChannel]:
    out: list[discord.TextChannel] = []
    for ch in channels:
        if isinstance(ch, discord.TextChannel):
            out.append(ch)
        else:
            resolved = guild.get_channel(int(ch))
            if isinstance(resolved, discord.TextChannel):
                out.append(resolved)
    return out

def _parse_stalker_loot_message(content: str) -> Optional[Tuple[int, str]]:
    """
    STALKERS format:
      <@userid>, Foray Successful/Failed
      <flavor>
      You Got <item name>

    Return (userid, item) if successful; otherwise None.
    """
    if not content:
        return None

    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    if not lines:
        return None

    first = lines[0]
    uid = _extract_first_mention_user_id(first)
    if uid is None:
        return None

    first_lower = first.lower()
    if "foray failed" in first_lower:
        return None
    if "foray successful" not in first_lower:
        return None

    # Find the "You Got ..." line anywhere (more robust than assuming exact line index)
    item: Optional[str] = None
    for ln in lines[1:]:
        ln_stripped = ln.strip()
        if ln_stripped.lower().startswith("you got "):
            item = ln_stripped[len("you got "):].strip()
            break

    if not item:
        return None
    return uid, item

def _parse_monolith_loot_message(content: str) -> Optional[Tuple[int, str]]:
    """
    Monolith format (successful):
      <@userid>, COME TO ME!

      You hear the voice of Monolith! You got <item name>

    Rule:
      - If first line is anything other than "<@userid>, COME TO ME!" -> skip.
      - Otherwise parse last sentence "You got <item name>" (case-insensitive).
    """
    if not content:
        return None

    lines = [ln.rstrip() for ln in content.splitlines() if ln.strip()]
    if not lines:
        return None

    first = lines[0].strip()
    uid = _extract_first_mention_user_id(first)
    if uid is None:
        return None

    # Must be exactly "<@userid>, COME TO ME!" (allow extra whitespace around comma / end)
    # We validate by removing the mention portion and checking the remainder.
    # Example first line: "<@123>, COME TO ME!"
    remainder = USER_MENTION_RE.sub("", first, count=1).strip()
    # remainder should start with "," then "COME TO ME!"
    if remainder != ", COME TO ME!":
        return None

    # Parse item from the full text (bots often keep it in one line/sentence)
    text = "\n".join(lines)
    m = re.search(r"\byou got\s+(.+?)\s*$", text, flags=re.IGNORECASE)
    if not m:
        return None

    item = m.group(1).strip()
    if not item:
        return None
    return uid, item

async def _collect_loot_from_channels(
    *,
    author: discord.Member,
    channels: Iterable[Union[int, discord.TextChannel]],
    parser,
    after_dt: Optional[datetime] = None,
    before_dt: Optional[datetime] = None,
) -> Dict[int, Set[str]]:
    """
    Generic collector:
      - scans ALL messages in given channels
      - only considers messages where msg.author.id == author.id
      - uses 'parser(content) -> (uid, item) | None'
      - accumulates {uid: set(items)}
    """
    if author.guild is None:
        return {}

    loot: DefaultDict[int, Set[str]] = defaultdict(set)
    resolved_channels = _resolve_channels(author.guild, channels)
    for ch in resolved_channels:
        # History scan
        scanned = 0
        async for msg in ch.history(
            limit=None,
            oldest_first=True,
            after=after_dt,
            before=before_dt,
        ):
            scanned += 1
            # gentle throttling on huge channels
            if scanned % 50 == 0:
                print(f"[DEBUG] Scanned in channel: {scanned}")
                await asyncio.sleep(0.3)
            if msg.author.id != author.id:
                continue

            parsed = parser(msg.content or "")
            if parsed is None:
                continue

            uid, item = parsed
            if item in WRONG_LOOTED_EQUIPMENT_NAMES:
                loot[uid].add(WRONG_LOOTED_EQUIPMENT_NAMES[item])
            else:
                loot[uid].add(item)

    return dict(loot)

async def collect_stalkers_loot(author: discord.Member) -> Dict[int, Set[str]]:
    """
    Parse whole STALKER_LOOT_CHANNELS.
    Returns: { user_id: {item1, item2, ...}, ... }
    Cached flow:
      - cache file holds loot parsed UP TO cache_cutoff_datetime (inclusive by 'before' bound)
      - we parse AFTER cache_cutoff_datetime for fresh data and merge at runtime
    """
    if author.guild is None:
        return {}

    guild_id = author.guild.id
    faction = "stalkers"
    cache_path, cache_dt_utc = _find_latest_loot_cache(guild_id, faction)

    if cache_path is None:
        # No cache yet: parse whole history, write cache with "finished" timestamp
        loot = await _collect_loot_from_channels(
            author=author,
            channels=STALKER_LOOT_CHANNELS,
            parser=_parse_stalker_loot_message,
        )
        ts_now = int(time.time())
        _write_loot_cache(_loot_cache_path(guild_id, faction, ts_now), loot)
        return loot

    # Cache exists: load it, parse only new messages after timestamp in filename, merge, write new cache
    cached_part = _read_loot_cache(cache_path)
    fresh_part = await _collect_loot_from_channels(
        author=author,
        channels=STALKER_LOOT_CHANNELS,
        parser=_parse_stalker_loot_message,
        after_dt=cache_dt_utc,  # only after the cached timestamp
    )
    merged = _merge_dicts(cached_part, fresh_part)

    ts_now = int(time.time())
    _write_loot_cache(_loot_cache_path(guild_id, faction, ts_now), merged)
    _safe_remove(cache_path)
    return merged

async def collect_monolith_loot(author: discord.Member) -> Dict[int, Set[str]]:
    """
    Parse whole MONOLITH_LOOT_CHANNELS.
    Returns: { user_id: {item1, item2, ...}, ... }
    Cached flow:
      - cache file holds loot parsed UP TO cache_cutoff_datetime
      - we parse AFTER cache_cutoff_datetime for fresh data and merge at runtime
    """
    if author.guild is None:
        return {}

    guild_id = author.guild.id
    faction = "monolith"
    cache_path, cache_dt_utc = _find_latest_loot_cache(guild_id, faction)

    if cache_path is None:
        loot = await _collect_loot_from_channels(
            author=author,
            channels=MONOLITH_LOOT_CHANNELS,
            parser=_parse_monolith_loot_message,
        )
        ts_now = int(time.time())
        _write_loot_cache(_loot_cache_path(guild_id, faction, ts_now), loot)
        return loot

    cached_part = _read_loot_cache(cache_path)
    fresh_part = await _collect_loot_from_channels(
        author=author,
        channels=MONOLITH_LOOT_CHANNELS,
        parser=_parse_monolith_loot_message,
        after_dt=cache_dt_utc,  # only after the cached timestamp
    )
    merged = _merge_dicts(cached_part, fresh_part)

    ts_now = int(time.time())
    _write_loot_cache(_loot_cache_path(guild_id, faction, ts_now), merged)
    _safe_remove(cache_path)
    return merged

# --------------------------------------------------------------------------------------------------------------------
# Calculating equipment bonus and cheating checks
# --------------------------------------------------------------------------------------------------------------------

async def parse_roll_embed_message(message: discord.Message) -> Tuple[int, int, List[str]]:
    """
    Parse roll from embed.title and user id from embed.description.

    Expected:
      message.embeds[0].title == "<roll number>"
      message.embeds[0].description contains "<@userid> ..."

    Returns: (roll, user_id, roles_list[str])
    """
    if not message.embeds:
        raise ValueError("Message has no embeds.")

    e = message.embeds[0]

    # 1) roll from title
    title = (e.title or "").strip()
    if not title:
        raise ValueError("Embed title is empty; cannot parse roll.")
    try:
        roll = int(title)
    except ValueError as ex:
        raise ValueError(f"Embed title is not an integer: {e.title!r}") from ex

    # 2) user_id from embed.description
    desc = e.description or ""
    m = USER_MENTION_RE.search(desc)
    if not m:
        raise ValueError("No <@userid> mention found in embed.description.")
    user_id = int(m.group(1))

    # 3) fetch roles for that user (if possible)
    roles: List[str] = []
    if message.guild is None:
        return roll, user_id, roles

    member: Optional[discord.Member] = message.guild.get_member(user_id)
    if member is None:
        try:
            member = await message.guild.fetch_member(user_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            member = None

    if member is None:
        return roll, user_id, roles

    roles = [r.name.strip() for r in member.roles if r != message.guild.default_role]
    return roll, user_id, roles

def get_faction(roles: Sequence[str]) -> str:
    """
    If any role in roles is present in MONOLITH_FACTIONS, return that role name.
    Otherwise return "STALKERS".
    """
    for r in roles:
        for monolith_faction in MONOLITH_FACTIONS:
            # such complication is required since the roles on the server have emoji before the actual name of the role
            if r.strip().endswith(monolith_faction):
                return monolith_faction

    return "STALKERS"

def get_equipped_equipment(
    roles: Sequence[str],
    factionEquipmentList: Set[str],
) -> Set[str]:
    """
    From roles, return only those that are equipment roles present in factionEquipmentList.
    """
    equipped: Set[str] = set()
    for r in roles:
        for faction_eq in factionEquipmentList:
            # such complication is required since the roles on the server have emoji before the actual name of the role
            if r.strip().endswith(faction_eq):
                equipped.add(faction_eq)
    return equipped

def filter_redundant_armor(
    equipped: Set[str], 
    roles: List[str],
    userid: int,
    roll: int,
    faction: str,
    equipmentDictionary: Dict[int, Set[str]],
) -> Set[str]:
    """
    Filter out Faction Wars 24 roles and double armors/weapons for TRANSITIONED_FACTIONS
    """
    global global_faction_wars_24_checks
    
    faction_wars_roles: Set[str] = set()
    for r in roles:
        for faction_r in FACTION_WARS_24_ROLES:
            # such complication is required since the roles on the server have emoji before the actual name of the role
            if r.strip().endswith(faction_r):
                faction_wars_roles.add(faction_r)
    equipped_armors = equipped.intersection(ALL_ARMOR)
    if faction in TRANSITIONED_FACTIONS:
        # Noon
        equipped_weapons = equipped.intersection(ALL_WEAPONS)
        if len(equipped_weapons) > 1:
            # did not deselect stalker weapons
            for eq in equipped_weapons:
                if eq in STALKER_WEAPONS:
                    equipped.remove(eq)
        if len(equipped_armors) > 1:
            # did not deselect stalker armor
            for eq in equipped_armors:
                if eq in STALKER_ARMOR:
                    equipped.remove(eq)
            equipped_armors = equipped.intersection(ALL_ARMOR)
        if len(equipped_armors) > 0 and len(faction_wars_roles) > 0 and (len(equipped_armors.intersection(FACTION_WARS_24_STALKER_ARMOR)) > 0 or len(equipped_armors.intersection(FACTION_WARS_24_MONOLITH_ARMOR)) > 0):
            cheating, fake_list = is_cheating(equipped, userid, equipmentDictionary)
            if not cheating:
                check_string = f"Please, validate `{userid}`(Noon) for following gear: {equipped_armors}. Affected roll: {roll}"
                print(f"[DEBUG] {check_string}")
                global_faction_wars_24_checks.append(check_string)
    else:
        if faction in MONOLITH_FACTIONS:
            # Monolith
            if len(equipped_armors) > 0:
                for eq_armor in equipped_armors:
                    if eq_armor in FACTION_WARS_24_STALKER_ARMOR:
                        equipped.remove(eq_armor)
                if len(faction_wars_roles) > 0 and len(equipped_armors.intersection(FACTION_WARS_24_MONOLITH_ARMOR)) > 0:
                    cheating, fake_list = is_cheating(equipped, userid, equipmentDictionary)
                    if not cheating:
                        check_string = f"Please, validate `{userid}`(Monolith) for following gear: {equipped_armors}. Affected roll: {roll}"
                        print(f"[DEBUG] {check_string}")
                        global_faction_wars_24_checks.append(check_string)

        else:
            # STALKERS
            if len(equipped_armors) > 0:
                for eq_armor in equipped_armors:
                    if eq_armor in FACTION_WARS_24_MONOLITH_ARMOR:
                        equipped.remove(eq_armor)
                if len(faction_wars_roles) > 0 and len(equipped_armors.intersection(FACTION_WARS_24_STALKER_ARMOR)) > 0:
                    cheating, fake_list = is_cheating(equipped, userid, equipmentDictionary)
                    if not cheating:
                        check_string = f"Please, validate `{userid}`(STALKERS) for following gear: {equipped_armors}. Affected roll: {roll}"
                        print(f"[DEBUG] {check_string}")
                        global_faction_wars_24_checks.append(check_string)
    return equipped
    
def is_cheating(
    equipmentList: Set[str],
    userid: int,
    equipmentDictionary: Dict[int, Set[str]],
) -> Tuple[bool, List[str]]:
    """
    For each equipment in equipmentList, check it's present in equipmentDictionary[userid].
    Anything missing is added to fakeEquipmentList.

    Returns: (isCheating, fakeEquipmentList)
    """
    owned: Set[str] = equipmentDictionary.get(userid, set())
    fakeEquipmentList: List[str] = []
    for eq in equipmentList:
        if eq not in owned:
            fakeEquipmentList.append(eq)
    
    if len(fakeEquipmentList) == 1 and (fakeEquipmentList[0] in FACTION_WARS_24_MONOLITH_ARMOR or list(fakeEquipmentList)[0] in FACTION_WARS_24_STALKER_ARMOR):
        return False, []
    return (len(fakeEquipmentList) > 0), fakeEquipmentList

def calculate_equipment_bonus(
    equipment: Sequence[str],
    roll: int,
) -> int:
    """
    Placeholder bonus calculation.
    You will fill EQUIPMENT_BONUSES with your real numbers.

    Returns: equipmentBonus (int)
    """
    bonus = 0
    for eq in equipment:
        
        bonus += FLAT_EQUIPMENT_BONUSES.get(eq, 0)    
        if roll % 2 == 0:
            bonus += EVEN_ROLL_EQUIPMENT_BONUSES.get(eq, 0)
        else:
            bonus += ODD_ROLL_EQUIPMENT_BONUSES.get(eq, 0)
        if roll >= 70:
            bonus += MORETHAN_70_EQUIPMENT_BONUSES.get(eq, 0)
        if roll >= 75:
            bonus += MORETHAN_75_EQUIPMENT_BONUSES.get(eq, 0)
        if roll >= 80:
            bonus += MORETHAN_80_EQUIPMENT_BONUSES.get(eq, 0)
        if roll >= 85:
            bonus += MORETHAN_85_EQUIPMENT_BONUSES.get(eq, 0)
        if roll >= 90:
            bonus += MORETHAN_90_EQUIPMENT_BONUSES.get(eq, 0)
        if roll % 10 == 0:
            bonus += ENDSIN_0_EQUIPMENT_BONUSES.get(eq, 0)
        if roll % 10 == 5:
            bonus += ENDSIN_5_EQUIPMENT_BONUSES.get(eq, 0)
        if roll % 10 == 7:
            bonus += ENDSIN_7_EQUIPMENT_BONUSES.get(eq, 0)
        if roll % 10 == 9:
            bonus += ENDSIN_9_EQUIPMENT_BONUSES.get(eq, 0)
            bonus += CONTAINS_9_EQUIPMENT_BONUSES.get(eq, 0)
        if "9" in str(roll):
            bonus += CONTAINS_9_EQUIPMENT_BONUSES.get(eq, 0)
        if roll == 100:
            bonus -= UNLUCKY_100_EQUIPMENT_MINUSES.get(eq, 0)
    return bonus

# --------------------------------------------------------------------------------------------------------------------
# Parse all rolls from the channel
# --------------------------------------------------------------------------------------------------------------------


async def count_rolls_in_channel(
    *,
    guild: discord.Guild,
    channel: discord.TextChannel,
    author: discord.Member,
    interaction: discord.Interaction,
    start_utc,
    end_utc,
) -> Tuple[int, int, List[Tuple[int, str]], Dict[int, List[str]], List[str]]:
    """
    Returns:
      (monolith_total, stalkers_total, cheaters, cheater_fake_equipment_map)

    Prints:
      - Scores for each faction
      - Cheaters and faked equipment
    """

    # ---- pre-create all needed variables/objects ----
    
    # looted equipment dictionaries
    await interaction.edit_original_response(content="Stage 1/2: parsing fairly looted equipment…")
    monolith_looted: Dict[int, Set[str]] = await collect_monolith_loot(author)
    stalkers_looted: Dict[int, Set[str]] = await collect_stalkers_loot(author)
    merged_looted = _merge_dicts(monolith_looted, stalkers_looted)
    # totals
    monolith_total = 0
    stalkers_total = 0

    # cheaters and their fake equipment
    cheaters: List[Tuple[int, str]] = []
    cheater_fake_equipment: Dict[int, List[str]] = defaultdict(list)

    # Object to hold one Weird Flower carrier. Once same roll was detected between two Weird Flower carriers, their rolls are set to 96 and 
    # the first carrier gets deleted from the list.
    weird_flower_carriers: Dict[int, Tuple[int, str, List[str]]] = defaultdict(tuple) # key: roll, value: tuple([User ID, faction, equipment])

    # ---- get list of all messages from specified author ----
    # (We stream messages; no need to materialize unless you want.)
    scanned = 0
    matched = 0
    weird_flower_pairs: List[str] = []

    await interaction.edit_original_response(content="Stage 2/2: parsing rolls…")
    async for msg in channel.history(after=start_utc, before=end_utc, limit=None, oldest_first=True):
        scanned += 1
        if scanned % 50 == 0:
            await asyncio.sleep(0.3)
        if msg.author.id != author.id:
            continue

        matched += 1

        # ---- parse roll message ----
        try:
            roll, userid, roles = await parse_roll_embed_message(msg)
        except Exception:
            # Skip messages that aren't the roll embed format
            continue

        faction = get_faction(roles)

        # Pick faction equipment list + looted dictionary
        if faction in MONOLITH_FACTIONS:
            faction_equipment_list = set(MONOLITH_ALL_EQUIPMENT)
            faction_looted_dict = monolith_looted
            is_monolith = True
            if faction in TRANSITIONED_FACTIONS:
                faction_equipment_list |= STALKERS_ALL_EQUIPMENT
                faction_looted_dict = merged_looted
        else:
            faction_equipment_list = STALKERS_ALL_EQUIPMENT
            faction_looted_dict = stalkers_looted
            is_monolith = False

        equipped = get_equipped_equipment(roles, faction_equipment_list)
        equipped = filter_redundant_armor(equipped, roles, userid, roll, faction, faction_looted_dict)
        
        cheating, fake_list = is_cheating(equipped, userid, faction_looted_dict)

        if cheating:
            cheaters_ids = [pair[0] for pair in cheaters]
            if (userid not in cheaters_ids):
                cheaters.append((userid, faction))
            # accumulate (dedupe while preserving order)
            existing = set(cheater_fake_equipment[userid])
            for x in fake_list:
                if x not in existing:
                    cheater_fake_equipment[userid].append(x)
                    existing.add(x)
        else:
            # if Weird Flower is detected, the roll is not calculated and kept in the dictionary
            # till the end of parsing. 
            if "Weird Flower" in equipped:
                if roll in weird_flower_carriers:
                    # handle detected pair with Weird Flowers
                    paired_userid, paired_faction, paired_equipped = weird_flower_carriers[roll]
                    pair_string = f"(roll {roll}): `{userid}`, `{paired_userid}`"
                    print(f"[DEBUG] Pair with Weird Flowers detected {pair_string}")
                    weird_flower_pairs.append(pair_string)
                    del weird_flower_carriers[roll]
                    paired_roll = WEIRD_FLOWER_PAIR_ROLL
                    if (roll == 1 or roll == 2):
                        roll = WEIRD_FLOWER_PAIR_ROLL
                        if "Weird Bolt" in equipped:
                            roll = WEIRD_BOLT_1_2_ROLL
                        if "Weird Bolt" in paired_equipped:
                            paired_roll = WEIRD_BOLT_1_2_ROLL
                    else:
                        roll = WEIRD_FLOWER_PAIR_ROLL
                    equipment_bonus = calculate_equipment_bonus(paired_equipped, paired_roll)
                    if paired_faction in MONOLITH_FACTIONS:
                        monolith_total += (paired_roll + equipment_bonus)
                    else:
                        stalkers_total += (paired_roll + equipment_bonus)
                    
                else:
                    weird_flower_carriers[roll] = tuple([userid, faction, equipped])
                    continue
            elif (roll == 1 or roll == 2) and "Weird Bolt" in equipped:
                roll = WEIRD_BOLT_1_2_ROLL

            equipment_bonus = calculate_equipment_bonus(equipped, roll)
            if is_monolith:
                monolith_total += (roll + equipment_bonus)
            else:
                stalkers_total += (roll + equipment_bonus)

    # Handle rest of rolls in weird_flower_carriers, which didn't get pair
    for roll, carrier_info in weird_flower_carriers.items():
        nonpaired_userid, nonpaired_faction, nonpaired_equipped = carrier_info
        if (roll == 1 or roll == 2) and "Weird Bolt" in nonpaired_equipped:
            roll = WEIRD_BOLT_1_2_ROLL
        equipment_bonus = calculate_equipment_bonus(nonpaired_equipped, roll)
        if nonpaired_faction in MONOLITH_FACTIONS:
            monolith_total += (roll + equipment_bonus)
        else:
            stalkers_total += (roll + equipment_bonus)

    # ---- Print results ----
    print("=== COUNT ROLLS RESULTS ===")
    print(f"Channel: #{channel.name} ({channel.id})")
    print(f"Author: {author} ({author.id})")
    print(f"Messages scanned: {scanned}")
    print(f"Messages matched (by author): {matched}")
    print(f"Monolith total score: {monolith_total} x {MONOLITH_MULTIPLIER} = {monolith_total * MONOLITH_MULTIPLIER}")
    print(f"STALKERS total score: {stalkers_total}")

    if cheaters:
        print("=== CHEATERS ===")
        for uid, faction in cheaters:
            fake = cheater_fake_equipment.get(uid, [])
            print(f"- {uid}({faction}): {fake}")
    else:
        print("No cheaters detected.")

    return monolith_total, stalkers_total, cheaters, dict(cheater_fake_equipment), weird_flower_pairs


# --------------------------------------------------------------------------------------------------------------------
# Bot Commands
# --------------------------------------------------------------------------------------------------------------------

@bot.tree.command(
    name="count_rolls",
    description="Count rolls in a channel for a time range for messages by a user."
)
@app_commands.describe(
    channel="Channel to scan",
    author="Whose messages to analyze",
    start=f"Start datetime ({DATETIME_FORMAT_HINT})",
    end=f"End datetime ({DATETIME_FORMAT_HINT})",
    tz="Timezone name (IANA), e.g. Europe/Warsaw"
)
async def count_rolls(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    author: discord.Member,
    start: str,
    end: str,
    tz: Optional[str] = None,
):
    
    print(f"[DEBUG] Launched /count_rolls")
    # Keep all Discord command functionality (guild, perms, etc.)
    if interaction.guild is None:
        await interaction.response.send_message("This command only works in a server (not in DMs).", ephemeral=True)
        return

    if not has_scan_permission(interaction):
        await interaction.response.send_message(
            "You don't have permission to run this (need Manage Messages or Admin).",
            ephemeral=True
        )
        return

    tz_name = tz or DEFAULT_TZ

    try:
        start_utc = parse_datetime(start, tz_name)
        end_utc = parse_datetime(end, tz_name)
    except ValueError as e:
        await interaction.response.send_message(str(e), ephemeral=True)
        return

    if end_utc <= start_utc:
        await interaction.response.send_message("End must be after Start.", ephemeral=True)
        return

    # Permissions check for the target channel
    me = interaction.guild.me or interaction.guild.get_member(bot.user.id)
    if me is None:
        try:
            me = await interaction.guild.fetch_member(bot.user.id)
        except discord.HTTPException:
            me = None

    if me is None:
        await interaction.response.send_message("Could not resolve bot member in this guild.", ephemeral=True)
        return

    perms = channel.permissions_for(me)
    if not (perms.view_channel and perms.read_message_history):
        await interaction.response.send_message(
            "Bot lacks View Channel and/or Read Message History in that channel.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    # Call business logic
    monolith_total, stalkers_total, cheaters, cheater_fake_map, weird_flower_pairs = await count_rolls_in_channel(
        guild=interaction.guild,
        channel=channel,
        author=author,
        interaction=interaction,
        start_utc=start_utc,
        end_utc=end_utc,
    )

    # Respond in Discord (still ephemeral; you can change if you want it public)
    lines = [
        f"- Channel: {channel.mention}",
        f"- Author: {author.mention}",
        f"- Range (local {tz_name}): {start} → {end}",
        "",
        f"**Monolith total score:** {monolith_total} x {MONOLITH_MULTIPLIER} = {monolith_total * MONOLITH_MULTIPLIER}",
        f"**STALKERS total score:** {stalkers_total}",
        "",
        f"**Cheaters:** {len(cheaters)}",
    ]
    if cheaters:
        # cap output so it doesn't get too long
        for uid, faction in cheaters[:50]:
            fake = cheater_fake_map.get(uid, [])
            fake_str = ", ".join(fake) if fake else "(no items listed)"
            lines.append(f"- `{uid}`({faction}): {fake_str}")
        if len(cheaters) > 20:
            lines.append(f"...and {len(cheaters) - 20} more.")
    
    lines.append(f"\n**Weird Flower Pairs:** {len(weird_flower_pairs)}")
    if weird_flower_pairs:
        for pair_line in weird_flower_pairs:
            lines.append(pair_line)
    
    global global_faction_wars_24_checks
    global_faction_wars_24_checks.sort()
    if global_faction_wars_24_checks:
        lines.append("\n **Here is the list of users with possible Faction Wars 24 equipment**, that should be validated manually in case it may change the result of the battle. The equipment bonuses are already added to the score, subtract the bonus if the equipment is confirmed to be from 2024 event (no reaction on armor-role-selection message). If the equipment is present, please check it for cheating as well (you can use /is_cheater author:@Wolf user:<userid>)")
        for check_line in global_faction_wars_24_checks:
            lines.append(check_line)
    global_faction_wars_24_checks = []
    await interaction.edit_original_response(content="\n".join(lines))

@bot.tree.command(
    name="is_cheater",
    description="Check whether a user is cheating based on currently equipped roles vs looted equipment."
)
@app_commands.describe(
    author="Bot/user whose messages are parsed in loot channels",
    user="User to check"
)
async def is_cheater_cmd(
    interaction: discord.Interaction,
    author: discord.Member,
    user: discord.Member,
):
    print(f"[DEBUG] Executed /is_cheater")
    
    if interaction.guild is None:
        await interaction.response.send_message("This command only works in a server (not in DMs).", ephemeral=True)
        return

    if not has_scan_permission(interaction):
        await interaction.response.send_message(
            "You don't have permission to run this (need Manage Messages, Admin, or be the bot owner).",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    # Build looted dicts (cached on disk by your existing flow)
    monolith_looted: Dict[int, Set[str]] = await collect_monolith_loot(author)
    stalkers_looted: Dict[int, Set[str]] = await collect_stalkers_loot(author)
    merged_looted = _merge_dicts(monolith_looted, stalkers_looted)

    roles = [r.name.strip() for r in user.roles if r != interaction.guild.default_role]
    faction = get_faction(roles)

    # Same faction logic as in count_rolls_in_channel
    if faction in MONOLITH_FACTIONS:
        faction_equipment_list = set(MONOLITH_ALL_EQUIPMENT)
        faction_looted_dict = monolith_looted
        if faction in TRANSITIONED_FACTIONS:
            faction_equipment_list |= STALKERS_ALL_EQUIPMENT
            faction_looted_dict = merged_looted
    else:
        faction_equipment_list = STALKERS_ALL_EQUIPMENT
        faction_looted_dict = stalkers_looted

    equipped = get_equipped_equipment(roles, faction_equipment_list)

    # Preserve global list from being polluted by this command
    saved_fw24 = list(global_faction_wars_24_checks)
    try:
        equipped = filter_redundant_armor(
            equipped=equipped,
            roles=roles,
            userid=user.id,
            roll=0,  # not applicable here; only used in debug strings
            faction=faction,
            equipmentDictionary=faction_looted_dict,
        )
    finally:
        global_faction_wars_24_checks.clear()
        global_faction_wars_24_checks.extend(saved_fw24)

    cheating, fake_list = is_cheating(equipped, user.id, faction_looted_dict)

    equipped_str = ", ".join(sorted(equipped)) if equipped else "(none)"
    if cheating:
        fake_str = ", ".join(fake_list) if fake_list else "(none)"
        msg = (
            f"**Result: CHEATER 🔴**\n"
            f"- User: {user.mention} (`{user.id}`)\n"
            f"- Faction: `{faction}`\n"
            f"- Equipped: {equipped_str}\n"
            f"- Missing from loot: {fake_str}\n"
        )
    else:
        msg = (
            f"**Result: NOT a cheater ✅**\n"
            f"- User: {user.mention} (`{user.id}`)\n"
            f"- Faction: `{faction}`\n"
            f"- Equipped: {equipped_str}\n"
        )

    await interaction.edit_original_response(content=msg)


def main():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        token = DISCORD_BOT_TOKEN
        if not token:
            raise RuntimeError("Set DISCORD_BOT_TOKEN environment variable.")
    bot.run(token)

if __name__ == "__main__":
    main()
