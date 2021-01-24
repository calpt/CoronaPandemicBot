# 🦠 Corona Pandemic Bot

[**@coronapandemicbot**](https://t.me/coronapandemicbot) is a Telegram bot that tracks the worldwide spread of the Covid-19 disease and worldwide vaccination efforts.

## ✨ Features

Commands:
- **/world** - Worldwide case statistics.
- **/today** - Summary of today's cases.
- **/list** - List of countries ordered by number of cases.
- **/subscribe** - Subscribe to daily status updates with new case statistics.
- **/setcountry** - Set your country (for /today and daily updates).
- **/[country]** - Case statistics for one country. Replace `[country]` with the country code or country name (e.g. /fr, /france).
- **/graph [country]** - Show a graph with a timeline of new cases of the last 30 days in one country. Type `/graph world` for worldwide cases.
- **/vacc [country]** - Show a graph with a timeline of daily administered vaccination doses in one country. Type `/vacc world` for worldwide vaccinations.
- **/map [country]** - Show a case distribution map for one country. Type `/map world` for world map.
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

The worldwide case statistics are provided and regularly updated by [worldometers.info](https://www.worldometers.info/coronavirus/).
The data for the case timeline plots is provided and updated by Johns Hopkins University.
The data for Covid-19 vaccinations is provided and updated by [Our World in Data](https://ourworldindata.org/covid-vaccinations).

All data is accessed via the [disease.sh REST API](https://github.com/disease-sh/API).

The case distribution maps are retrieved from [Wikimedia Commons](https://commons.wikimedia.org/wiki/Main_Page) and accessed via the [Wikidata Query Service](https://query.wikidata.org/).
