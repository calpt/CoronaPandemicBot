import io
from datetime import timedelta

import matplotlib
import matplotlib.pyplot as plt


matplotlib.use("Agg")
matplotlib.style.use("seaborn")


def plot_timeseries(data):
    dates = [data["first_date"] + timedelta(days=i) for i in range(len(data["cases"]))]
    fig, ax = plt.subplots()
    plt.plot(dates, data["cases"], ".-c", label="Infections")
    plt.fill_between(dates, data["cases"], color="c", alpha=0.5)
    plt.plot(dates, data["deaths"], ".-r", label="Deaths")
    plt.fill_between(dates, data["deaths"], color="r", alpha=0.5)
    plt.annotate(data["cases"][-1], (dates[-1], data["cases"][-1]), ha="right", va="bottom", color="c")
    plt.annotate(data["deaths"][-1], (dates[-1], data["deaths"][-1]), ha="right", va="bottom", color="r")
    plt.legend(loc="upper left")
    plt.xticks(rotation=30, ha="right")
    plt.xlim((dates[0], dates[-1]))
    plt.ylabel("Cases")
    plt.title("New Covid-19 Cases in {} - {} Days".format(data["name"], len(data["cases"])))
    plt.text(0, 0, "by @coronapandemicbot; based on data by JHUCSSE", fontsize=6, va="bottom", transform=ax.transAxes)
    plt.tight_layout()
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    plt.clf()
    return buffer


if __name__ == "__main__":
    from statistics_api import CovidApi

    api = CovidApi()
    data = api.timeseries(country="de")
    buffer = plot_timeseries(data)
    with open("plot.png", "wb") as f:
        f.write(buffer.getvalue())
