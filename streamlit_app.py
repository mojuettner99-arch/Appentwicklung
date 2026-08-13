"""Streamlit-Oberfläche für das LF-10.2-Projekt PID-Regler-Simulator."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from pid_core import (
    SimulationConfig,
    analyze_linear_model,
    calculate_metrics,
    parse_profile,
    simulate,
)


st.set_page_config(
    page_title="LoopLab – PID-Regler Simulator",
    page_icon="↻",
    layout="wide",
)

st.markdown(
    """
    <style>
      .stApp { background: #f2f0e9; color: #142e2d; }
      [data-testid="stSidebar"] { background: #142e2d; }
      [data-testid="stSidebar"] * { color: #ffffff; }
      [data-testid="stMetric"] {
        background: #fffefa; border: 1px solid rgba(20,46,45,.15);
        border-radius: 12px; padding: 14px;
      }
      h1 { letter-spacing: -0.045em; }
      .subtitle { color: #667876; max-width: 820px; line-height: 1.7; }
      .formula {
        background: #fffefa; border: 1px solid rgba(20,46,45,.15);
        border-radius: 12px; padding: 14px 18px; margin-top: 18px;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("LoopLab – PID-Regler Simulator")
st.markdown(
    '<p class="subtitle">Verändere Regler und PT1-Strecke. Die Sprungantwort, '
    "Stellgröße und technischen Kennwerte werden bei jeder Eingabe automatisch "
    "neu berechnet.</p>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("01 · Regler einstellen")
    preset = st.selectbox("Voreinstellung", ["Ausgewogen", "Sanft", "Dynamisch"])
    presets = {
        "Ausgewogen": (2.2, 0.85, 0.35),
        "Sanft": (1.1, 0.35, 0.08),
        "Dynamisch": (3.8, 1.45, 0.65),
    }
    default_kp, default_ki, default_kd = presets[preset]
    kp = st.slider("Kp · Proportionalanteil", 0.0, 8.0, default_kp, 0.1)
    ki = st.slider("Ki · Integralanteil [1/s]", 0.0, 3.0, default_ki, 0.05)
    kd = st.slider("Kd · Differentialanteil [s]", 0.0, 2.0, default_kd, 0.05)

    with st.expander("Strecke & Versuch", expanded=False):
        plant_gain = st.slider("Ks · Streckenverstärkung", 0.2, 3.0, 1.0, 0.1)
        time_constant = st.slider("T · Zeitkonstante [s]", 0.3, 10.0, 2.5, 0.1)
        dead_time = st.slider("L · Totzeit [s]", 0.0, 3.0, 0.25, 0.05)
        setpoint = st.slider("w · Sollwert", 0.2, 2.0, 1.0, 0.1)
        disturbance = st.slider("z · Störsprung", -1.0, 1.0, -0.2, 0.1)

    st.divider()
    st.subheader("Eigenes Testprofil")
    uploaded_file = st.file_uploader(
        "CSV mit time, setpoint und optional disturbance",
        type=["csv"],
        help="Die Zeitachse muss bei 0 beginnen und streng aufsteigend sein.",
    )

profile = None
if uploaded_file is not None:
    try:
        profile = parse_profile(uploaded_file)
        st.success(f"CSV-Profil mit {len(profile)} Stützstellen geladen.")
        with st.expander("Importierte Daten anzeigen"):
            st.dataframe(profile, width="stretch")
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

config = SimulationConfig(
    kp=kp,
    ki=ki,
    kd=kd,
    plant_gain=plant_gain,
    time_constant=time_constant,
    dead_time=dead_time,
    setpoint=setpoint,
    disturbance=disturbance,
)

try:
    result = simulate(config, profile)
    metrics = calculate_metrics(result)
    linear_analysis = analyze_linear_model(config)
except ValueError as exc:
    st.error(str(exc))
    st.stop()
except Exception as exc:
    st.error(f"Die Simulation konnte nicht berechnet werden: {exc}")
    st.stop()

st.subheader("02 · Systemantwort")
if linear_analysis["stable"]:
    st.success("Die linearisierte Polanalyse bewertet diese Einstellung als stabil.")
else:
    st.warning(
        "Die linearisierte Polanalyse erkennt eine instabile Einstellung. "
        "Begrenzung und Anti-Windup halten die numerische Simulation dennoch endlich."
    )
figure = go.Figure()
figure.add_trace(
    go.Scatter(
        x=result["time"], y=result["setpoint"], name="Sollwert w(t)",
        line=dict(color="#ed9c3d", width=2, dash="dash"),
    )
)
figure.add_trace(
    go.Scatter(
        x=result["time"], y=result["output"], name="Regelgröße y(t)",
        line=dict(color="#0d716b", width=3), fill="tozeroy",
        fillcolor="rgba(13,113,107,.10)",
    )
)
figure.add_trace(
    go.Scatter(
        x=result["time"], y=result["control"], name="Stellgröße u(t)",
        line=dict(color="#7e8a88", width=1), yaxis="y2", opacity=0.72,
    )
)
figure.update_layout(
    height=500,
    paper_bgcolor="#fffefa",
    plot_bgcolor="#fffefa",
    margin=dict(l=45, r=45, t=35, b=45),
    legend=dict(orientation="h", y=1.12, x=0),
    hovermode="x unified",
    xaxis=dict(title="Zeit [s]", gridcolor="rgba(20,46,45,.10)"),
    yaxis=dict(title="Soll- / Regelgröße", gridcolor="rgba(20,46,45,.10)"),
    yaxis2=dict(title="Stellgröße", overlaying="y", side="right", range=[-5.5, 5.5]),
)
st.plotly_chart(figure, width="stretch", config={"displaylogo": False})

columns = st.columns(5)
metric_values = [
    ("Anstiegszeit tr", metrics["rise_time"], "s"),
    ("Ausregelzeit ts", metrics["settling_time"], "s"),
    ("Überschwingen Mp", metrics["overshoot_percent"], "%"),
    ("Regelabweichung", metrics["steady_state_error"], ""),
    ("Fehlerfläche IAE", metrics["iae"], ""),
]
for column, (label, value, unit) in zip(columns, metric_values):
    display = "nicht erreicht" if not np.isfinite(value) else f"{value:.2f} {unit}".strip()
    column.metric(label, display)

st.markdown(
    '<div class="formula"><b>Regler:</b> GR(s) = Kp + Ki/s + Kd·s &nbsp;&nbsp; '
    '<b>Strecke:</b> GS(s) = Ks·e<sup>−Ls</sup> / (T·s + 1)</div>',
    unsafe_allow_html=True,
)

with st.expander("Lineare Pole anzeigen"):
    pole_rows = [
        {"Realteil": pole.real, "Imaginärteil": pole.imag}
        for pole in linear_analysis["poles"]
    ]
    st.dataframe(pole_rows, width="stretch")
    st.caption(
        "Die Totzeit wird für diese ergänzende Analyse durch eine Padé-Näherung "
        "erster Ordnung abgebildet."
    )

with st.expander("Numerische Ergebnisse anzeigen / herunterladen"):
    st.dataframe(result, width="stretch", height=320)
    st.download_button(
        "Simulation als CSV herunterladen",
        data=result.to_csv(index=False).encode("utf-8"),
        file_name="pid_simulation.csv",
        mime="text/csv",
    )
