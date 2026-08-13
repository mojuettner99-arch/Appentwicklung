# LoopLab – PID-Regler Simulator (Streamlit)

Diese Fassung erfüllt die technischen Vorgaben des LF-10.2-Projekts: Python,
interaktive Parameter, CSV-Import, numerische Berechnung, dynamische Diagramme,
Kennwerte, Datentabelle, Ergebnis-Download und Fehlerbehandlung.

## Lokal starten

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Tests ausführen

```bash
pytest -q
```

## CSV-Format

Pflichtspalten sind `time` und `setpoint`; `disturbance` ist optional. Alternativ
werden die deutschen Namen `zeit`, `sollwert` und `stoerung` akzeptiert. Die Zeit
muss bei 0 beginnen, streng aufsteigen und darf höchstens 120 Sekunden umfassen.

## Hugging Face Spaces

Beim Erstellen des Space das SDK **Docker** wählen und den Inhalt dieses Ordners
hochladen. Der Container startet Streamlit auf Port 7860.
