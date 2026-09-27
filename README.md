# Education in Lebanese towns and villages

A Streamlit dashboard for the MSBA325 assignment. It shows how illiteracy, school dropout, schools and
universities differ between Lebanon's governorates, districts and towns.

**Live app:** https://educationinlebanon-auczamhmgiu674ark2ko6b.streamlit.app

**Repository:** https://github.com/jadbeayni/education_in_lebanon

## How it works
- Two linked filters in the sidebar. Choose governorates and the district list narrows to districts inside them;
  districts that no longer belong to the selection are dropped automatically.
- The charts go one step deeper as you narrow the selection: governorates, then districts, then individual towns.
- Views: a map and a ranking of illiteracy, illiteracy against school dropout, and public and private schools.
- The design reasoning for both filters is on the page under "Design notes".

## Data
Two datasets from the AUB linked-data portal (PKGCubes Publisher), `Educational_Level-Lebanon-2023` and
`Educational_Resources-Lebanon-2023`, joined by town. They come from the Rural Development module of the IMPACT
platform (Central Inspection, Lebanon), where municipalities report town-level indicators, so the figures are
approximate. Cleaning is in `data.py` and summarised at the bottom of the page. The "public school coverage index"
column is not used because its definition is unclear. Boundary shapes come from geoBoundaries and carry no data.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Files
| File | Purpose |
|---|---|
| `app.py` | Page layout, filters and text |
| `data.py` | Loading, cleaning, joining and the drill-down table |
| `charts.py` | The four Plotly figures |
| `theme.py` | Chart colours |
| `data/` | The two portal exports and the boundary GeoJSON |
