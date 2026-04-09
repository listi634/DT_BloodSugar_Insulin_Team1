import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button

# --- Parameter des Modells ---
G_BASAL = 5.0    # Basalwert Blutzucker (mmol/l)
I_BASAL = 10.0     # Basalwert Insulin (mU/L)
DT = 1            # Zeitschritt in Minuten
MINUTES = 1440    # 24 Stunden

# Dynamik-Konstanten (vereinfacht)
k_g = 10  # Wie schnell Insulin den Zucker senkt 
k_i = 0.05  # Wie schnell Insulin abgebaut wird
k_abs = 0.03 # Wie schnell Nahrung ins Blut geht

class GlucoseSimulation:
    def __init__(self):
        self.time = np.arange(0, MINUTES, DT)
        self.glucose = np.full(MINUTES, G_BASAL)
        self.insulin = np.full(MINUTES, I_BASAL)
        self.meal_buffer = 0.0
        self.current_step = 0
        
        # Setup Plot
        self.fig, (self.ax_g, self.ax_i) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
        plt.subplots_adjust(bottom=0.2)
        
        self.line_g, = self.ax_g.plot(self.time, self.glucose, 'r-', label='Glukose (mg/dl)')
        self.line_i, = self.ax_i.plot(self.time, self.insulin, 'b-', label='Insulin (mU/L)')
        self.current_text = self.ax_g.text(
            0.98, 0.95, '', transform=self.ax_g.transAxes,
            ha='right', va='top', fontsize=12, fontweight='bold',
            bbox=dict(facecolor='white', alpha=0.7, edgecolor='gray')
        )
        
        self.ax_g.set_ylim(40, 300)
        self.ax_i.set_ylim(0, 100)
        self.ax_g.legend()
        self.ax_i.legend()
        self.ax_i.set_xlabel("Zeit (Minuten)")

        # Knöpfe hinzufügen
        ax_meal = plt.axes([0.15, 0.05, 0.3, 0.075])
        ax_ins = plt.axes([0.55, 0.05, 0.3, 0.075])
        self.btn_meal = Button(ax_meal, 'Nahrung (+50g KH)', color='orange')
        self.btn_ins = Button(ax_ins, 'Insulin (+10 Einheiten)', color='lightblue')
        
        self.btn_meal.on_clicked(self.add_meal)
        self.btn_ins.on_clicked(self.add_insulin)

    def add_meal(self, event):
        self.meal_buffer += 100.0 # Simulierter Anstieg
        print("Nahrung hinzugefügt!")

    def add_insulin(self, event):
        # Sofortiger Anstieg des Insulinspiegels an der aktuellen Stelle
        idx = self.current_step % MINUTES
        self.insulin[idx:] += 40.0
        print("Insulin gespritzt!")

    def update(self, frame):
        # Berechne nächsten Schritt (Euler-Verfahren)
        i = self.current_step % (MINUTES - 1)
        
        # 1. Insulin-Abbau
        di = -k_i * (self.insulin[i] - I_BASAL)
        self.insulin[i+1] = self.insulin[i] + di
        
        # 2. Glukose-Veränderung (Nahrungsaufnahme vs. Insulinwirkung)
        dg = -k_g * (self.insulin[i] - I_BASAL) + self.meal_buffer * k_abs
        self.glucose[i+1] = self.glucose[i] + dg
        
        # Nahrungseffekt lässt langsam nach
        self.meal_buffer *= 0.98 
        
        # Update Plot
        self.line_g.set_ydata(self.glucose)
        self.line_i.set_ydata(self.insulin)
        current_value = self.glucose[i+1]
        color = 'green' if current_value <= G_BASAL else 'red'
        self.current_text.set_text(f'Aktuell: {current_value:.1f} mg/dl')
        self.current_text.set_color(color)
        self.current_step += 1
        return self.line_g, self.line_i, self.current_text

# Simulation starten
sim = GlucoseSimulation()

# Animation (Interaktivität)
from matplotlib.animation import FuncAnimation
ani = FuncAnimation(sim.fig, sim.update, interval=50, blit=True)

plt.show()