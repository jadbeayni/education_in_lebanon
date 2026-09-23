"""Lebanon Education Atlas: an interactive companion to the MSBA325 Plotly assignment."""
import numpy as np
import streamlit as st

import charts
from data import (SHAPE_TO_GOV, corr, describe_r, districts_for, drill_table,
                  filter_towns, load_geojson, load_towns)
from theme import CSS, html

st.set_page_config(page_title="Lebanon Education Atlas", layout="wide", initial_sidebar_state="collapsed")
st.markdown(CSS, unsafe_allow_html=True)

towns, audit = load_towns()
geojson = load_geojson()

# ------------------------------------------------------------ reference numbers
gov_stats = towns.groupby("governorate").agg(illit=("illiterate", "mean"), schools=("schools", "mean"), n=("town", "count"))
hi, lo = gov_stats["illit"].idxmax(), gov_stats["illit"].idxmin()
ratio = gov_stats.loc[hi, "illit"] / gov_stats.loc[lo, "illit"]
nat_illit = towns["illiterate"].mean()
nat_schools = towns["schools"].mean()

dist_stats = towns.groupby("district").agg(illit=("illiterate", "mean"), schools=("schools", "mean"), n=("town", "count"))
dist_stats = dist_stats[dist_stats["n"] >= 5]
r_gov = gov_stats["illit"].corr(gov_stats["schools"])
r_dist = dist_stats["illit"].corr(dist_stats["schools"])
r_town = corr(towns["schools"], towns["illiterate"])


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def signed(x: float) -> str:
    return f"{x:+.2f}".replace("-", "−")


# ------------------------------------------------------------------------- hero
st.markdown(html(f"""
<div class="hero">
<div class="eyebrow">Lebanon &middot; Education &middot; Town-level data, 2023</div>
<h1>Same country. <em>{ratio:.1f}&times;</em> the illiteracy.</h1>
<p>Adult illiteracy in {hi} is {ratio:.1f} times the rate in {lo}. The obvious explanation is that some regions
simply have fewer schools. This page tests that idea town by town, and the answer depends on how closely you look.</p>
</div>
"""), unsafe_allow_html=True)

# ---------------------------------------------------------------------- filters
st.markdown('<div class="section">Explore</div>', unsafe_allow_html=True)
st.markdown('<div class="helper">Choose one or more governorates, then narrow to districts inside them. '
            'Every chart and number below follows your selection. Leave both empty to see all of Lebanon.</div>',
            unsafe_allow_html=True)

f1, f2, f3 = st.columns([1.1, 1.1, 1])
with f1:
    gov_sel = st.multiselect("Governorate", sorted(towns["governorate"].unique()), key="gov",
                             placeholder="All governorates")

# Linked control: the district list depends on the governorates chosen. Districts picked earlier
# that no longer belong to the new scope are dropped, so the two widgets can never contradict each other.
dist_options = districts_for(towns, gov_sel)
st.session_state["dist"] = [d for d in st.session_state.get("dist", []) if d in dist_options]
with f2:
    dist_sel = st.multiselect("District", dist_options, key="dist",
                              placeholder="All districts" + (" in selection" if gov_sel else ""))

sel = filter_towns(towns, gov_sel, dist_sel)
level_word = "town" if dist_sel else "district" if gov_sel else "governorate"
with f3:
    st.markdown(html(f"""
    <div class="tile-label" style="margin-top:.35rem">Viewing</div>
    <div style="color:#f4f3ee;font-size:1.05rem;margin-top:.15rem">{len(sel):,} of {len(towns):,} towns</div>
    <div class="tile-sub">Ranking drills down to <b>{level_word}s</b></div>
    """), unsafe_allow_html=True)

# -------------------------------------------------------------------------- KPIs
sel_illit = sel["illiterate"].mean()
sel_schools = sel["schools"].mean()
r_sel = corr(sel["schools"], sel["illiterate"])
diff = sel_illit - nat_illit
delta = "Lebanon-wide average" if abs(diff) < 0.05 else f"{'&#9650;' if diff > 0 else '&#9660;'} {abs(diff):.1f} pts vs. Lebanon ({nat_illit:.1f}%)"

k = st.columns(4)
tiles = [
    ("Towns in view", f"{len(sel):,}", "", f"{plural(sel['governorate'].nunique(), 'governorate')} \u00b7 {plural(sel['district'].nunique(), 'district')}"),
    ("Avg. illiteracy", f"{sel_illit:.1f}", "%", delta),
    ("Schools per town", f"{sel_schools:.1f}", "", f"Lebanon average: {nat_schools:.1f}"),
    ("Schools vs. illiteracy", "n/a" if np.isnan(r_sel) else f"r = {signed(r_sel)}", "", describe_r(r_sel, len(sel))),
]
for col, (label, value, unit, sub) in zip(k, tiles):
    col.markdown(html(f"""
    <div class="tile"><div class="tile-label">{label}</div>
    <div class="tile-value">{value}<small>{unit}</small></div>
    <div class="tile-sub">{sub}</div></div>
    """), unsafe_allow_html=True)

CFG = {"displayModeBar": False}
st.write("")

# ------------------------------------------------------------- map + ranked bars
c1, c2 = st.columns([5, 7], gap="large")
with c1:
    st.markdown('<div class="chart-title">Where illiteracy concentrates</div>'
                '<div class="chart-note">Average % illiterate by governorate, for the towns in view. Grey = outside your selection.</div>',
                unsafe_allow_html=True)
    st.plotly_chart(charts.map_fig(sel, geojson, SHAPE_TO_GOV), width="stretch", config=CFG)

table, level, total = drill_table(sel, gov_sel, dist_sel)
with c2:
    title = {"governorate": "Illiteracy by governorate", "district": "Illiteracy by district", "town": "Highest-illiteracy towns"}[level]
    note = ("Whiskers show the standard error; <b>n</b> is the number of towns behind each average."
            if level != "town" else f"Showing the {len(table)} highest of {total} towns in the selected districts.")
    st.markdown(f'<div class="chart-title">{title}</div><div class="chart-note">{note}</div>', unsafe_allow_html=True)
    st.plotly_chart(charts.bar_fig(table, level), width="stretch", config=CFG)

# ----------------------------------------------------------------------- scatter
st.markdown('<div class="section">Do schools explain it?</div>', unsafe_allow_html=True)
s1, s2 = st.columns([8, 4], gap="large")
with s1:
    st.markdown('<div class="chart-title">Schools vs. illiteracy, every town</div>'
                '<div class="chart-note">Your selection in blue; all other towns stay visible in grey for context. '
                'A small horizontal jitter separates towns with identical school counts.</div>', unsafe_allow_html=True)
    st.plotly_chart(charts.scatter_fig(towns, sel), width="stretch", config=CFG)
with s2:
    if np.isnan(r_sel):
        headline, body = "n/a", "Select a larger area: correlation needs at least 8 towns with varying school counts."
    else:
        headline = f"r = {signed(r_sel)}"
        direction = ("Towns with more schools tend to have <i>higher</i> illiteracy." if r_sel > 0.1
                     else "Towns with more schools tend to have <i>lower</i> illiteracy." if r_sel < -0.1
                     else "Knowing how many schools a town has tells you almost nothing about its illiteracy rate.")
        body = f"Across the {len(sel):,} towns in view there is {describe_r(r_sel, len(sel))}. {direction}"
    st.markdown(html(f"""
    <div class="reading"><div class="tile-label">Reading your selection</div>
    <div class="r">{headline}</div><p>{body}</p>
    <p style="color:#8d8c85;font-size:.85rem">r runs from &minus;1 to +1; values near 0 mean no linear relationship.</p></div>
    """), unsafe_allow_html=True)

# ---------------------------------------------------------------------- insights
st.markdown('<div class="section">What the data says</div>', unsafe_allow_html=True)
i1, i2 = st.columns(2, gap="large")
i1.markdown(html(f"""
<div class="card accent"><h4>A gap that survives the uncertainty</h4>
<div class="big">{ratio:.1f}&times;</div>
<p>{hi} averages {gov_stats.loc[hi, 'illit']:.1f}% illiteracy ({gov_stats.loc[hi, 'n']} towns); {lo} averages
{gov_stats.loc[lo, 'illit']:.1f}% ({gov_stats.loc[lo, 'n']} towns). The whiskers on the ranking chart show that even
{hi}'s smaller sample leaves it clearly above {lo}, so the gap is not a sampling accident.</p></div>
"""), unsafe_allow_html=True)
i2.markdown(html(f"""
<div class="card accent"><h4>The finer you look, the weaker the link gets</h4>
<p>Correlation between schools and illiteracy, at three levels of detail:</p>
<p><b>Governorates</b> (7): <b>{signed(r_gov)}</b> &nbsp;&middot;&nbsp; <b>Districts</b> ({len(dist_stats)}): <b>{signed(r_dist)}</b>
&nbsp;&middot;&nbsp; <b>Towns</b> ({len(towns):,}): <b>{signed(r_town)}</b></p>
<p>Regions with more illiteracy tend to have more schools per town. That is a settlement effect (many small
villages, each needing its own school), not evidence that schools cause illiteracy. Use the filters to watch it dissolve.</p></div>
"""), unsafe_allow_html=True)

# ---------------------------------------------------------------- design notes
st.markdown('<div class="section">Design notes</div>', unsafe_allow_html=True)
with st.expander("Governorate selector: why a multiselect"):
    st.markdown("""
**Question it answers.** *Is the pattern national, or driven by a few regions?* Reading two regions side by side
(say Baalbek-Hermel against Mount Lebanon) is the comparison that reveals the gap.

**Why this widget.** A single-choice dropdown or radio group forces one region at a time, so the reader has to remember
one chart while looking at the next. Seven checkboxes would take a permanent block of the page. A multiselect
holds any number of regions in one compact control, and an empty selection means "all of Lebanon", so the page opens on
the national picture. Clicking the map was tempting but is imprecise and not keyboard accessible.

**Course concept: focusing attention while keeping context.** Choosing regions highlights them in colour on the map and
scatter, while everything else fades to grey instead of disappearing. The reader focuses without losing the reference frame.
""")
with st.expander("District selector: why a dependent multiselect"):
    st.markdown("""
**Question it answers.** *Inside a region, is the gap spread evenly or concentrated in a few districts?* It also lets
the reader test whether the schools-and-illiteracy relationship survives at a finer grain.

**Why this widget.** A slider suits numbers, not named places, and a free-text box makes people guess spellings.
The district list is *linked*: it shows only districts inside the chosen governorates, so at most a handful of options
appear instead of all 25, and impossible combinations (Tyre inside Akkar) cannot be built. Picking districts then
drills the ranking chart one level further, down to individual towns.

**Course concept: reducing clutter through progressive disclosure.** The reader gets the overview first (governorates),
then zooms (districts), then details (towns), and never faces more than the next step's worth of choices.
""")

# ------------------------------------------------------------------------ about
st.markdown('<div class="section">About the data</div>', unsafe_allow_html=True)
st.markdown(html(f"""
<div class="foot"><b>Source.</b> AUB linked-data portal (PKGCubes Publisher), datasets <i>Educational_Level-Lebanon-2023</i> and
<i>Educational_Resources-Lebanon-2023</i>, originally published by Impact Open Data (impact.cib.gov.lb) and joined on town.
Each row is one town; percentages describe residents' highest education level.<br>
<b>Cleaning.</b> Of {audit['raw']:,} towns, {audit['no_data']} had no attainment figures, {audit['bad_sum']} reported shares that do not
sum to roughly 100% (one summed to 13,200%), and {audit['missing_illiteracy']} lacked an illiteracy value. {audit['final']:,} towns remain.<br>
<b>Limits.</b> A single-year snapshot. Averages are unweighted by population (town populations are not in the data).
Beirut has no towns in the source. Boundary shapes are from geoBoundaries and carry no data.</div>
"""), unsafe_allow_html=True)
