#!/usr/bin/env python3

import argparse
import time
from statistics import mean, stdev
import numpy as np
import polars as pl
import pandas as pd


def build_dataframe(n_rows: int, n_cols: int, seed: int = 0):
    rng = np.random.default_rng(seed)
    data = {f"col_{i}": rng.integers(0, 1_000_000, n_rows) for i in range(n_cols)}
    data["value"] = rng.random(n_rows)
    return pl.DataFrame(data), pd.DataFrame(data)


# -------------------- POLARS --------------------

def workload_polars(df: pl.DataFrame, mode: str) -> pl.DataFrame:
    lf = df.lazy() if mode == "lazy" else df

    if mode != "lazy":
        # eager requires reassignment at every step
        lf = lf.filter(pl.col("value") > 0.2)
        lf = lf.filter(pl.col("col_0") % 2 == 0)
        lf = lf.with_columns([
            (pl.col("col_1") * 2 + pl.col("col_2")).alias("derived_1"),
            (pl.col("value").log1p() * 100).alias("derived_2"),
        ])
        lf = lf.with_columns([
            (pl.col("derived_1") + pl.col("derived_2")).alias("score"),
        ])
        lf = lf.with_columns([
            (pl.col("score") / pl.col("col_3").max()).alias("norm_score"),
        ])
        lf = lf.group_by([(pl.col("col_0") % 5).alias("g1"), (pl.col("col_1") % 3).alias("g2")]).agg([
            pl.mean("score").alias("score_mean"),
            pl.median("value").alias("value_med"),
            pl.max("col_2").alias("max_c2"),
        ])
        lf = lf.sort("score_mean", descending=True)
        lf = lf.rename({"g1": "group_a", "g2": "group_b"})
        return lf
    else:
        return (
            lf.filter(pl.col("value") > 0.2)
              .filter(pl.col("col_0") % 2 == 0)
              .with_columns([
                  (pl.col("col_1") * 2 + pl.col("col_2")).alias("derived_1"),
                  (pl.col("value").log1p() * 100).alias("derived_2"),
              ])
              .with_columns((pl.col("derived_1") + pl.col("derived_2")).alias("score"))
              .with_columns((pl.col("score") / pl.col("col_3").max()).alias("norm_score"))
              .group_by([(pl.col("col_0") % 5).alias("g1"), (pl.col("col_1") % 3).alias("g2")])
              .agg([
                  pl.mean("score").alias("score_mean"),
                  pl.median("value").alias("value_med"),
                  pl.max("col_2").alias("max_c2"),
              ])
              .sort("score_mean", descending=True)
              .rename({"g1": "group_a", "g2": "group_b"})
              .collect()
        )


# -------------------- PANDAS --------------------

def workload_pandas(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["value"] > 0.2]
    df = df[df["col_0"] % 2 == 0].copy()

    df["derived_1"] = df["col_1"] * 2 + df["col_2"]
    df["derived_2"] = np.log1p(df["value"]) * 100
    df["score"] = df["derived_1"] + df["derived_2"]
    df["norm_score"] = df["score"] / df["col_3"].max()

    df["group_a"] = df["col_0"] % 5
    df["group_b"] = df["col_1"] % 3

    grouped = df.groupby(["group_a", "group_b"]).agg(
        score_mean=("score", "mean"),
        value_med=("value", "median"),
        max_c2=("col_2", "max"),
    ).reset_index()

    return grouped.sort_values("score_mean", ascending=False)


# -------------------- BENCHMARK --------------------

def timeit(func, *args, repeats: int = 3) -> list[float]:
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        func(*args)
        times.append(time.perf_counter() - t0)
    return times


def fmt_stats(times: list[float]) -> str:
    return f"{mean(times):.3f} s ± {stdev(times):.3f}" if len(times) > 1 else f"{times[0]:.3f} s"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--rows", type=int, default=10000000)
    parser.add_argument("-c", "--cols", type=int, default=20)
    parser.add_argument("-n", "--repeats", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


def main():
    args = parse_args()
    print(f"Generating {args.rows:,} rows × {args.cols + 1} cols...")
    df_polars, df_pandas = build_dataframe(args.rows, args.cols, seed=args.seed)

    print("Warming up...")
    workload_polars(df_polars, "eager")
    workload_polars(df_polars, "lazy")
    workload_pandas(df_pandas)

    print(f"\nBenchmarking {args.repeats}× each mode…")

    times_polars_eager = timeit(workload_polars, df_polars, "eager", repeats=args.repeats)
    times_polars_lazy = timeit(workload_polars, df_polars, "lazy", repeats=args.repeats)
    times_pandas = timeit(workload_pandas, df_pandas, repeats=args.repeats)

    print("\nResults")
    print("-" * 60)
    print(f"Polars (eager):       {fmt_stats(times_polars_eager)}")
    print(f"Polars (lazy):        {fmt_stats(times_polars_lazy)}")
    print(f"Pandas:               {fmt_stats(times_pandas)}")

    print("\nSpeed-up ratios:")
    print(f"Pandas vs Polars eager:   ×{mean(times_pandas) / mean(times_polars_eager):.2f}")
    print(f"Pandas vs Polars lazy:    ×{mean(times_pandas) / mean(times_polars_lazy):.2f}")
    print(f"Polars lazy vs eager:     ×{mean(times_polars_lazy) / mean(times_polars_eager):.2f}")


if __name__ == "__main__":
    main()
