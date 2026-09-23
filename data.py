"""Loading, cleaning and joining the two AUB linked-data cubes."""
from __future__ import annotations

import json
from pathlib import Path

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
            "dropout": lvl["PercentageofSchooldropout"],
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
    df = df.merge(res[["town", "schools", "public_schools", "private_schools", "universities"]], on="town", how="left")
    audit["unmatched"] = int(df["schools"].isna().sum())
    audit["final"] = len(df)
    reported = df[LEVELS].stack()
    audit["round5"] = float((reported % 5 == 0).mean())   # share of reported percentages that are multiples of 5

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


# ------------------------------------------------------------------- selection
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


def level_of(governorates: list[str], districts: list[str]) -> str:
    """Grain shown in the charts: one step below whatever the reader has selected."""
    return "town" if districts else "district" if governorates else "governorate"


def units_table(sel: pd.DataFrame, level: str) -> pd.DataFrame:
    """One row per governorate / district / town in the selection, sorted by illiteracy.

    Governorate and district rows are averages of their towns' figures; town rows are the raw figures.
    """
    cols = {"illiterate": "illiterate", "dropout": "dropout", "university": "university",
            "public_schools": "public", "private_schools": "private"}
    if level == "town":
        t = sel.rename(columns=cols)
        out = t[["town", "district", "illiterate", "dropout", "university", "public", "private", "universities"]].copy()
        out = out.rename(columns={"town": "label", "district": "context"})
        out["n"] = 1
    else:
        g = sel.groupby(level).agg(n=("town", "count"), illiterate=("illiterate", "mean"), dropout=("dropout", "mean"),
                                   university=("university", "mean"), public=("public_schools", "mean"),
                                   private=("private_schools", "mean"), universities=("universities", "sum")).reset_index()
        out = g.rename(columns={level: "label"}).assign(context="")
    return out.sort_values("illiterate", ascending=False).reset_index(drop=True)
