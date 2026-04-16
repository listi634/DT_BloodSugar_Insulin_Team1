# Projekt-Spezifikation: Blutzucker-Insulin Digital Twin

## 1. Projektübersicht
Das Ziel des Projekts ist die Entwicklung eines **Digitalen Zwilling (DT)** zur Modellierung und Simulation des Glukose-Insulin-Systems des menschlichen Körpers. Der Fokus liegt auf der Auswirkung von Mahlzeiten auf die Blutplasma-Werte und der Integration von Continuous Glucose Monitoring (CGM) sowie Insulinpumpen.

## 2. Systemgrundlagen & Begriffe
* **CGM-Patch:** Misst Glukosewerte im Gewebe (Interstitium). Daraus wird der Blutzucker- und Insulinspiegel abgeschätzt.
* **Glukose (G):** Einheit in $mmol/L$.
    * Basalwert ($G_b$): $\approx 5$.
    * Typischer Bereich: $4$ bis $10$.
* **Insulin (I):** Einheit in $\mu U/mL$ (bzw. $U/L$).
    * Basalwert ($I_b$): $\approx 10$.
    * Gefastet: $5$ bis $15$.
    * Nach Mahlzeit: $40$ bis $60$.

## 3. Modellierung (Grey-Box Modell)
Es soll ein dynamisches **Low-Order Grey-Box Modell** mittels Differentialgleichungen (ODEs) erstellt werden.

### Ein- und Ausgänge
* **System-Inputs:** Glukose-Äquivalent einer Mahlzeit (Essen).
* **System-Outputs:** Messung der Gewebeglukose (Interstitium via CGM).

### Dynamik & Erwartetes Verhalten
1.  **Kopplung:** Glukoseanstieg bewirkt Insulinanstieg; hohes Insulin senkt den Glukosespiegel.
2.  **Zeitverlauf nach Mahlzeit:**
    * Anstieg von $G$ nach 5–10 Min.
    * Maximum von $G$ nach 30–60 Min.
    * Insulin reagiert verzögert.
3.  **Stabilisierung:** Ohne weiteren Input Rückkehr zu Basalwerten ($G_b, I_b$) innerhalb von 2–3 Stunden.
4.  **Stabilität:** Das System muss stabil sein und darf keine Schwingungen aufweisen.

## 4. Technische Implementierung
Die Umsetzung erfolgt wahlweise in:
* **MATLAB / Simulink (Version 2025b):** Nutzung der Campus-Lizenz.
* **Python:** Nutzung von Bibliotheken zur Simulation von Differentialgleichungen und Graphen für Zeitreihen (z. B. PyCharm oder Jupyter Notebooks).

## 5. Projektaufgaben (Meilensteine)
1.  **Konzept & Brainstorming:** Reflexion über Nutzen und Motivation für Anwender (Diabetiker, Sportler).
2.  **Modell-Spezifikation:** Erstellung eines Textes und eines Blockdiagramms des Glukose-Insulin-Systems (basierend auf dem Referenzmodell: Gastrointestinaltrakt, Leber, Muskel-/Fettgewebe).
3.  **Mathematisches Modell:** Aufbau der ODEs zur Beschreibung der Dynamik.
4.  **Simulation & Validierung:** Bestätigung des Verhaltens durch Simulation der Zeitverläufe.
5.  **Use-Case Insulinpumpe:** Analyse des Mehrwerts des Digitalen Zwillings für die Entwicklung oder den Betrieb einer Insulinpumpe (Sicherheit, Kosten, Qualität).

## 6. Business & Value Perspective
* **User-Sicht:** Besseres Verständnis der eigenen Werte zur Steigerung der Leistungsfähigkeit und Gesundheit.
* **Unternehmens-Sicht:** Identifikation zusätzlicher Services durch den DT und Ableitung von Anforderungen (5D Digital Twin Framework).