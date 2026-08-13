from io import StringIO

import numpy as np
import pytest

from pid_core import (
    SimulationConfig,
    analyze_linear_model,
    calculate_metrics,
    parse_profile,
    simulate,
)


def test_default_simulation_reaches_setpoint():
    result = simulate(SimulationConfig(disturbance=0.0))
    metrics = calculate_metrics(result)
    assert len(result) > 1000
    assert np.isfinite(result.to_numpy()).all()
    assert abs(result.iloc[-1]["output"] - 1.0) < 0.02
    assert metrics["rise_time"] > 0
    assert metrics["iae"] > 0


def test_actuator_saturation_is_respected_for_extreme_tuning():
    result = simulate(SimulationConfig(kp=8.0, ki=3.0, kd=2.0, dead_time=3.0))
    assert result["control"].between(-5.0, 5.0).all()
    assert np.isfinite(result.to_numpy()).all()


def test_csv_profile_accepts_german_headers():
    profile = parse_profile(StringIO("zeit;sollwert;stoerung\n0;0;0\n5;1;-0.2\n10;0.5;0\n"))
    result = simulate(SimulationConfig(), profile)
    assert list(profile.columns) == ["time", "setpoint", "disturbance"]
    assert result.iloc[-1]["setpoint"] == pytest.approx(0.5)


@pytest.mark.parametrize(
    "csv_text, message",
    [
        ("foo,bar\n0,1\n1,2\n", "Spalten time und setpoint"),
        ("time,setpoint\n1,0\n2,1\n", "bei 0 beginnen"),
        ("time,setpoint\n0,0\n0,1\n", "streng aufsteigend"),
        ("time,setpoint\n0,0\n1,nicht-zahl\n", "ungültige Zahlenwerte"),
    ],
)
def test_invalid_csv_is_rejected(csv_text, message):
    with pytest.raises(ValueError, match=message):
        parse_profile(StringIO(csv_text))


def test_invalid_time_constant_is_rejected():
    with pytest.raises(ValueError, match="Zeitkonstante"):
        simulate(SimulationConfig(time_constant=0.0))


def test_default_linear_model_is_stable_and_has_finite_poles():
    analysis = analyze_linear_model(SimulationConfig())
    assert analysis["stable"] is True
    assert len(analysis["poles"]) >= 2
    assert np.isfinite(analysis["poles"]).all()
