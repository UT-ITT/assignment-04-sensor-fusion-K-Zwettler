[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/AktWbCri)

# assignment-04-CV-Sensor-Fusion

# 1

Das Programm muss mit folgenden Argumenten in der Kommandozeile ausgeführt werden:

1. Input image (Name der file des Bildes, das man transformen möchte)
2. Output destination (Name der file, in die das transformierte Bild gespeichert werden soll)
3. Resolution (dabei sind width und height als verschiedene Argumente zu geben)

Beispiel Eingabe: python3 image_extractor.py sample_image.jpg result.jpg 1000 600

Das Programm wird dann gestartet und man kann Punkte einzeichnen und diese durch das Drücken von 'esc' wieder löschen. Sobald 4 Punkte eingezeichnet wurden, wird das transformierte Bild in einem neuen Fenster gezeigt und durch Drücken von 's' kann man dieses speichern. Indem man 'q' drückt, kann man alle Fenster schließen.

# 2

In meinem AR game werden, sobald die vier Aruco Marker erkannt werden, blaue und ein rote Bälle von unten nach oben geschossen, bevor sie dann wieder nach unten fallen und verschwinden. Ziel ist es, mit dem Finger die blauen Bälle zu zerstören, indem man sie berührt. Das erhöht den score. Berührt man allerdings die roten Bälle, so geht der score wieder runter.
Das Spiel kann durch das Drücken von 'q' wieder geschlossen werden.
