# 🦠 Corona Pandemic Bot

[**@coronapandemicbot**](https://t.me/coronapandemicbot) is a Telegram bot that tracks the worldwide spread of the COVID-19 disease.

## ✨ Features

Commands:
- **/world** - Worldwide case statistics.
- **/today**  - Summary of today's cases.
- **/list** - List of countries ordered by number of cases.
- **/[country]** - Case statistics for one country. Replace `[country]` with the country code or country name (e.g. /fr, /france).
- **/subscribe** - Subscribe to daily status updates with new case statistics.
- **/setcountry** - Set your country (for /today and daily updates).
- **/help** - Show the help.

You can use this bot in any Telegram chat without adding it by typing `@coronapandemicbot [country]`.

## 🛠 Setup

1. Clone this repo and install required Python dependencies:
```
python3 -m pip install -r requirements.txt
```
2. Create your own Telegram bot by contacting [@BotFather](https://t.me/BotFather).
3. Rename the included file `config.sample.json` to `config.json` and fill in your personal bot token.  
3. Run the bot:
```
python3 bot.py
```

## 📊 Data

The worldwide case statistics are provided and regularly updated by [worldometers.info](https://www.worldometers.info/coronavirus/) and accessed through the [NovelCOVID REST API](https://github.com/NovelCovid/API).

The case distribution maps are retrieved from [Wikimedia Commons](https://commons.wikimedia.org/wiki/Main_Page) and accessed via the [Wikidata Query Service](https://query.wikidata.org/).
