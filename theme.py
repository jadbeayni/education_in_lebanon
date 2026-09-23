"""Design tokens and page CSS. Every colour used anywhere in the app is defined here."""

# Surfaces and ink (dark theme)
SURFACE = "#1a1a19"
CARD = "#242423"
GRID = "#333331"
TEXT = "#f4f3ee"
TEXT_2 = "#c3c2b7"
MUTED = "#8d8c85"

# Categorical slots 1 and 2, dark-mode steps (validated together on SURFACE)
BLUE = "#3987e5"
ORANGE = "#d95926"

# Context marks: present, but visibly de-emphasised
CONTEXT = "#5f5e59"
NO_DATA = "#2b2b29"

# Sequential ramp for magnitude: one hue (blue), darkest = low, brightest = high on a dark surface
SEQUENTIAL = ["#104281", "#1c5cab", "#2a78d6", "#5598e7", "#86b6ef", "#b7d3f6"]

FONT = "Inter, system-ui, -apple-system, 'Segoe UI', sans-serif"


def html(block: str) -> str:
    """Strip indentation and blank lines so Markdown never mistakes HTML for a code block."""
    return "\n".join(line.strip() for line in block.strip().splitlines() if line.strip())


CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Inter:wght@400;500;600&display=swap');

.stApp {{ font-family: {FONT}; }}
.block-container {{ max-width: 1240px; padding-top: 2.2rem; padding-bottom: 4rem; }}
#MainMenu, footer {{ visibility: hidden; }}

.eyebrow {{ font-size: .72rem; letter-spacing: .16em; text-transform: uppercase; color: {BLUE}; font-weight: 600; margin-bottom: .6rem; }}
.hero h1 {{ font-family: 'Fraunces', Georgia, serif; font-weight: 600; font-size: 3.1rem; line-height: 1.08; letter-spacing: -.01em; color: {TEXT}; margin: 0 0 .9rem 0; padding: 0; }}
.hero h1 em {{ font-style: normal; color: {BLUE}; }}
.hero p {{ font-size: 1.08rem; color: {TEXT_2}; max-width: 46rem; line-height: 1.6; margin: 0; }}

.section {{ font-size: .72rem; letter-spacing: .16em; text-transform: uppercase; color: {MUTED}; font-weight: 600; margin: 2.6rem 0 .8rem 0; border-top: 1px solid {GRID}; padding-top: 1rem; }}
.helper {{ color: {TEXT_2}; font-size: .95rem; margin: -.2rem 0 1rem 0; }}

.tile {{ background: {CARD}; border: 1px solid {GRID}; border-radius: 10px; padding: 1rem 1.15rem; min-height: 7.6rem; }}
.tile-label {{ font-size: .74rem; letter-spacing: .08em; text-transform: uppercase; color: {MUTED}; font-weight: 600; }}
.tile-value {{ font-family: 'Fraunces', Georgia, serif; font-size: 2.3rem; color: {TEXT}; line-height: 1.15; margin-top: .25rem; }}
.tile-value small {{ font-size: 1.05rem; color: {TEXT_2}; margin-left: 2px; }}
.tile-sub {{ font-size: .85rem; color: {TEXT_2}; margin-top: .15rem; }}

.chart-title {{ font-size: 1.02rem; font-weight: 600; color: {TEXT}; margin: 0 0 .1rem 0; }}
.chart-note {{ font-size: .85rem; color: {MUTED}; margin: 0 0 .4rem 0; }}

.card {{ background: {CARD}; border: 1px solid {GRID}; border-radius: 10px; padding: 1.2rem 1.35rem; min-height: 16rem; }}
.card h4 {{ font-size: 1.05rem; margin: 0 0 .5rem 0; color: {TEXT}; }}
.card p {{ color: {TEXT_2}; font-size: .95rem; line-height: 1.6; margin: 0 0 .5rem 0; }}
.card .big {{ font-family: 'Fraunces', Georgia, serif; font-size: 2.6rem; color: {BLUE}; line-height: 1.1; }}
.card.accent {{ border-left: 3px solid {BLUE}; }}

.reading {{ background: {CARD}; border: 1px solid {GRID}; border-left: 3px solid {ORANGE}; border-radius: 10px; padding: 1.1rem 1.25rem; }}
.reading .r {{ font-family: 'Fraunces', Georgia, serif; font-size: 2.1rem; color: {TEXT}; }}
.reading p {{ color: {TEXT_2}; font-size: .95rem; line-height: 1.55; margin: .35rem 0 0 0; }}

.foot {{ color: {MUTED}; font-size: .82rem; line-height: 1.6; }}
.foot b {{ color: {TEXT_2}; font-weight: 600; }}

div[data-testid="stExpander"] {{ background: {CARD}; border: 1px solid {GRID}; border-radius: 10px; }}
div[data-testid="stMultiSelect"] label p {{ font-weight: 600; color: {TEXT}; }}
</style>
"""
