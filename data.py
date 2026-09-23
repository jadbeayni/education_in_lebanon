"""Loading, cleaning and joining the two AUB linked-data cubes."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"

LEVEL_COLS = {
    "PercentageofEducationlevelofresidents-illeterate": "illiterate",
    "PercentageofEducationlevelofresidents-elementary": "elementary",
    "PercentageofEducationlevelofresidents-intermediate": "intermediate",
    "PercentageofEducationlevelofresidents-vocational": "vocational",
    "PercentageofEducationlevelofresidents-secondary": "secondary",
    "PercentageofEducationlevelofresidents-university": "university",
    "PercentageofEducationlevelofresidents-highereducation": "higher_ed",
}
LEVELS = list(LEVEL_COLS.values())

# geoBoundaries shape name -> governorate label used in the education data
SHAPE_TO_GOV = {
    "Baalbek-Hermel": "Baalbek-Hermel",
    "Beyrouth": "Beirut",
    "Liban-Nord": "North",
    "Mont-Liban": "Mount Lebanon",
    "Keserwan-Jbeil": "Mount Lebanon",
    "Liban-Sud": "South",
    "Nabatîyé": "Nabatieh",
    "Béqaa": "Beqaa",
    "Aakkâr": "Akkar",
}


def _label(uri: str, strip: tuple[str, ...]) -> str:
    """Readable name from a DBpedia URI; repairs UTF-8 that was double-encoded upstream."""
    s = uri.rstrip("/").split("/")[-1].replace("_", " ")
    try:
        s = s.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    for token in strip:
        s = s.replace(token, "")
    return s.strip(" ,")


@st.cache_data(show_spinner=False)
def load_towns() -> tuple[pd.DataFrame, dict]:
    """Return one clean row per town plus an audit trail of every row dropped."""
    lvl = pd.read_csv(DATA_DIR / "education_level.csv").rename(columns=LEVEL_COLS)
    res = pd.read_csv(DATA_DIR / "education_resources.csv")

    df = pd.DataFrame(
        {
            "town": lvl["Town"],
            "governorate": lvl["refArea Governorate"].map(lambda u: _label(u, ("Governorate", "page/"))),
            "district": lvl["refArea District"].map(lambda u: _label(u, (" District", ", Lebanon"))),
            **{c: lvl[c] for c in LEVELS},
        }
    )
    audit = {"raw": len(df)}

    # 1. towns with no attainment figures at all (blank in the source, not zero)
    has_data = df[LEVELS].notna().any(axis=1)
    audit["no_data"] = int((~has_data).sum())
    df = df[has_data].copy()

    # 2. attainment shares must sum to ~100%; anything else is a data-entry error
    total = df[LEVELS].sum(axis=1)
    ok = total.between(90, 110)
    audit["bad_sum"] = int((~ok).sum())
    df = df[ok].copy()

    # 3. every analysis below is about illiteracy, so the figure itself must exist
    has_illit = df["illiterate"].notna()
    audit["missing_illiteracy"] = int((~has_illit).sum())
    df = df[has_illit].copy()

    # 4. a district that appears under two governorates is a labelling error:
    #    keep the towns under its dominant governorate, drop the strays
    modal = df.groupby("district")["governorate"].agg(lambda s: s.value_counts().idxmax())
    consistent = df["governorate"] == df["district"].map(modal)
    audit["mislabelled"] = int((~consistent).sum())
    df = df[consistent].copy()

    # 5. join the school / university counts (same 1,137 towns in both cubes)
    res = pd.DataFrame(
        {
            "town": res["Town"],
            "public_schools": res["Type and size of educational resources - public schools"],
            "private_schools": res["Type and size of educational resources - private schools"],
            "universities": res["Type and size of educational resources - universities"],
        }
    )
    res["schools"] = res["public_schools"] + res["private_schools"]
    df = df.merge(res[["town", "schools", "universities"]], on="town", how="left")
    audit["unmatched"] = int(df["schools"].isna().sum())
    audit["final"] = len(df)

    return df.reset_index(drop=True), audit


def _wind(ring: list, clockwise: bool) -> list:
    """Return the ring wound in the requested direction (shoelace sign decides)."""
    signed_area = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:]))
    is_clockwise = signed_area < 0
    return ring if is_clockwise == clockwise else ring[::-1]


@st.cache_resource(show_spinner=False)
def load_geojson() -> dict:
    """Boundaries with Plotly-style winding.

    The GeoJSON spec wants exterior rings counter-clockwise, but Plotly's projection-based maps
    (d3-geo) want them clockwise. With the spec's winding, each polygon is read as "the whole globe
    except this shape" and the map fills a giant rectangle instead of the country.
    """
    with open(DATA_DIR / "lebanon_governorates.geojson", encoding="utf-8") as f:
        gj = json.load(f)
    for feat in gj["features"]:
        feat["id"] = feat["properties"]["shapeName"]
        geom = feat["geometry"]
        polygons = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        for poly in polygons:
            poly[0] = _wind(poly[0], clockwise=True)
            poly[1:] = [_wind(hole, clockwise=False) for hole in poly[1:]]
    return gj


# ---------------------------------------------------------------- statistics
def corr(x: pd.Series, y: pd.Series, min_n: int = 8) -> float:
    """Pearson r, or NaN when there are too few towns or no variation."""
    pair = pd.concat([x, y], axis=1).dropna()
    if len(pair) < min_n or pair.iloc[:, 0].std() == 0 or pair.iloc[:, 1].std() == 0:
        return float("nan")
    return float(np.corrcoef(pair.iloc[:, 0], pair.iloc[:, 1])[0, 1])


def describe_r(r: float, n: int) -> str:
    if np.isnan(r):
        return f"Too few towns ({n}) for a meaningful correlation"
    size = abs(r)
    strength = "no relationship" if size < 0.1 else "a weak" if size < 0.3 else "a moderate" if size < 0.5 else "a strong"
    if size < 0.1:
        return "no relationship"
    return f"{strength} {'positive' if r > 0 else 'negative'} relationship"


def districts_for(towns: pd.DataFrame, governorates: list[str]) -> list[str]:
    scope = towns[towns["governorate"].isin(governorates)] if governorates else towns
    return sorted(scope["district"].unique())


def filter_towns(towns: pd.DataFrame, governorates: list[str], districts: list[str]) -> pd.DataFrame:
    out = towns
    if governorates:
        out = out[out["governorate"].isin(governorates)]
    if districts:
        out = out[out["district"].isin(districts)]
    return out


def drill_table(sel: pd.DataFrame, governorates: list[str], districts: list[str], top_n: int = 15):
    """Rows for the ranked bar chart, one level below the current selection.

    nothing picked        -> governorates
    governorate(s) picked -> districts inside them
    district(s) picked    -> the individual towns (top_n by illiteracy)
    """
    if districts:
        t = sel.nlargest(top_n, "illiterate")
        out = pd.DataFrame({"label": t["town"], "mean": t["illiterate"], "se": 0.0, "n": 1, "context": t["district"]})
        return out.sort_values("mean"), "town", len(sel)
    key = "district" if governorates else "governorate"
    g = sel.groupby(key)["illiterate"].agg(mean="mean", std="std", n="count").reset_index()
    g["se"] = (g["std"] / np.sqrt(g["n"])).fillna(0.0)
    out = g.rename(columns={key: "label"}).assign(context="")
    return out[["label", "mean", "se", "n", "context"]].sort_values("mean"), key, len(g)
