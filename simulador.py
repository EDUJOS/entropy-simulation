import matplotlib.pyplot as plt
import numpy as np
import tkinter as tk
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation

class WaterPhaseChangeSimulation:
    def __init__(self, is_reversible=True):
        # Condiciones iniciales (convertidas a SI)
        self.mass = 3 #* 0.45359237  # 6 lbm a kg
        self.initial_pressure = 20 #* 6894.76  # 20 psia a Pa
        self.initial_temp = 70 if is_reversible else 55 # (70 - 32) * 5/9 + 273.15 if is_reversible else (55 - 32) * 5/9 + 273.15 # 70°F a K
        self.heat_input = 3450 if is_reversible else 4000 # * 1055.06  # 3450 Btu a Joules
        
        # Entropía específica inicial y final (convertida a J/kg·K)
        self.s1 = 0.07459 if is_reversible else 0.04586 # * 5380.03 if is_reversible else 0.04586 * 5380.003  # Btu/lbm·R a J/kg·K
        self.s2 = 1.7761 if is_reversible else 1.9591 # * 5380.03 if is_reversible else 1.8398 * 5380.003  # Btu/lbm·R a J/kg·K
        
        # Parámetros de visualización
        self.piston_length = 2.0  # m
        self.piston_width = 1.0   # m
        self.fixed_height = self.piston_length * 0.8  # Altura fija del pistón al 80% del espacio
        self.num_particles = 100
        
        # Control de la simulación
        self.is_reversible = is_reversible
        self.max_velocity = 2
        self.initial_velocity = 0.5
        self.heat_rate = 1.0 if is_reversible else 2.0  # Factor de velocidad del proceso
        
        # Configuración de la visualización
        self.fig, self.ax = plt.subplots(figsize=(4, 6))
        self.setup_plot()
        
        # Variables de control
        self.animation = None
        self.is_running = False
        
    def setup_plot(self):
        self.ax.set_xlim(0, self.piston_width)
        self.ax.set_ylim(0, self.piston_length)
        self.scatter = self.ax.scatter([], [], s=50)
        self.piston_line, = self.ax.plot([], [], 'r-', lw=2)
        self.ax.set_xlabel('Ancho (m)')
        self.ax.set_ylabel('Altura (m)')
        self.text_info = self.ax.text(0.02, 0.98, '', transform=self.ax.transAxes, verticalalignment='top')
        self.fig.tight_layout()

    def initialize_particles(self):
        # Partículas inicialmente más juntas (líquido)
        margin = 0.05
        positions = np.random.uniform(
            [margin, margin],
            [self.piston_width - margin, self.fixed_height - margin],
            (self.num_particles, 2)
        )
        
        # Velocidades iniciales bajas (líquido)
        angles = np.random.uniform(0, 2*np.pi, self.num_particles)
        velocities = np.zeros((self.num_particles, 2))
        velocities[:,0] = self.initial_velocity * 0.5 * np.cos(angles)
        velocities[:,1] = self.initial_velocity * 0.5 * np.sin(angles)
        
        return positions, velocities

    def calculate_phase_properties(self, progress):
        """Calcula las propiedades en función del progreso del calentamiento"""
        # Temperatura interpolada entre inicial y punto de ebullición
        boiling_temp = 227.92 # 373.15  # K (100°C)
        if progress < 0.5:
            # Calentamiento hasta ebullición
            temperature = self.initial_temp + (boiling_temp - self.initial_temp) * (2 * progress)
            phase = "liquid"
        else:
            # Vaporización
            temperature = boiling_temp # if self.is_reversible else 400 # (400 - 32) * 5/9 + 273.15
            phase = "mixed"
        
        # Entropía interpolada
        entropy = self.s1 + (self.s2 - self.s1) * progress
        
        return temperature, phase, entropy

    def update_particle_motion(self, positions, velocities, height, phase, temperature):
        """Actualiza el movimiento de las partículas según la fase"""
        dt = 0.03  # Paso de tiempo
        
        temperature_factor = np.sqrt(temperature / self.initial_temp)

        # Ajustar velocidades según la fase y temperatura
        if phase == "liquid":
            max_speed = self.max_velocity * 0.5 * temperature_factor
        else:
            max_speed = self.max_velocity * temperature_factor
        
        # Escalar velocidades
        speeds = np.linalg.norm(velocities, axis=1)
        scale_factors = np.minimum(max_speed / speeds, 1.0)
        velocities *= scale_factors[:, np.newaxis]
        
        # Actualizar posiciones
        new_positions = positions + velocities * dt
        
        # Colisiones
        for i in range(len(positions)):
            # Colisiones horizontales
            if new_positions[i,0] < 0:
                new_positions[i,0] = 0
                velocities[i,0] *= -0.95
            elif new_positions[i,0] > self.piston_width:
                new_positions[i,0] = self.piston_width
                velocities[i,0] *= -0.95
            
            # Colisiones verticales
            if new_positions[i,1] < 0:
                new_positions[i,1] = 0
                velocities[i,1] *= -0.95
            elif new_positions[i,1] > height:
                new_positions[i,1] = height
                velocities[i,1] *= -0.95
        
        return new_positions, velocities

    def run_simulation(self):
        self.is_running = True
        positions, velocities = self.initialize_particles()
        # current_height = self.piston_length / 3
        
        # Factor de irreversibilidad
        entropy_factor = 1.0 # if self.is_reversible else 1.2
        frame_count = 0
        data_history = []
        
        def update(frame):
            nonlocal positions, velocities, frame_count
            
            if not self.is_running:
                return self.scatter, self.piston_line, self.text_info
            
            # Progreso del proceso (0 a 1)
            progress = min(1.0, frame * 0.005 * self.heat_rate)
            
            # Calcular propiedades actuales
            temperature, phase, entropy = self.calculate_phase_properties(progress)
            
            # Actualizar altura del pistón (expansión)
            # if phase == "mixed":
            #     target_height = self.piston_length * (0.33 + 0.67 * (progress - 0.5) * 2)
            #     current_height = min(target_height, self.piston_length)
            
            # Actualizar partículas
            positions, velocities = self.update_particle_motion(
                positions, velocities, self.fixed_height, phase, temperature
            )
            
            # Visualización
            self.scatter.set_offsets(positions)
            speeds = np.linalg.norm(velocities, axis=1)
            colors = plt.cm.coolwarm(speeds / self.max_velocity)
            self.scatter.set_color(colors)
            self.piston_line.set_data([0, self.piston_width], [self.fixed_height, self.fixed_height])
            
            # Información en pantalla
            current_entropy = entropy * entropy_factor
            info_text = (
                f'T: {temperature:.1f}°F -> {(temperature - 32) * 5/9 + 273:.1f}K\n'
                f'P: {self.initial_pressure} Psia -> {(self.initial_pressure * 6894.76)/1000:.1f} kPa\n'
                f'Fase: {"Líquida" if phase=="liquid" else "Cambio de fase"}\n'
                f'S: {current_entropy} Btu/lbm·R -> {(current_entropy * 5380.03)/1000:.2f} kJ/kg·K'
            )
            self.text_info.set_text(info_text)
            
            # Guardar datos
            data_history.append((temperature, current_entropy))
            
            # Finalizar simulación
            if progress >= 1.0:
                frame_count += 1
                if frame_count > 300: # Esperar 15 segundos antes de cerrar
                    self.is_running = False
                    plt.close()
            
            return self.scatter, self.piston_line, self.text_info
        
        self.ax.clear()
        self.setup_plot()
        process_type = "Reversible" if self.is_reversible else "Irreversible"
        self.ax.set_title(f"Proceso Isobárico {process_type}")
        
        self.animation = FuncAnimation(
            self.fig,
            update,
            frames=None,
            interval=20,
            blit=True,
            cache_frame_data=False
        )
        
        plt.show()
        
        if data_history:
            final_temp, final_entropy = data_history[-1]
            return {
                "initial_temperature": self.initial_temp,  # K
                "final_temperature": final_temp,  # K
                "initial_pressure": self.initial_pressure,  # / 1000 kPa
                "final_pressure": self.initial_pressure,  # / 1000 kPa
                "initial_entropy": self.s1,  # / 1000 kJ/kg·K
                "final_entropy": self.s2,  # / 1000 kJ/kg·K
                "entropy_change": (self.mass * (self.s2 - self.s1))  # / 1000 kJ/K
            }
        return None

def setup_gui():
    root = tk.Tk()
    root.title("Simulación de Cambio de Fase Isobárico")
    
    sim = None
    
    def create_new_simulation(is_reversible):
        nonlocal sim
        if sim is not None:
            plt.close('all')
        sim = WaterPhaseChangeSimulation(is_reversible=is_reversible)
        return sim
    
    def run_reversible():
        sim = create_new_simulation(True)
        results = sim.run_simulation()
        if results:
            display_results(results, "Resultados del Proceso Reversible")

    def run_irreversible():
        sim = create_new_simulation(False)
        results = sim.run_simulation()
        if results:
            display_results(results, "Resultados del Proceso Irreversible")

    def display_results(results, title):
        result_text = (
            f"{title}\n\n"
            f"Masa: {sim.mass:.2f} lbm\n"
            f"Temperatura Inicial: {results['initial_temperature']:.1f}°F\n"
            f"Temperatura Final: {results['final_temperature']:.1f}°F\n"
            f"Presión: {results['initial_pressure']:.1f} Psia (constante)\n"
            f"Entropía Inicial: {results['initial_entropy']:.4f} Btu/lbm·R\n"
            f"Entropía Final: {results['final_entropy']:.4f} Btu/lbm·R\n"
            f"Cambio de Entropía: {results['entropy_change']:.4f} Btu/R"
        )
        messagebox.showinfo(title, result_text)

    button_frame = tk.Frame(root)
    button_frame.pack(pady=5)
    
    tk.Button(button_frame, text="Proceso Reversible", 
              command=run_reversible).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Proceso Irreversible", 
              command=run_irreversible).pack(side=tk.LEFT, padx=5)

    root.mainloop()

if __name__ == "__main__":
    setup_gui()