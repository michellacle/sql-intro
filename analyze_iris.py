from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt


DATABASE_PATH = Path(__file__).with_name("iris.duckdb")
VISUALIZATION_PATH = Path(__file__).with_name("iris_analytics.png")

ANALYSES = [
    (
        "Dataset overview",
        """
        SELECT COUNT(*) AS flower_count,
               COUNT(DISTINCT Species) AS species_count
        FROM iris
        """,
    ),
    (
        "Flowers per species",
        """
        SELECT Species, COUNT(*) AS flower_count
        FROM iris
        GROUP BY Species
        ORDER BY Species
        """,
    ),
    (
        "Measurement summary by species",
        """
        SELECT Species,
               ROUND(AVG(SepalLengthCm), 2) AS avg_sepal_length,
               ROUND(AVG(PetalLengthCm), 2) AS avg_petal_length,
               MIN(PetalLengthCm) AS shortest_petal,
               MAX(PetalLengthCm) AS longest_petal
        FROM iris
        GROUP BY Species
        ORDER BY avg_petal_length DESC
        """,
    ),
    (
        "Flowers with petals at least 5 cm long",
        """
        SELECT Species, COUNT(*) AS flower_count
        FROM iris
        WHERE PetalLengthCm >= 5
        GROUP BY Species
        ORDER BY flower_count DESC, Species
        """,
    ),
    (
        "Petal length/width correlation by species",
        """
        SELECT Species,
               ROUND(CORR(PetalLengthCm, PetalWidthCm), 3) AS correlation
        FROM iris
        GROUP BY Species
        ORDER BY Species
        """,
    ),
    (
        "Three longest-petaled flowers per species",
        """
        SELECT Species, PetalLengthCm, PetalWidthCm
        FROM iris
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY Species
            ORDER BY PetalLengthCm DESC
        ) <= 3
        ORDER BY Species, PetalLengthCm DESC
        """,
    ),
]


def create_visual_report(connection) -> None:
    summary = connection.execute(
        """
        SELECT Species,
               COUNT(*) AS flower_count,
               AVG(PetalLengthCm) AS avg_petal_length,
               MIN(PetalLengthCm) AS shortest_petal,
               MAX(PetalLengthCm) AS longest_petal,
               COUNT(*) FILTER (WHERE PetalLengthCm >= 5) AS long_petal_count
        FROM iris
        GROUP BY Species
        ORDER BY Species
        """
    ).fetchall()
    correlations = dict(
        connection.execute(
            """
            SELECT Species, CORR(PetalLengthCm, PetalWidthCm)
            FROM iris
            GROUP BY Species
            """
        ).fetchall()
    )
    measurements = connection.execute(
        "SELECT Species, PetalLengthCm, PetalWidthCm FROM iris"
    ).fetchall()

    species = [row[0] for row in summary]
    labels = [name.removeprefix("Iris-") for name in species]
    colors = ["#168C82", "#E07A5F", "#52627A"]

    figure, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    figure.suptitle("Iris Dataset: DuckDB Analytics", fontsize=17, fontweight="bold")

    axes[0, 0].bar(labels, [row[1] for row in summary], color=colors)
    axes[0, 0].set_title("Flowers by species")
    axes[0, 0].set_ylabel("Flower count")

    averages = [row[2] for row in summary]
    ranges = [
        [average - row[3] for average, row in zip(averages, summary)],
        [row[4] - average for average, row in zip(averages, summary)],
    ]
    axes[0, 1].bar(labels, averages, yerr=ranges, capsize=5, color=colors)
    axes[0, 1].set_title("Petal length by species (mean and range)")
    axes[0, 1].set_ylabel("Petal length (cm)")

    for name, color in zip(species, colors):
        points = [row for row in measurements if row[0] == name]
        axes[1, 0].scatter(
            [row[1] for row in points],
            [row[2] for row in points],
            label=f"{name.removeprefix('Iris-')} (r={correlations[name]:.2f})",
            color=color,
            alpha=0.7,
            edgecolors="white",
            linewidths=0.4,
        )
    axes[1, 0].set_title("Petal length vs. width")
    axes[1, 0].set_xlabel("Petal length (cm)")
    axes[1, 0].set_ylabel("Petal width (cm)")
    axes[1, 0].legend(frameon=False)

    long_petal_counts = [row[5] for row in summary]
    bars = axes[1, 1].bar(labels, long_petal_counts, color=colors)
    axes[1, 1].bar_label(bars, padding=3)
    axes[1, 1].set_title("Flowers with petals at least 5 cm")
    axes[1, 1].set_ylabel("Flower count")

    for axis in axes.flat:
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        axis.grid(axis="y", color="#D9DEDF", linewidth=0.7, alpha=0.7)
        axis.set_axisbelow(True)

    figure.savefig(VISUALIZATION_PATH, dpi=160, facecolor="white")
    plt.close(figure)
    print(f"\nVisual report saved to {VISUALIZATION_PATH.name}")


def main() -> None:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"DuckDB database not found: {DATABASE_PATH}")

    with duckdb.connect(str(DATABASE_PATH), read_only=True) as connection:
        for title, query in ANALYSES:
            print(f"\n{title}")
            connection.sql(query).show()
        create_visual_report(connection)


if __name__ == "__main__":
    main()