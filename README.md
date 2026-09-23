# Lebanon Education Atlas

An interactive Streamlit companion to the MSBA325 Plotly assignment. It asks one question:
**do school counts explain illiteracy in Lebanon, and does the answer change with how closely you look?**

**Live app:** _add the Streamlit Community Cloud link here after deploying_

## What it does
- Two **linked** filters: choose governorates, and the district list narrows to districts inside them.
  Districts that stop being valid are dropped automatically.
- Three coordinated views: a governorate choropleth, a ranked bar chart that drills from
  governorates to districts to individual towns, and a schools-vs-illiteracy scatter with a live correlation.
- Design justifications for both filters are on the page (Design notes).

## Data
Two RDF Data Cubes from the AUB linked-data portal (PKGCubes Publisher), `Educational_Level-Lebanon-2023` and
`Educational_Resources-Lebanon-2023` (published by Impact Open Data), joined on town. Cleaning is documented in
`data.py` and summarised at the bottom of the page. Boundary shapes come from geoBoundaries and carry no data.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Files
| File | Purpose |
|---|---|
| `app.py` | Page layout, widgets and linking logic |
| `data.py` | Loading, cleaning, joining; drill-down and statistics helpers |
| `charts.py` | The three Plotly figures |
| `theme.py` | Colours and CSS (single source of truth for the look) |
| `data/` | The two portal exports and the boundary GeoJSON |
