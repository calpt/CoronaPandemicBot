import io
from datetime import timedelta

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter


matplotlib.use("Agg")
matplotlib.style.use("seaborn")


def _moving_avg(data, days=7):
    # Use 1d convolution for moving average, as explained in https://stackoverflow.com/a/22621523.
    return np.convolve(data, np.ones(days) / days, mode="valid")


def plot_timeseries(data):
    fig, ax = plt.subplots()
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    cases, deaths = _moving_avg(data["cases"]), _moving_avg(data["deaths"])
    dates = [data["last_date"] - timedelta(days=i) for i in range(len(cases))][::-1]
    plt.plot(dates, cases, ".-c", label="Infections")
    plt.fill_between(dates, cases, color="c", alpha=0.5)
    plt.plot(dates, deaths, ".-r", label="Deaths")
    plt.fill_between(dates, deaths, color="r", alpha=0.5)
    plt.annotate(round(cases[-1]), (dates[-1], cases[-1]), ha="right", va="bottom", color="c")
    plt.annotate(round(deaths[-1]), (dates[-1], deaths[-1]), ha="right", va="bottom", color="r")
    plt.legend()
    plt.xticks(rotation=30, ha="right")
    plt.xlim((dates[0], dates[-1]))
    plt.ylabel("Cases (moving 7-day avg.)")
    plt.title("New Covid-19 Cases in {} - {} Days".format(data["name"], len(cases)))
    plt.text(0, 0, "by @coronapandemicbot; data by JHUCSSE", fontsize=6, va="bottom", transform=ax.transAxes)
    plt.tight_layout()
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    plt.clf()
    return buffer


def plot_vaccinations_series(data):
    fig, ax = plt.subplots()
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    vaccinations = _moving_avg(data["vaccinations"])
    dates = [data["last_date"] - timedelta(days=i) for i in range(len(vaccinations))][::-1]
    plt.plot(dates, vaccinations, ".-g")
    plt.fill_between(dates, vaccinations, color="g", alpha=0.5)
    plt.xticks(rotation=30, ha="right")
    plt.xlim((dates[0], dates[-1]))
    plt.ylabel("Vaccinations Doses (moving 7-day avg.)")
    plt.title("Daily Vaccination Doses in {} - {} Days".format(data["name"], len(vaccinations)))
    plt.text(0.01, 0.95, f"Total: {data['total']:,}", weight="bold", transform=ax.transAxes)
    plt.text(
        0, 0, "by @coronapandemicbot; data by ourworldindata.org.", fontsize=6, va="bottom", transform=ax.transAxes
    )
    plt.tight_layout()
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    plt.clf()
    return buffer


if __name__ == "__main__":
    import argparse
    from statistics_api import CovidApi

    parser = argparse.ArgumentParser(description="Create timeline plots used by @coronapandemicbot")
    parser.add_argument("type", type=str, choices=["cases", "vacc"], help="type of plot to create")
    parser.add_argument("--country", type=str, default=None, help="country to plot, world by default")
    parser.add_argument("-o", "--output", type=str, default="plot.png", help="output file, defaults to plot.png")

    args = parser.parse_args()

    api = CovidApi()
    if args.type == "cases":
        data = api.timeseries(country=args.country)
        buffer = plot_timeseries(data)
    else:
        data = api.vaccinations_series(country=args.country)
        buffer = plot_vaccinations_series(data)
    with open(args.output, "wb") as f:
        f.write(buffer.getvalue())
