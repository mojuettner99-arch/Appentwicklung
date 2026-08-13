# Themenvorschlag für LF 10.2

## Titel / Thema

**Interaktiver PID-Regler-Simulator für das dynamische Verhalten eines
geschlossenen Regelkreises (LF 8)**

## Geplanter Umfang

- Eingabe der PID-Parameter `Kp`, `Ki` und `Kd` über Schieberegler
- Eingabe der Parameter einer PT1-Strecke: Verstärkung `Ks`, Zeitkonstante `T`
  und Totzeit `L`
- Vorgabe von Sollwert und Störsprung sowie Auswahl vorbereiteter Regler-Sätze
- CSV-Upload eines eigenen Sollwert- und Störprofils mit den Spalten `time`,
  `setpoint` und optional `disturbance`
- Zeitdiskrete Simulation mit Stellgrößenbegrenzung, Anti-Windup und gefiltertem
  D-Anteil
- Ergänzende Stabilitätsbewertung des linearisierten Regelkreises über dessen
  Pole mit der Python Control Systems Library
- Interaktives Diagramm für Sollwert, Regelgröße und Stellgröße
- Automatische Bestimmung von Anstiegszeit, Ausregelzeit, Überschwingweite,
  bleibender Regelabweichung und Fehlerfläche IAE
- Tabellenansicht und CSV-Download der berechneten Simulationswerte
- Verständliche Fehlermeldungen bei fehlerhaften Parametern oder CSV-Dateien
