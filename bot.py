import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from analyzer import analyze_text
import re
import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz
import datetime

TOKEN = os.getenv("BOT_TOKEN")

TEAM_MAP = {
    "曼聯": "Manchester United",
    "車路士": "Chelsea",
    "利物浦": "Liverpool",
    "阿仙奴": "Arsenal",
}

LEAGUE_MAP = {
    "英超": "Premier League",
}

user_cache = {}

def is_match(a, b):
    return fuzz.partial_ratio(a.lower(), b.lower()) > 70

def parse_input(text):
    text = text.replace("/analyze", "").strip()
    parts = text.split()

    league = None
    if parts[-1] in LEAGUE_MAP:
        league = parts[-1]
        text = " ".join(parts[:-1])

    teams = re.split(r"\s+vs\s+|\s+對\s+", text)
    if len(teams) != 2:
        return None

    t1 = TEAM_MAP.get(teams[0], teams[0])
    t2 = TEAM_MAP.get(teams[1], teams[1])

    return t1, t2, league

def match_league(text, league):
    if not league:
        return True
    return league in text

def search_matches(team1, team2, league=None):

    results = []
    today = datetime.datetime.now()

    for i in range(3):
        date = (today + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        url = f"https://bf.titan007.com/football/Over_{date}.htm"

        res = requests.get(url)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")

        for row in soup.select("tr"):
            text = row.text

            if not (is_match(team1, text) and is_match(team2, text)):
                continue

            if not match_league(text, league):
                continue

            link = row.find("a")
            if link and "analysis" in link.get("href", ""):
                results.append({
                    "text": text[:50],
                    "url": "https://odds.titan007.com" + link["href"]
                })

    return results[:5]

def analyze_command(update, context):

    parsed = parse_input(update.message.text)

    if not parsed:
        update.message.reply_text("❌ 格式：/analyze 曼聯 vs 車路士")
        return

    team1, team2, league = parsed

    matches = search_matches(team1, team2, league)

    if not matches:
        update.message.reply_text("❌ 找不到比賽")
        return

    if len(matches) == 1:
        result = analyze_text(matches[0]["url"])
        update.message.reply_text(result)
        return

    msg = "🔍 找到多場：\n\n"
    for i, m in enumerate(matches):
        msg += f"{i+1}. {m['text']}\n"

    msg += "\n回覆數字選擇"

    user_cache[update.message.chat_id] = matches
    update.message.reply_text(msg)

def handle_choice(update, context):

    chat_id = update.message.chat_id
    text = update.message.text.strip()

    if chat_id not in user_cache:
        return

    if not text.isdigit():
        return

    idx = int(text) - 1
    matches = user_cache[chat_id]

    if idx < 0 or idx >= len(matches):
        update.message.reply_text("❌ 無效")
        return

    result = analyze_text(matches[idx]["url"])
    update.message.reply_text(result)

    del user_cache[chat_id]

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("analyze", analyze_command))
    dp.add_handler(MessageHandler(Filters.text, handle_choice))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
