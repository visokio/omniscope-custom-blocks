"""Clean the orders, then total them per region (and, with a target table, compare with the targets)."""
import pandas as pd
from kedro.pipeline import Pipeline, node


def clean_orders(orders: pd.DataFrame) -> pd.DataFrame:
    df = orders.copy()
    df["Status"] = df["Status"].astype(str).str.strip().str.title()
    return df[df["Status"] != "Cancelled"].reset_index(drop=True)


def summarise(orders: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
    df = orders.copy()
    df["Value"] = df["Quantity"].astype(float) * df["Unit Price"].astype(float)
    out = (df.groupby("Region", as_index=False)
             .agg(Orders=("Order", "nunique"), Units=("Quantity", "sum"), Sales=("Value", "sum")))
    out["Sales"] = out["Sales"].round(2)
    out = out.merge(targets, on="Region", how="left")
    out["Target met"] = out["Sales"] >= out["Target"]
    return out.sort_values("Region").reset_index(drop=True)


def create_clean_pipeline() -> Pipeline:
    return Pipeline([node(clean_orders, "orders", "clean_orders", name="clean_orders")])


def create_pipeline() -> Pipeline:
    return create_clean_pipeline() + Pipeline(
        [node(summarise, ["clean_orders", "targets"], "region_summary", name="summarise")])
