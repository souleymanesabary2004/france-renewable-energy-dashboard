"""Plot helpers and small statistics shared by notebook 03 and the Streamlit app."""
import numpy as np
import pandas as pd

try:                                     # matplotlib is only needed by the notebooks
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    from matplotlib.collections import PatchCollection
    from matplotlib.patches import Polygon as MplPolygon
except ImportError:                      # the Streamlit app only uses the plotly functions below
    mpl = plt = PatchCollection = MplPolygon = None

from . import config as cfg

GROUP_COLOR = {False: "#009E73", True: "#CC79A7"}
GROUP_LABEL = {False: "without nuclear", True: "with nuclear"}
INK = "#222222"
MUTED = "#6B6B6B"
GRID = "#E3E3E3"


def set_style():
    mpl.rcParams.update({
        "figure.dpi": 110, "savefig.dpi": 200, "figure.facecolor": "white", "axes.facecolor": "white",
        "font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold",
        "axes.titlelocation": "left", "axes.labelcolor": INK, "axes.edgecolor": "#B0B0B0",
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
        "grid.linewidth": 0.7, "axes.axisbelow": True, "xtick.color": INK, "ytick.color": INK,
        "legend.frameon": False, "legend.fontsize": 9, "axes.prop_cycle": mpl.cycler(color=list(cfg.COLOR.values())),
    })


def suptitle(fig, title, subtitle=None, y=1.02):
    fig.suptitle(title, x=0.01, y=y, ha="left", fontsize=14, fontweight="bold", color=INK)
    if subtitle:
        fig.text(0.01, y - 0.045, subtitle, ha="left", va="top", fontsize=10, color=MUTED)


def source_note(fig, text="Source: ODRE / data.gouv.fr, monthly regional production by source (2014-2025). Own calculations.",
                y=-0.02):
    fig.text(0.01, y, text, ha="left", va="top", fontsize=8, color=MUTED)


# ------------------------------------------------------------------ text helpers
def n(x, nd=0):
    """number with a space as thousands separator"""
    return f"{x:,.{nd}f}".replace(",", " ")


def direction(delta, up="rose", down="fell", flat="stayed flat", tol=0.0):
    return up if delta > tol else down if delta < -tol else flat


def pick(value, rules, default=""):
    """rules = [(threshold, text), ...] sorted from the highest threshold; first one with value >= threshold wins"""
    for thr, text in rules:
        if value >= thr:
            return text
    return default


def cagr(v0, v1, years):
    if v0 is None or v0 <= 0 or v1 <= 0 or years <= 0:
        return np.nan
    return ((v1 / v0) ** (1 / years) - 1) * 100


# ------------------------------------------------------------------ statistics
def decompose(series, period=12):
    """Classical additive decomposition (centred moving average), no external package."""
    s = pd.Series(series).astype(float)
    w = np.r_[0.5, np.ones(period - 1), 0.5] / period
    trend = pd.Series(np.convolve(s.to_numpy(), w, mode="same"), index=s.index)
    half = period // 2
    trend.iloc[:half] = np.nan
    trend.iloc[-half:] = np.nan
    detr = s - trend
    pos = np.arange(len(s)) % period
    seas_by_pos = detr.groupby(pos).mean()
    seas_by_pos = seas_by_pos - seas_by_pos.mean()
    seasonal = pd.Series(seas_by_pos.reindex(pos).to_numpy(), index=s.index)
    resid = s - trend - seasonal
    return pd.DataFrame({"observed": s, "trend": trend, "seasonal": seasonal, "resid": resid})


def strengths(dec):
    d = dec.dropna()
    fs = max(0.0, 1 - d["resid"].var() / (d["seasonal"] + d["resid"]).var())
    ft = max(0.0, 1 - d["resid"].var() / (d["trend"] + d["resid"]).var())
    return fs, ft


def gini(values):
    v = np.sort(np.asarray(values, dtype=float))
    v = v[~np.isnan(v)]
    if len(v) == 0 or v.sum() == 0:
        return np.nan
    k = np.arange(1, len(v) + 1)
    return float((2 * (k * v).sum() / (len(v) * v.sum())) - (len(v) + 1) / len(v))


# ------------------------------------------------------------------ map
def _rings(geometry):
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"][0]]
    if geometry["type"] == "MultiPolygon":
        return [poly[0] for poly in geometry["coordinates"]]
    return []


def draw_map(ax, geojson, values, cmap="YlGn", vmin=None, vmax=None, label_fmt="{:.0f}", labels=None,
             edge="white", title=None, cbar_label=None, fig=None):
    """Choropleth of the 13 regions. values: dict region_code -> number."""
    vals = [v for v in values.values() if v is not None and not np.isnan(v)]
    vmin = min(vals) if vmin is None else vmin
    vmax = max(vals) if vmax is None else vmax
    norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)
    cm = plt.get_cmap(cmap)
    xs, ys = [], []
    for f in geojson["features"]:
        code = f["properties"]["region_code"]
        v = values.get(code, np.nan)
        color = cm(norm(v)) if v is not None and not np.isnan(v) else "#DDDDDD"
        patches = []
        for ring in _rings(f["geometry"]):
            arr = np.asarray(ring)
            xs += list(arr[:, 0])
            ys += list(arr[:, 1])
            patches.append(MplPolygon(arr, closed=True))
        ax.add_collection(PatchCollection(patches, facecolor=color, edgecolor=edge, linewidth=0.8))
    ax.set_xlim(min(xs) - 0.3, max(xs) + 0.3)
    ax.set_ylim(min(ys) - 0.3, max(ys) + 0.3)
    ax.set_aspect(1 / np.cos(np.radians(46.5)))
    ax.axis("off")
    ax.grid(False)
    if labels:
        for code, (x, y, txt) in labels.items():
            ax.text(x, y, txt, ha="center", va="center", fontsize=7.5, color=INK)
    if title:
        ax.set_title(title, loc="left")
    if fig is not None:
        sm = mpl.cm.ScalarMappable(norm=norm, cmap=cm)
        cb = fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.04, pad=0.02, shrink=0.8)
        cb.outline.set_visible(False)
        if cbar_label:
            cb.set_label(cbar_label, fontsize=8)
    return norm, cm


# ------------------------------------------------------------------ cards (business question / observation / ...)
class Cards:
    """Keeps one card per figure: shown in the notebook and written in eda_report.md."""

    def __init__(self, folder):
        self.folder = folder
        self.items = []

    def save(self, fig, fid):
        path = self.folder / f"{fid}.png"
        fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
        return path

    def add(self, fid, section, title, question, observation, interpretation, value):
        item = dict(id=fid, section=section, title=title, question=question, observation=observation,
                    interpretation=interpretation, value=value, file=f"figures/{fid}.png")
        self.items.append(item)
        from IPython.display import Markdown, display
        display(Markdown(self.as_markdown(item, heading=3)))

    @staticmethod
    def as_markdown(it, heading=3, with_image=False):
        h = "#" * heading
        out = [f"{h} {it['id']} · {it['title']}", "",
               f"**Business question.** {it['question']}", "",
               f"**Observation.** {it['observation']}", "",
               f"**Interpretation.** {it['interpretation']}", "",
               f"**Storytelling value.** {it['value']}", ""]
        if with_image:
            out.insert(2, f"![{it['id']}]({it['file']})\n")
        return "\n".join(out)


# =====================================================================
# plotly charts for the Streamlit app (one consistent style, hover on every mark)
# =====================================================================
def _go():
    import plotly.graph_objects as go
    return go


def _base(fig, title=None, height=420, ytitle=None, xtitle=None, legend_bottom=True):
    fig.update_layout(
        template="plotly_white", height=height, title=dict(text=title, x=0, xanchor="left", font=dict(size=15)) if title else None,
        font=dict(family="Inter, Arial, sans-serif", size=12, color=INK), margin=dict(l=10, r=10, t=50 if title else 15, b=10),
        hoverlabel=dict(bgcolor="white", font_size=12), hovermode="x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.18, x=0) if legend_bottom else dict())
    if ytitle:
        fig.update_layout(yaxis_title_text=ytitle)
    if xtitle:
        fig.update_xaxes(title_text=xtitle)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor="#BBBBBB")
    return fig


def production_bars(nat, share_col="renewable_share_pct", sources=("hydro", "bioenergy", "wind", "solar"), title=None):
    """Stacked bars of the renewable production (TWh) + line of the renewable share (right axis).
    nat: DataFrame with columns year, <source>_gwh and the share column."""
    go = _go()
    fig = go.Figure()
    for s in sources:
        fig.add_bar(x=nat["year"], y=nat[cfg.GWH[s]] / 1000, name=cfg.LABEL[s], marker_color=cfg.COLOR[s],
                    hovertemplate="%{y:.1f} TWh<extra>" + cfg.LABEL[s] + "</extra>")
    fig.add_scatter(x=nat["year"], y=nat[share_col], name="Renewable share (right axis)", yaxis="y2", mode="lines+markers",
                    line=dict(color=INK, width=3), marker=dict(size=7), hovertemplate="%{y:.1f} %<extra>Renewable share</extra>")
    fig.update_layout(barmode="stack", yaxis2=dict(overlaying="y", side="right", title="Share of production (%)", showgrid=False,
                                                    range=[0, max(5, float(nat[share_col].max()) * 1.4)]))
    fig.update_xaxes(dtick=1)
    return _base(fig, title, ytitle="Renewable production (TWh per year)", xtitle="Year")


def line_chart(df, x, series, title=None, ytitle=None, xtitle=None, height=420, dash=None, fmt=".1f", unit=""):
    """series: dict label -> (column, color)."""
    go = _go()
    fig = go.Figure()
    for lab, (col, color) in series.items():
        fig.add_scatter(x=df[x], y=df[col], name=lab, mode="lines+markers", line=dict(color=color, width=2.6, dash=(dash or {}).get(lab)),
                        marker=dict(size=6), hovertemplate="%{y:" + fmt + "}" + unit + "<extra>" + lab + "</extra>")
    return _base(fig, title, height, ytitle, xtitle)


def change_bars(values, colors, title=None, xtitle=None, height=360, fmt="+.1f"):
    """Horizontal bars of a signed change per label (e.g. points of share by source)."""
    go = _go()
    s = values.sort_values()
    fig = go.Figure(go.Bar(x=s.values, y=s.index, orientation="h", marker_color=[colors[i] for i in s.index],
                           text=[format(v, fmt) for v in s.values], textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{x:" + fmt + "}<extra></extra>"))
    lo, hi = float(min(s.min(), 0)), float(max(s.max(), 0))
    pad = (hi - lo) * 0.22 or 1.0
    fig.update_layout(hovermode="closest", showlegend=False, xaxis=dict(range=[lo - (pad if lo < 0 else 0), hi + pad]))
    fig.add_vline(x=0, line_color="#777777", line_width=1)
    return _base(fig, title, height, xtitle=xtitle, legend_bottom=False)


def ranked_bars(df, label, value, group=None, title=None, xtitle=None, height=480, fmt=".1f", unit=""):
    """Horizontal bar ranking (best at the top), coloured by group (with / without nuclear)."""
    go = _go()
    d = df.sort_values(value)
    fig = go.Figure()
    groups = [None] if group is None else [False, True]
    for g in groups:
        sub = d if g is None else d[d[group] == g]
        fig.add_bar(x=sub[value], y=sub[label], orientation="h", name=GROUP_LABEL[g] if g is not None else value,
                    marker_color=GROUP_COLOR[g] if g is not None else "#0072B2", text=[format(v, fmt) + unit for v in sub[value]],
                    textposition="outside", cliponaxis=False, hovertemplate="%{y}: %{x:" + fmt + "}" + unit + "<extra></extra>")
    lo, hi = float(min(d[value].min(), 0)), float(max(d[value].max(), 0))
    pad = (hi - lo) * 0.16 or 1.0
    fig.update_layout(barmode="relative", hovermode="closest", yaxis=dict(categoryorder="array", categoryarray=list(d[label])),
                      xaxis=dict(range=[lo - (pad if lo < 0 else 0), hi + pad]))
    fig.add_vline(x=0, line_color="#777777", line_width=1)
    return _base(fig, title, height, xtitle=xtitle, legend_bottom=group is not None)


def _bounds(geojson):
    xs, ys = [], []

    def walk(c):
        if c and isinstance(c[0], (int, float)):
            xs.append(c[0]); ys.append(c[1])
        else:
            for x in c:
                walk(x)
    for f in geojson["features"]:
        walk(f["geometry"]["coordinates"])
    return min(xs), max(xs), min(ys), max(ys)


def map_chart(geojson, df, value, title=None, colorbar_title=None, scale="YlGn", zmid=None, height=520, fmt=".1f", extra=None):
    """Choropleth of the regions drawn with MapLibre on a blank background (no tile server, no external file needed).
    df: region_code, region, value, [extra columns for the hover]."""
    go = _go()
    hover = "<b>%{customdata[0]}</b><br>" + (colorbar_title or value) + ": %{z:" + fmt + "}"
    cd = [df["region"]]
    if extra:
        for i, (lab, col, f) in enumerate(extra, start=1):
            hover += f"<br>{lab}: %{{customdata[{i}]:{f}}}"
            cd.append(df[col])
    x0, x1, y0, y1 = _bounds(geojson)
    lat = (y0 + y1) / 2
    zoom = float(np.log2(0.86 * height * 360 * np.cos(np.radians(lat)) / (256 * (y1 - y0))))
    fig = go.Figure(go.Choroplethmap(
        geojson=geojson, locations=df["region_code"], featureidkey="properties.region_code", z=df[value],
        colorscale=scale, zmid=zmid, marker_opacity=0.92, marker_line_color="white", marker_line_width=0.9,
        colorbar=dict(title=dict(text=colorbar_title or value, side="right"), thickness=14, len=0.8),
        customdata=np.stack(cd, axis=-1), hovertemplate=hover + "<extra></extra>"))
    fig.update_layout(map=dict(style="white-bg", center=dict(lat=lat, lon=(x0 + x1) / 2), zoom=zoom), hovermode="closest")
    return _base(fig, title, height, legend_bottom=False)


def quadrant_chart(reg, x, y, size, title=None, xtitle=None, ytitle=None, height=520, xline=None, yline=None):
    """Level (x) versus progress (y); bubble = production; colour = with / without nuclear."""
    go = _go()
    fig = go.Figure()
    smax = float(reg[size].max())
    for g in (False, True):
        sub = reg[reg["has_nuclear"] == g]
        fig.add_scatter(x=sub[x], y=sub[y], mode="markers+text", text=sub["region_short"], textposition="top center", name=GROUP_LABEL[g],
                        marker=dict(size=12 + 38 * sub[size] / smax, color=GROUP_COLOR[g], opacity=0.85, line=dict(color="white", width=1)),
                        customdata=np.stack([sub["region"], sub[size] / 1000], axis=-1),
                        hovertemplate="<b>%{customdata[0]}</b><br>level: %{x:.1f} %<br>progress: %{y:+.1f} pts<br>production: %{customdata[1]:.1f} TWh<extra></extra>")
    if xline is not None:
        fig.add_vline(x=xline, line_dash="dash", line_color="#888888")
    if yline is not None:
        fig.add_hline(y=yline, line_dash="dash", line_color="#888888")
    for txt, ax_, ay_, xa, ya in [("Leaders", 0.99, 0.99, "right", "top"), ("Catching up", 0.01, 0.99, "left", "top"),
                                  ("Resting on its level", 0.99, 0.01, "right", "bottom"), ("Lagging", 0.01, 0.01, "left", "bottom")]:
        fig.add_annotation(text=f"<b>{txt}</b>", xref="paper", yref="paper", x=ax_, y=ay_, showarrow=False, xanchor=xa, yanchor=ya,
                           font=dict(color=MUTED, size=13))
    fig.update_layout(hovermode="closest")
    return _base(fig, title, height, ytitle, xtitle)


def heatmap(pivot, title=None, colorbar_title="%", scale="YlGn", height=460, fmt=".0f", zmid=None):
    go = _go()
    fig = go.Figure(go.Heatmap(z=pivot.values, x=[str(c) for c in pivot.columns], y=list(pivot.index), colorscale=scale, zmid=zmid,
                               colorbar=dict(title=colorbar_title, thickness=14), text=np.vectorize(lambda v: format(v, fmt))(pivot.values),
                               texttemplate="%{text}", textfont=dict(size=10), hovertemplate="%{y}, %{x}: %{z:" + fmt + "}<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(hovermode="closest")
    return _base(fig, title, height, legend_bottom=False)


def dumbbell(reg, label, start, end, group="has_nuclear", title=None, xtitle=None, height=480):
    """Value at the start and at the end of the period for every region."""
    go = _go()
    d = reg.sort_values(end)
    fig = go.Figure()
    for _, r in d.iterrows():
        fig.add_scatter(x=[r[start], r[end]], y=[r[label]] * 2, mode="lines", line=dict(color="#C9C9C9", width=3), showlegend=False, hoverinfo="skip")
    fig.add_scatter(x=d[start], y=d[label], mode="markers", name="Start year", marker=dict(size=10, color="white", line=dict(color="#555555", width=2)),
                    hovertemplate="%{y}: %{x:.1f} % (start)<extra></extra>")
    fig.add_scatter(x=d[end], y=d[label], mode="markers", name="End year", marker=dict(size=13, color=[GROUP_COLOR[v] for v in d[group]]),
                    hovertemplate="%{y}: %{x:.1f} % (end)<extra></extra>")
    fig.update_layout(hovermode="closest", yaxis=dict(categoryorder="array", categoryarray=list(d[label])))
    return _base(fig, title, height, xtitle=xtitle)


def seasonal_chart(month_df, share_col="renewable_share_pct", sources=("hydro", "bioenergy", "wind", "solar"), title=None):
    """Average monthly renewable production by source (TWh) + renewable share (right axis). month_df: month, <source>_gwh, share."""
    go = _go()
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig = go.Figure()
    for s in sources:
        fig.add_bar(x=month_df["month"].map(lambda m: months[int(m) - 1]), y=month_df[cfg.GWH[s]] / 1000, name=cfg.LABEL[s], marker_color=cfg.COLOR[s],
                    hovertemplate="%{y:.2f} TWh<extra>" + cfg.LABEL[s] + "</extra>")
    fig.add_scatter(x=month_df["month"].map(lambda m: months[int(m) - 1]), y=month_df[share_col], name="Renewable share (right axis)", yaxis="y2",
                    mode="lines+markers", line=dict(color=INK, width=3), hovertemplate="%{y:.1f} %<extra>Renewable share</extra>")
    fig.update_layout(barmode="stack", yaxis2=dict(overlaying="y", side="right", title="Share (%)", showgrid=False,
                                                    range=[0, max(5, float(month_df[share_col].max()) * 1.5)]))
    return _base(fig, title, ytitle="Average production (TWh per month)", xtitle="Calendar month")


def profile_chart(prof, title=None):
    """Seasonal profile of each source = monthly mean / yearly mean (1 = average month)."""
    go = _go()
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig = go.Figure()
    for s in prof.columns:
        fig.add_scatter(x=months, y=prof[s], name=cfg.LABEL[s], mode="lines+markers", line=dict(color=cfg.COLOR[s], width=3),
                        hovertemplate="%{y:.2f} x average month<extra>" + cfg.LABEL[s] + "</extra>")
    fig.add_hline(y=1, line_dash="dot", line_color="#888888")
    return _base(fig, title, ytitle="Production relative to the average month (1 = average)", xtitle="Calendar month")


def decomposition_chart(dec, title=None, unit="TWh"):
    from plotly.subplots import make_subplots
    go = _go()
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06, subplot_titles=("Observed", "Trend (12-month centred average)", "Seasonal component"))
    for i, (col, color) in enumerate([("observed", "#0072B2"), ("trend", "#D55E00"), ("seasonal", "#009E73")], start=1):
        fig.add_scatter(x=dec.index, y=dec[col], mode="lines", line=dict(color=color, width=2.2), showlegend=False,
                        hovertemplate="%{y:.2f} " + unit + "<extra>" + col + "</extra>", row=i, col=1)
    fig.update_yaxes(title_text=unit)
    return _base(fig, title, height=560, legend_bottom=False)


def scenario_chart(years, hist, proj, title=None):
    """Historical (solid) and scenario (dashed) renewable share."""
    go = _go()
    fig = go.Figure()
    fig.add_scatter(x=years["hist"], y=hist, name="Observed", mode="lines+markers", line=dict(color="#0072B2", width=3), hovertemplate="%{y:.1f} %<extra>Observed</extra>")
    fig.add_scatter(x=years["proj"], y=proj, name="Scenario (assumptions set with the sliders above)", mode="lines+markers",
                    line=dict(color="#D55E00", width=3, dash="dash"), hovertemplate="%{y:.1f} %<extra>Scenario</extra>")
    fig.update_xaxes(dtick=1)
    return _base(fig, title, ytitle="Renewable share of national production (%)", xtitle="Year")


def mix_area(df, title=None, height=380):
    """100 % stacked area of the source shares over the years (one region)."""
    go = _go()
    fig = go.Figure()
    for s in ["nuclear", "thermal", "hydro", "bioenergy", "wind", "solar"]:
        fig.add_scatter(x=df["year"], y=df[f"{s}_share_pct"], name=cfg.LABEL[s], mode="lines", stackgroup="one", line=dict(width=0.5, color="white"),
                        fillcolor=cfg.COLOR[s], hovertemplate="%{y:.1f} %<extra>" + cfg.LABEL[s] + "</extra>")
    fig.update_yaxes(range=[0, 100])
    fig.update_xaxes(dtick=1)
    return _base(fig, title, height, ytitle="Share of regional production (%)", xtitle="Year")
