from streamlit.testing.v1 import AppTest


def test_streamlit_app_loads_and_reacts_to_pid_slider():
    app = AppTest.from_file("streamlit_app.py", default_timeout=30).run()
    assert not app.exception
    assert app.title[0].value == "LoopLab – PID-Regler Simulator"
    assert len(app.slider) == 8
    assert len(app.metric) == 5

    original_iae = app.metric[4].value
    app.slider[0].set_value(6.0).run()

    assert not app.exception
    assert app.metric[4].value != original_iae
