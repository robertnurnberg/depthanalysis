import argparse
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import collections


class depthdata:
    def __init__(self, prefix, labels):
        self.prefix = prefix
        self.data = []  # triplets: (date, depthsum, depths)
        self.rolling_window_size = 0
        with open(prefix + ".csv") as f:
            for line in f:
                line = line.strip()
                if line.startswith("Start") or not line:
                    continue
                parts = line.split(",")
                date = datetime.fromisoformat(parts[0].replace(".", "-"))
                depthsum = int(parts[1])
                depths = int(parts[2])
                self.data.append((date, depthsum, depths))

        self.data.sort(key=lambda x: x[0])
        self.date = [item[0] for item in self.data]
        self.depthsum = [item[1] for item in self.data]
        self.depths = [item[2] for item in self.data]

        self.labels = []  # pairs: (date, label)
        if labels:
            with open(labels) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(",")
                    date = datetime.fromisoformat(parts[0].replace(".", "-"))
                    label = parts[1]
                    self.labels.append((date, label))
        self.labels.sort(key=lambda x: x[0])

    def calculate_rolling_averages(self, window_days=7):
        self.rolling_window_size = window_days
        self.rolling_dates = []
        self.rolling_depth = []

        window = collections.deque()
        sum_depthsum = sum_depths = 0

        started_rolling = False
        window_delta = timedelta(days=window_days)
        for item in self.data:
            current_date, depthsum, depths = item
            window.append(item)
            sum_depthsum += depthsum
            sum_depths += depths

            while window and current_date - window[0][0] >= window_delta:
                _, old_depthsum, old_depths = window.popleft()
                sum_depthsum -= old_depthsum
                sum_depths -= old_depths
                if not started_rolling:
                    started_rolling = True
                    self.rolling_dates = self.rolling_dates[-1:]
                    self.rolling_depth = self.rolling_depth[-1:]

            depth_avg = (sum_depthsum / sum_depths) if sum_depths else 0

            self.rolling_dates.append(current_date)
            self.rolling_depth.append(depth_avg)

    def create_graph(self, plot_scatter=True):
        dotSize, smallDotSize, lineWidth = 20, 4, 1.8
        if len(self.date) >= 100:
            dotSize, smallDotSize = 10, 3

        fig, ax = plt.subplots(figsize=(12, 7))
        yColor, depthColor, rollingDepthColor = "black", "blue", "darkblue"

        plot_rolling = self.rolling_window_size >= 1
        if plot_scatter:
            raw_depth_avg = [
                (self.depthsum[i] / self.depths[i]) if self.depths[i] else 0
                for i in range(len(self.depths))
            ]
            point_size = smallDotSize * 1.5 if plot_rolling else dotSize
            scatter_alpha = 0.4 if plot_rolling else 1.0
            depth_scatter_label = "Book Exit Depth" if not plot_rolling else None
            ax.scatter(
                self.date,
                raw_depth_avg,
                label=depth_scatter_label,
                color=depthColor,
                s=point_size,
                alpha=scatter_alpha,
            )

        if plot_rolling:
            depth_label = f"Book Exit Depth ({self.rolling_window_size}-day avg)"
            ax.plot(
                self.rolling_dates,
                self.rolling_depth,
                label=depth_label,
                color=rollingDepthColor,
                linewidth=lineWidth,
            )

        ax.set_ylabel("depth", color=yColor)
        ax.tick_params(axis="y", labelcolor=yColor)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        ax.grid(True, which="major", axis="y", alpha=0.3, linewidth=0.5)
        fig.autofmt_xdate(rotation=30, ha="right")
        plt.setp(ax.get_xticklabels(), fontsize=8)

        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
        for d, l in self.labels:
            if mdates.date2num(d) >= xmin and mdates.date2num(d) <= xmax:
                ax.axvline(
                    x=d, color="lightgray", linestyle="--", linewidth=1, alpha=0.7
                )
                ax.text(
                    x=d,
                    y=0.999 * ymax,
                    s=" " + l,
                    verticalalignment="top",
                    fontsize=4,
                    color="gray",
                )

        ax.legend(fontsize="small")
        plt.title(f"Engine Depth Statistics for {self.prefix}.csv")
        plt.tight_layout(rect=[0, 0.03, 1, 0.98])

        if self.rolling_window_size >= 1:
            save_path = self.prefix + f"_d{self.rolling_window_size}" + ".png"
        else:
            save_path = self.prefix + ".png"
        plt.savefig(save_path, dpi=300)
        print(f"Plot saved to {save_path}")
        plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Plot depth data with optional rolling average.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "filename",
        nargs="?",
        help="CSV file with depth statistics over time",
        default="results.csv",
    )
    parser.add_argument(
        "--labels",
        default=None,
        help="Optional csv file with x-axis labels.",
    )
    parser.add_argument(
        "--rolling",
        type=int,
        default=30,
        help="Number of days for the rolling average window. Set to 0 to disable rolling average.",
    )
    parser.add_argument(
        "--hide-scatter",
        action="store_true",
        help="Do not show the raw daily scatter points.",
    )
    args = parser.parse_args()
    prefix, _, _ = args.filename.partition(".")
    data = depthdata(prefix, args.labels)
    if args.rolling >= 1:
        data.calculate_rolling_averages(args.rolling)

    data.create_graph(not args.hide_scatter)
