"""Numerischer Kern des PID-Regler-Simulators.

Das Modell verwendet eine PT1-Strecke mit optionaler Totzeit:

    Gs(s) = Ks * exp(-L*s) / (T*s + 1)

Der PID-Regler wird zeitdiskret mit Stellgrößenbegrenzung, Anti-Windup und
gefiltertem D-Anteil berechnet. Die Funktionen sind bewusst unabhängig von
Streamlit gehalten, damit sie mit pytest oder in Google Colab getestet werden
können.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import control as ct


@dataclass(frozen=True)
class SimulationConfig:
    kp: float = 2.2
    ki: float = 0.85
    kd: float = 0.35
    plant_gain: float = 1.0
    time_constant: float = 2.5
    dead_time: float = 0.25
    setpoint: float = 1.0
    disturbance: float = -0.2
    duration: float = 30.0
    dt: float = 0.02
    actuator_min: float = -5.0
    actuator_max: float = 5.0


def validate_config(config: SimulationConfig) -> None:
    """Prüft alle numerischen Eingaben und liefert verständliche Fehler."""
    values = np.asarray(list(config.__dict__.values()), dtype=float)
    if not np.all(np.isfinite(values)):
        raise ValueError("Alle Parameter müssen endliche Zahlen sein.")
    if config.time_constant <= 0:
        raise ValueError("Die Zeitkonstante T muss größer als 0 sein.")
    if config.dead_time < 0:
        raise ValueError("Die Totzeit L darf nicht negativ sein.")
    if config.duration <= 0 or config.duration > 120:
        raise ValueError("Die Simulationsdauer muss zwischen 0 und 120 s liegen.")
    if config.dt <= 0 or config.dt > config.duration:
        raise ValueError("Die Schrittweite dt muss positiv und kleiner als die Dauer sein.")
    if config.actuator_min >= config.actuator_max:
        raise ValueError("Die untere Stellgrenze muss kleiner als die obere sein.")


def parse_profile(uploaded_file) -> pd.DataFrame:
    """Liest ein Sollwertprofil aus CSV und vereinheitlicht die Spaltennamen.

    Pflichtspalten: ``time`` und ``setpoint``. Deutsche Alternativen
    ``zeit``/``sollwert`` werden akzeptiert. ``disturbance`` ist optional.
    """
    try:
        frame = pd.read_csv(uploaded_file, sep=None, engine="python")
    except Exception as exc:  # pandas liefert je nach Fehler verschiedene Typen
        raise ValueError("Die CSV-Datei konnte nicht gelesen werden.") from exc

    aliases = {
        "t": "time",
        "zeit": "time",
        "w": "setpoint",
        "sollwert": "setpoint",
        "z": "disturbance",
        "stoerung": "disturbance",
        "störung": "disturbance",
    }
    frame.columns = [aliases.get(str(column).strip().lower(), str(column).strip().lower()) for column in frame.columns]
    missing = {"time", "setpoint"} - set(frame.columns)
    if missing:
        raise ValueError("Die CSV-Datei benötigt die Spalten time und setpoint.")
    if "disturbance" not in frame.columns:
        frame["disturbance"] = 0.0
    frame = frame[["time", "setpoint", "disturbance"]].copy()
    for column in frame.columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame.isna().any().any() or not np.isfinite(frame.to_numpy()).all():
        raise ValueError("Die CSV-Datei enthält fehlende oder ungültige Zahlenwerte.")
    if len(frame) < 2:
        raise ValueError("Das CSV-Profil benötigt mindestens zwei Datenzeilen.")
    if not np.isclose(frame.iloc[0]["time"], 0.0):
        raise ValueError("Die Zeitachse des CSV-Profils muss bei 0 beginnen.")
    if not np.all(np.diff(frame["time"].to_numpy()) > 0):
        raise ValueError("Die Zeitwerte müssen streng aufsteigend sein.")
    if frame.iloc[-1]["time"] > 120:
        raise ValueError("Das CSV-Profil darf höchstens 120 Sekunden lang sein.")
    return frame


def simulate(config: SimulationConfig, profile: pd.DataFrame | None = None) -> pd.DataFrame:
    """Simuliert den geschlossenen Regelkreis im Zeitbereich."""
    validate_config(config)
    duration = float(profile.iloc[-1]["time"]) if profile is not None else config.duration
    duration = max(5.0, duration)
    time = np.arange(0.0, duration + config.dt / 2, config.dt)

    if profile is None:
        setpoint = np.where(time >= 1.0, config.setpoint, 0.0)
        disturbance = np.where(time >= duration * 0.55, config.disturbance, 0.0)
    else:
        profile_time = profile["time"].to_numpy()
        setpoint = np.interp(time, profile_time, profile["setpoint"].to_numpy())
        disturbance = np.interp(time, profile_time, profile["disturbance"].to_numpy())

    output = np.zeros_like(time)
    control = np.zeros_like(time)
    error = np.zeros_like(time)
    p_part = np.zeros_like(time)
    i_part = np.zeros_like(time)
    d_part = np.zeros_like(time)
    integral = 0.0
    filtered_derivative = 0.0
    filter_time = max(0.03, 4.0 * config.dt)
    delay_steps = max(0, round(config.dead_time / config.dt))
    delayed_control = np.zeros(len(time) + delay_steps + 1)

    for index in range(1, len(time)):
        error[index] = setpoint[index] - output[index - 1]
        derivative = (error[index] - error[index - 1]) / config.dt
        filtered_derivative += (config.dt / (filter_time + config.dt)) * (
            derivative - filtered_derivative
        )
        candidate_integral = integral + error[index] * config.dt
        p_part[index] = config.kp * error[index]
        i_candidate = config.ki * candidate_integral
        d_part[index] = config.kd * filtered_derivative
        raw_control = p_part[index] + i_candidate + d_part[index]
        control[index] = np.clip(raw_control, config.actuator_min, config.actuator_max)

        pushes_further_into_limit = (
            raw_control > config.actuator_max and error[index] > 0
        ) or (raw_control < config.actuator_min and error[index] < 0)
        if not pushes_further_into_limit:
            integral = candidate_integral
        i_part[index] = config.ki * integral

        delayed_control[index + delay_steps] = control[index]
        plant_input = delayed_control[index] + disturbance[index]
        output[index] = output[index - 1] + config.dt / config.time_constant * (
            config.plant_gain * plant_input - output[index - 1]
        )

    return pd.DataFrame(
        {
            "time": time,
            "setpoint": setpoint,
            "output": output,
            "control": control,
            "disturbance": disturbance,
            "error": error,
            "p_part": p_part,
            "i_part": i_part,
            "d_part": d_part,
        }
    )


def calculate_metrics(result: pd.DataFrame) -> dict[str, float]:
    """Berechnet typische Kennwerte der Sprungantwort."""
    setpoint = result["setpoint"].to_numpy()
    output = result["output"].to_numpy()
    time = result["time"].to_numpy()
    error = setpoint - output
    active_indices = np.flatnonzero(np.abs(setpoint) > 1e-6)
    start_index = int(active_indices[0]) if active_indices.size else 0
    target = float(setpoint[start_index]) if active_indices.size else float(setpoint[-1])
    direction = 1.0 if target >= 0 else -1.0

    def first_crossing(fraction: float) -> float:
        candidates = np.flatnonzero(
            direction * output[start_index:] >= direction * target * fraction
        )
        return float(time[start_index + candidates[0]]) if candidates.size else np.nan

    t10 = first_crossing(0.1)
    t90 = first_crossing(0.9)
    rise_time = t90 - t10 if np.isfinite(t10) and np.isfinite(t90) else np.nan
    tolerance = max(abs(float(setpoint[-1])) * 0.02, 0.01)
    outside = np.flatnonzero(np.abs(error) > tolerance)
    settling_time = (
        float(time[outside[-1] + 1]) if outside.size and outside[-1] + 1 < len(time) else np.nan
    )
    peak = float(np.max(direction * output))
    overshoot = max(0.0, (peak - abs(target)) / abs(target) * 100) if abs(target) > 1e-6 else 0.0
    tail_count = max(10, len(result) // 20)
    steady_error = float(np.mean(np.abs(error[-tail_count:])))
    iae = float(np.trapezoid(np.abs(error), time))
    return {
        "rise_time": rise_time,
        "settling_time": settling_time,
        "overshoot_percent": overshoot,
        "steady_state_error": steady_error,
        "iae": iae,
    }


def analyze_linear_model(config: SimulationConfig) -> dict[str, object]:
    """Analysiert die Pole des idealisierten linearen geschlossenen Kreises.

    Die Totzeit wird mit einer Padé-Näherung erster Ordnung angenähert und der
    D-Anteil mit demselben kleinen Tiefpass wie in der Simulation realisierbar
    gemacht. Stellgrößenbegrenzung und Anti-Windup sind nichtlinear und daher in
    dieser ergänzenden Polanalyse nicht enthalten.
    """
    validate_config(config)
    s = ct.TransferFunction.s
    derivative_filter = max(0.03, 4.0 * config.dt)
    controller = (
        config.kp
        + config.ki / s
        + config.kd * s / (derivative_filter * s + 1)
    )
    plant = config.plant_gain / (config.time_constant * s + 1)
    if config.dead_time > 0:
        delay_num, delay_den = ct.pade(config.dead_time, 1)
        plant *= ct.tf(delay_num, delay_den)
    closed_loop = ct.feedback(controller * plant, 1)
    poles = np.asarray(ct.poles(closed_loop), dtype=complex)
    stable = bool(np.all(np.real(poles) < -1e-8)) if poles.size else True
    return {"poles": poles, "stable": stable, "system": closed_loop}
