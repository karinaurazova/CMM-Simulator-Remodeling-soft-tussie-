import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                            QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                            QDoubleSpinBox, QComboBox, QGroupBox, QFileDialog,
                            QCheckBox, QFormLayout, QScrollArea, QSpinBox,
                            QMessageBox)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from core.models import ConstrainedMixtureModel

class CMMGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CMM Simulator - Remodeling soft tussie")
        self.setGeometry(100, 100, 1400, 900)
        self.model = None
        self.results = {}
        self.all_results = {}
        self.init_ui()
        self.setup_styles()
        
    def init_ui(self):
        self.tabs = QTabWidget()
        self.setup_control_tab()
        self.setup_visualization_tab()
        self.setup_comparison_tab()
        self.setCentralWidget(self.tabs)
    
    def setup_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #aaa;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: white;
            }
            QPushButton {
                min-height: 30px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QComboBox, QDoubleSpinBox, QSpinBox {
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 4px;
                min-width: 120px;
            }
        """)

    def setup_control_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout(content)
        
        protocol_params = [
            ('protocol_type', 0, 0, 2, 1, 0, "Protocol Type: 0=Persistent, 1=Linear, 2=Cyclic"),
            ('a', 0.1, 0.01, 1.0, 0.01, 3, "The parameter of the rate of deformation growth"),
            ('lambda_roof', 1.1, 1.0, 2.0, 0.01, 2, "Base Stretch Value")
        ]
        layout.addWidget(self.create_parameter_group("Loading Protocol", protocol_params))

        mechanical_params = [
            ('c_c', 1.0, 0.1, 100.0, 0.1, 2, "Collagen stiffness [kPa]"),
            ('c_e', 50.0, 1.0, 200.0, 1.0, 1, "Elastin stiffness [kPa]"),
            ('c_g', 10.0, 1.0, 50.0, 1.0, 1, "Matrix stiffness [kPa]")
        ]
        layout.addWidget(self.create_parameter_group("Mechanical properties", mechanical_params))

        initial_params = [
            ('fi0_c', 0.75, 0.01, 1.0, 0.01, 2, "Initial collagen content"),
            ('fi0_e', 0.05, 0.01, 1.0, 0.01, 2, "Initial elastin content"),
            ('fi0_g', 0.20, 0.01, 1.0, 0.01, 2, "Initial matrix content"),
            ('lambda0_c', 1.05, 1.0, 2.0, 0.01, 2, "Initial stretching of collagen"),
            ('lambda0_e', 1.10, 1.0, 2.0, 0.01, 2, "Initial stretching of elastin")
        ]
        layout.addWidget(self.create_parameter_group("Initial parameters", initial_params))

        remodel_params = [
            ('k_cplus', 1.0, 0.0, 10.0, 0.1, 2, "Rate of collagen synthesis"),
            ('k_cminus', 1.0, 0.0, 10.0, 0.1, 2, "Rate of collagen degradation"),
            ('k_eplus', 1.0, 0.0, 10.0, 0.1, 2, "Elastin synthesis rate"),
            ('k_eminus', 1.0, 0.0, 10.0, 0.1, 2, "Rate of elastin degradation"),
            ('alpha_c', 0.01, 0.0, 0.1, 0.001, 4, "Collagen nonlinearity coefficient"),
            ('gamma', 1.0, 0.1, 5.0, 0.1, 1, "Anisotropy parameter")
        ]
        layout.addWidget(self.create_parameter_group("Tissue remodeling", remodel_params))
        
        feedback_params = [
            ('K_cplus', 0.04, 0.0, 0.5, 0.01, 3, "Feedback coefficient"),
            ('sigma0_c', 1.0, 0.1, 10.0, 0.1, 2, "Homeostatic stress")
        ]
        layout.addWidget(self.create_parameter_group("Mechanical feedback", feedback_params))

        sim_params = [
            ('t_end', 10.0, 1.0, 100.0, 1.0, 1, "Simulation time [days]"),
            ('n_points', 1000, 100, 10000, 100, 0, "Number of sampling points"),
            ('epsilon', 1e-4, 1e-6, 1e-2, 1e-4, 6, "Calculation accuracy")
        ]
        layout.addWidget(self.create_parameter_group("Simulation parameters", sim_params))

        btn_layout = QHBoxLayout()
        self.run_btn = QPushButton("Run the simulation")
        self.run_btn.clicked.connect(self.run_simulation)
        self.save_btn = QPushButton("Save settings")
        self.save_btn.clicked.connect(self.save_parameters)
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll)
        self.tabs.addTab(tab, "Control")

    def setup_visualization_tab(self):
        self.vis_tab = QWidget()
        layout = QVBoxLayout()
        
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        
        control_layout = QHBoxLayout()
        self.plot_type = QComboBox()
        self.plot_type.addItems([
            "Component stress",
            "Volume fractions",
            "Protocol comparison"
        ])
        self.plot_type.currentIndexChanged.connect(self.update_plot)
        
        control_layout.addWidget(QLabel("Chart type:"))
        control_layout.addWidget(self.plot_type)
        
        self.save_plot_btn = QPushButton("Save chart")
        self.save_plot_btn.clicked.connect(self.save_plot)
        control_layout.addWidget(self.save_plot_btn)
        
        layout.addLayout(control_layout)
        layout.addWidget(self.canvas)
        self.vis_tab.setLayout(layout)
        self.tabs.addTab(self.vis_tab, "Visualization")

    def setup_comparison_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        self.compare_group = QGroupBox("Selecting protocols for comparison")
        compare_layout = QHBoxLayout()
        self.protocol_checks = {}
        protocols = ['constant', 'linear', 'cyclic']
        for protocol in protocols:
            cb = QCheckBox(self._protocol_name(protocol))
            cb.setChecked(True)
            self.protocol_checks[protocol] = cb
            compare_layout.addWidget(cb)
        
        self.compare_group.setLayout(compare_layout)
        layout.addWidget(self.compare_group)
        
        self.compare_figure = Figure(figsize=(10, 6))
        self.compare_canvas = FigureCanvas(self.compare_figure)
        layout.addWidget(self.compare_canvas)
        
        self.update_compare_btn = QPushButton("Update comparison")
        self.update_compare_btn.clicked.connect(self.update_comparison_plot)
        layout.addWidget(self.update_compare_btn)
        
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Protocol comparison")

    def create_parameter_group(self, title, parameters):
        group = QGroupBox(title)
        layout = QFormLayout()
        
        for param in parameters:
            name, default, min_val, max_val, step, decimals, tooltip = param
            spinbox = QDoubleSpinBox()
            spinbox.setRange(min_val, max_val)
            spinbox.setValue(default)
            spinbox.setSingleStep(step)
            spinbox.setDecimals(decimals)
            spinbox.setToolTip(tooltip)
            
            setattr(self, f"{name}_spin", spinbox)
            
            layout.addRow(QLabel(name.replace('_', ' ').title() + ":"), spinbox)
        
        group.setLayout(layout)
        return group

    def _protocol_name(self, protocol):
        names = {
            'constant': "Constant load (0)",
            'linear': "Linear load (1)", 
            'cyclic': "Cyclic load (2)"
        }
        return names.get(protocol, protocol)

    def get_current_parameters(self):
        params = {
            'protocol': ['constant', 'linear', 'cyclic'][int(self.protocol_type_spin.value())],
            'a': self.a_spin.value(),
            'lambda_roof': self.lambda_roof_spin.value(),
            'c_c': self.c_c_spin.value(),
            'c_e': self.c_e_spin.value(),
            'c_g': self.c_g_spin.value(),
            'fi0_c': self.fi0_c_spin.value(),
            'fi0_e': self.fi0_e_spin.value(),
            'fi0_g': self.fi0_g_spin.value(),
            'lambda0_c': self.lambda0_c_spin.value(),
            'lambda0_e': self.lambda0_e_spin.value(),
            'k_cplus': self.k_cplus_spin.value(),
            'k_cminus': self.k_cminus_spin.value(),
            'k_eplus': self.k_eplus_spin.value(),
            'k_eminus': self.k_eminus_spin.value(),
            'alpha_c': self.alpha_c_spin.value(),
            'gamma': self.gamma_spin.value(),
            'K_cplus': self.K_cplus_spin.value(),
            'sigma0_c': self.sigma0_c_spin.value(),
            't_end': self.t_end_spin.value(),
            'n_points': int(self.n_points_spin.value()),
            'epsilon': self.epsilon_spin.value()
        }
        return params

    def run_simulation(self):
        try:
            params = self.get_current_parameters()
            self.model = ConstrainedMixtureModel(params)
            
            use_feedback = self.K_cplus_spin.value() > 0
            protocol = params['protocol']
    
            if not hasattr(self, 'all_results'):
                self.all_results = {}
            
            self.results = self.model.simulate(protocol, feedback=use_feedback)
            self.all_results[protocol] = self.results
            
            self.update_plot()
            self.tabs.setCurrentIndex(1)
            
            QMessageBox.information(
                self, 
                "Simulation completed", 
                f"Calculation completed successfully!\n"
                f"Protocol:{self._protocol_name(protocol)}\n"
                f"Mechanical feedback: {'Yes' if use_feedback else 'No'}\n"
                f"Final stress: {self.results['sigma_total'][-1]:.2f} kPa"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Simulation error", 
                f"Calculation failed:\n{str(e)}"
            )

    def update_plot(self):
        if not hasattr(self, 'results') or not self.results:
            return
            
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        t = self.results['time']
        
        plot_type = self.plot_type.currentText()
        protocol = self.get_current_parameters()['protocol']
        protocol_name = self._protocol_name(protocol)
        
        if plot_type == "Component stress":
            if 'sigma_c' in self.results:
                ax.plot(t, self.results['sigma_c'], label='Collagen', linewidth=2)
            if 'sigma_e' in self.results:
                ax.plot(t, self.results['sigma_e'], label='Elastin', linewidth=2)
            if 'sigma_g' in self.results:
                ax.plot(t, self.results['sigma_g'], label='Matrix', linewidth=2)
            
            ax.set_title(f"Component stress\n{protocol_name}", fontsize=12)
            ax.set_ylabel('Stress (kPa)')
            ax.legend()
            
        elif plot_type == "Volume fractions":
            if 'J_c' in self.results:
                ax.plot(t, self.results['J_c'], label='Collagen', linewidth=2)
            if 'J_e' in self.results:
                ax.plot(t, self.results['J_e'], label='Elastin', linewidth=2)
            if 'J_g' in self.results:
                ax.plot(t, [self.params['Jg0']]*len(t), label='Matrix', linewidth=2)
            
            ax.set_title(f"Volume fractions companents\n{protocol_name}", fontsize=12)
            ax.set_ylabel('Volume fraction')
            ax.legend()
        
        ax.set_xlabel('Time (days)')
        ax.grid(True, linestyle='--', alpha=0.6)
        self.canvas.draw()

    def update_comparison_plot(self):
        self.compare_figure.clear()
        ax = self.compare_figure.add_subplot(111)
        
        selected_protocols = [p for p, cb in self.protocol_checks.items() 
                            if cb.isChecked() and p in self.all_results]
        
        for protocol in selected_protocols:
            data = self.all_results[protocol]
            ax.plot(data['time'], data['sigma_total'], 
                   label=self._protocol_name(protocol),
                   linewidth=2)
        
        ax.set_title("Comparison of stress by protocols", fontsize=12)
        ax.set_xlabel("Time (days)")
        ax.set_ylabel("Total stress (kPa)")
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.6)
        self.compare_canvas.draw()

    def save_parameters(self):
        params = self.get_current_parameters()
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save settings", "", 
            "JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            import json
            with open(filename, 'w') as f:
                json.dump(params, f, indent=4)
            
            QMessageBox.information(
                self, 
                "Saving complete", 
                f"Parameters have been successfully saved to the file:\n{filename}"
            )

    def save_plot(self):
        if not hasattr(self, 'results'):
            QMessageBox.warning(
                self,
                "No data",
                "Run a simulation first"
            )
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save chart", "", 
            "PNG Images (*.png);;PDF Files (*.pdf);;All Files (*)"
        )
        
        if filename:
            if self.tabs.currentIndex() == 1:
                self.figure.savefig(filename, dpi=300, bbox_inches='tight')
            else:  
                self.compare_figure.savefig(filename, dpi=300, bbox_inches='tight')
            
            QMessageBox.information(
                self, 
                "Saving complete", 
                f"Chart have been successfully saved to the file:\n{filename}"
            )

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    try:
        from PyQt5.QtGui import QIcon
        app.setWindowIcon(QIcon('icon.png'))
    except:
        pass
    
    window = CMMGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
