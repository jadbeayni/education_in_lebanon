"""Education in Lebanese towns and villages: interactive companion to the MSBA325 Plotly assignment."""
import streamlit as st

import charts
from data import SHAPE_TO_GOV, districts_for, filter_towns, level_of, load_geojson, load_towns, units_table

st.set_page_config(page_title="Education in Lebanese towns", layout="wide")

towns, audit = load_towns()
geojson = load_geojson()
CFG = {"displayModeBar": False}

# ------------------------------------------------------------------ sidebar filters
st.sidebar.header("Filters")
gov_sel = st.sidebar.multiselect("Governorate", sorted(towns["governorate"].unique()), key="gov",
                                 placeholder="All governorates")

# The district list depends on the governorates chosen. Districts picked earlier that no longer
# belong to the new selection are dropped, so the two filters can never contradict each other.
dist_options = districts_for(towns, gov_sel)
st.session_state["dist"] = [d for d in st.session_state.get("dist", []) if d in dist_options]
dist_sel = st.sidebar.multiselect("District", dist_options, key="dist", placeholder="All districts")
st.sidebar.caption("The district list follows the governorates you pick. "
                   "Leave both empty to see all of Lebanon.")

sel = filter_towns(towns, gov_sel, dist_sel)
level = level_of(gov_sel, dist_sel)
units = units_table(sel, level)
units_all_towns = units_table(sel, "town") if level == "town" else units   # the scatter shows every town

# ------------------------------------------------------------------------- heading
st.title("Education in Lebanese towns and villages")
st.write("How schooling differs between governorates and districts, based on figures reported by "
         "municipalities for 2023. Use the filters on the left to narrow the view. "
         "Every number and chart on this page follows your selection.")


# ---------------------------------------------------------------------------- KPIs
def average(col: str) -> float:
    return float(sel[col].mean())


def delta(col: str):
    if len(sel) == len(towns):
        return None
    return f"{average(col) - towns[col].mean():+.1f} points vs. all towns"


k1, k2, k3, k4 = st.columns(4)
k1.metric("Towns in view", f"{len(sel):,}")
k2.metric("Illiterate residents (average town)", f"{average('illiterate'):.1f}%", delta("illiterate"), delta_color="inverse")
k3.metric("School dropout (average town)", f"{average('dropout'):.1f}%", delta("dropout"), delta_color="inverse")
k4.metric("Towns with a university", f"{int((sel['universities'] > 0).sum())} of {len(sel)}")

# ------------------------------------------------------------------- map and ranking
unit_word = level
st.subheader("Where illiteracy is highest")
left, right = st.columns([5, 6], gap="large")
with left:
    st.markdown("**Average share of illiterate residents, by governorate**")
    st.caption("Each figure is the average of its towns. Grey areas are outside your selection.")
    st.plotly_chart(charts.map_fig(sel, geojson, SHAPE_TO_GOV), width="stretch", config=CFG)
with right:
    title = "Towns with the highest illiteracy" if level == "town" else f"Average share of illiterate residents, by {unit_word}"
    st.markdown(f"**{title}**")
    st.caption(f"Showing the {charts.TOP_N} highest of {len(units)} towns." if level == "town" and len(units) > charts.TOP_N
               else "The number of towns behind each average is shown in brackets.")
    st.plotly_chart(charts.ranking_fig(units, level), width="stretch", config=CFG)

# ---------------------------------------------------------------- dropout and schools
st.subheader("Dropout and schools")
c1, c2 = st.columns(2, gap="large")
with c1:
    st.markdown(f"**Illiteracy and school dropout, by {unit_word}**")
    st.caption(f"Each dot is one {unit_word}. Hover over a dot for its name and figures.")
    st.plotly_chart(charts.dropout_fig(units_all_towns, level), width="stretch", config=CFG)
with c2:
    st.markdown("**Public and private schools**")
    st.caption("Same order as the ranking above, highest illiteracy first.")
    st.plotly_chart(charts.schools_fig(units, level), width="stretch", config=CFG)

if level == "town":
    st.subheader("Towns in the selected districts")
    table = units_all_towns.rename(columns={
        "label": "Town", "context": "District", "illiterate": "Illiterate (%)", "dropout": "Dropout (%)",
        "university": "University (%)", "public": "Public schools", "private": "Private schools",
        "universities": "Universities"}).drop(columns="n")
    st.dataframe(table, hide_index=True, width="stretch")

# -------------------------------------------------------------------- what stands out
g = towns.groupby("governorate").agg(
    n=("town", "count"), illit=("illiterate", "mean"), median=("illiterate", "median"),
    drop=("dropout", "mean"), univ=("university", "mean"),
    schools=("schools", "mean"), has_univ=("universities", lambda s: int((s > 0).sum())))
g["high"] = towns.assign(h=towns["illiterate"] >= 10).groupby("governorate")["h"].mean() * 100
w1, w2 = list(g["illit"].nlargest(2).index)
best = g["illit"].idxmin()
same_two = set(g["drop"].nlargest(2).index) == {w1, w2} == set(g["univ"].nsmallest(2).index)
n_univ = int((towns["universities"] > 0).sum())

st.subheader("What stands out")
st.markdown(
    f"**Illiteracy is concentrated in a few governorates.** In the average {w1} town, {g.loc[w1, 'illit']:.1f}% of residents "
    f"are illiterate, against {g.loc[best, 'illit']:.1f}% in the average {best} town. The typical town looks alike everywhere "
    f"(median {g['median'].min():.0f} to {g['median'].max():.0f}%). What differs is how common high-illiteracy towns are: "
    f"{g.loc[w1, 'high']:.0f}% of towns in {w1} and {g.loc[w2, 'high']:.0f}% in {w2} report at least 10% illiterate residents, "
    f"compared with {g.loc[best, 'high']:.0f}% in {best}.")
if same_two:
    st.markdown(
        f"**The same governorates trail on other measures.** {w1} and {w2} also report the highest school dropout "
        f"({g.loc[w1, 'drop']:.1f}% and {g.loc[w2, 'drop']:.1f}%) and the smallest share of residents with a university education "
        f"({g.loc[w1, 'univ']:.1f}% and {g.loc[w2, 'univ']:.1f}%). {best} reports {g.loc[best, 'drop']:.1f}% dropout "
        f"and {g.loc[best, 'univ']:.1f}% with a university education.")
st.markdown(
    f"**The number of schools does not explain the gap.** {w1} has {g.loc[w1, 'schools']:.1f} schools per town on average and "
    f"{w2} has {g.loc[w2, 'schools']:.1f}, more than {best} ({g.loc[best, 'schools']:.1f}). Universities are rare everywhere: "
    f"only {n_univ} of {len(towns)} towns have one, and only {g.loc['Akkar', 'has_univ']} of Akkar's {int(g.loc['Akkar', 'n'])} towns. "
    "Counting schools says nothing about class size, distance or quality.")

# ------------------------------------------------------------------- design notes
st.subheader("Design notes")
with st.expander("Governorate filter"):
    st.markdown("""
**Question it answers.** Is the pattern the same across regions, or is it driven by one or two governorates?

**Why a multiselect.** A reader often wants to compare regions, for example Akkar with Mount Lebanon. A single-choice
dropdown or a radio button only allows one region at a time. Seven checkboxes would take a lot of space, and clicking the
map is imprecise and cannot be done with a keyboard. Leaving the filter empty shows all of Lebanon, so the page opens on the
national picture.

**Course concept: focusing attention.** The map, the figures at the top and every chart narrow to the chosen governorates,
and the rest of the map turns grey. The reader sees only what they asked about, with the national average still shown
next to the numbers for context.
""")
with st.expander("District filter"):
    st.markdown("""
**Question it answers.** Within a governorate, is illiteracy spread across all districts or concentrated in a few?

**Why a dependent multiselect.** The district list only shows districts inside the chosen governorates, so a reader sees
a handful of options instead of all 25 and cannot build a combination that does not exist, such as a Tyre district inside
Akkar. I considered one long list of every district, which is harder to scan and allows those contradictions, and a slider,
which does not suit named places. Choosing districts also takes the charts one step further down, to individual towns.

**Course concept: reducing clutter.** The page starts with the overview (governorates), moves to districts when a
governorate is chosen, and shows individual towns only when a district is chosen. At each step the reader sees only as much
detail as they asked for.
""")

# ---------------------------------------------------------------------- about the data
st.subheader("About the data")
st.markdown(f"""
- **Source.** AUB linked-data portal (PKGCubes Publisher): the datasets *Educational_Level-Lebanon-2023* and
  *Educational_Resources-Lebanon-2023*, joined by town. They come from the Rural Development module of the IMPACT platform run by
  Lebanon's Central Inspection, which collects town and village indicators directly from municipalities.
- **Estimates.** Because municipalities report the figures, they are approximate: {audit['round5']:.0%} of the reported percentages are
  multiples of 5.
- **Averages.** Governorate and district figures are simple averages of their towns. They are not weighted by population,
  because town populations are not in the data, and a few towns with very high values pull averages up.
- **Cleaning.** Of {audit['raw']:,} towns, {audit['no_data']} had no education figures and {audit['bad_sum']} reported shares that do not
  add up to roughly 100%. {audit['missing_illiteracy']} more had no illiteracy value. {audit['final']:,} towns remain.
- **Not covered.** Beirut has no towns in the data, and the figures are for one year (2023). Boundary shapes come from geoBoundaries.
""")
