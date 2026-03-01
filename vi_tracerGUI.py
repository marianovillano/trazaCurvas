import sys
from PyHT6022.LibUsbScope import Oscilloscope
from threading import Thread
import threading

from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import QWidget
from PySide6.QtWidgets import QComboBox
from PySide6.QtCore import Signal, QObject
import pyqtgraph as pg
import pyqtgraph.exporters
import time
import serial
import serial.tools.list_ports
import os
from PySide6.QtGui import QAction


# Señales Qt para comunicación thread-safe
class WorkerSignals(QObject):
    """Señales para comunicación entre threads y la GUI"""
    uart_message = Signal(str)
    scope_message = Signal(str)
    update_frequency = Signal(str)
    update_voltage = Signal(str)
    update_impedance = Signal(str)
    trigger_capture = Signal()  # Aciona captura de forma thread-safe


class PortComboBox(QComboBox):
    popup_about_to_show = Signal()

    def showPopup(self):
        self.popup_about_to_show.emit()
        super().showPopup()


class ICProfileWidget(QWidget):
    capture_requested = Signal(str)  # Emits path to save image to

    def __init__(self, parent=None):
        super().__init__(parent)
        self.btn_view_comp = None
        self.btn_capture = None
        self.btn_new_ic = None
        self.current_pin = 1
        self.lbl_pin_status = None
        self.btn_create_tree = None
        self.pin_count = None
        self.ic_name = None
        self.ic_label = None
        self.board_name = None
        self.base_folder = ""
        self.current_folder = ""
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QFormLayout(self)

        # Board Name
        self.board_name = QtWidgets.QLineEdit()
        layout.addRow("Board Name:", self.board_name)

        # IC Label (U...)
        self.ic_label = QtWidgets.QLineEdit()
        self.ic_label.setFixedWidth(60)
        layout.addRow("IC Label (U..):", self.ic_label)

        # IC Name
        self.ic_name = QtWidgets.QLineEdit()
        layout.addRow("IC Name:", self.ic_name)
        # layout.addRow(QtWidgets.QLabel("--- Capture ---"))

        # Pin Count
        self.pin_count = QtWidgets.QSpinBox()
        self.pin_count.setRange(1, 999)
        self.pin_count.setValue(1)
        layout.addRow("Nº of Pins:", self.pin_count)     

        # Create Tree Button
        self.btn_create_tree = QtWidgets.QPushButton("Create/Select Tree")
        self.btn_create_tree.clicked.connect(self.create_tree)
        layout.addRow(self.btn_create_tree)

        # Current Pin Status
        self.lbl_pin_status = QtWidgets.QLabel("Pin 1")
        layout.addRow("Pin to capture:", self.lbl_pin_status)
        # self.current_pin = 1
        
        # Status / New IC
        self.btn_new_ic = QtWidgets.QPushButton("New IC")
        self.btn_new_ic.clicked.connect(self.new_ic)
        layout.addRow(self.btn_new_ic)

        # Capture Button
        self.btn_capture = QtWidgets.QPushButton("Capture Trace")
        self.btn_capture.clicked.connect(self.capture)
        self.btn_capture.setEnabled(False)
        layout.addRow(self.btn_capture)

        # View Comparison
        self.btn_view_comp = QtWidgets.QPushButton("View Comparison")
        self.btn_view_comp.clicked.connect(self.view_comparison)
        layout.addRow(self.btn_view_comp)

    def create_tree(self):
        board = self.board_name.text().strip()
        label = self.ic_label.text().strip()

        if not board or not label:
            QtWidgets.QMessageBox.warning(self, "Missing Info", "Please enter Board Name and IC Label.")
            return

        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Base Folder")
        if folder:
            self.base_folder = folder
            # Create structure: Base/Board/Label
            self.current_folder = os.path.join(self.base_folder, board, label)
            os.makedirs(self.current_folder, exist_ok=True)
            QtWidgets.QMessageBox.information(self, "Created", f"Folder created:\n{self.current_folder}")
            self.btn_capture.setEnabled(True)
            #self.new_ic()

    def new_ic(self):
        self.current_pin = 1
        self.update_status()
        self.ic_name.clear()
        self.ic_label.clear()
        self.pin_count.setValue(1)
        self.ic_name.setEnabled(True)
        self.pin_count.setEnabled(True)

    def update_status(self):
        if self.current_pin > self.pin_count.value():
            return
        self.lbl_pin_status.setText(f"Pin {self.current_pin}")

    def capture(self):
        if not self.current_folder:
            return
        label = self.ic_label.text().strip()
        board = self.board_name.text().strip()
        self.current_folder = os.path.join(self.base_folder, board, label)
        os.makedirs(self.current_folder, exist_ok=True)
        
        ic_name = self.ic_name.text().strip()
        # ic_label = self.ic_label.text().strip() # Already have folder
        
        if not ic_name:
             QtWidgets.QMessageBox.warning(self, "Missing Info", "Please enter IC Name.")
             return

        if self.current_pin > self.pin_count.value():
            QtWidgets.QMessageBox.information(self, "Done", "All pins for this IC captured.")
            return

        # Matches Tkinter format: ICName_ICLabel_pinX.png
        # Tkinter: self.ic_name.get() + "_" +  self.ic_label.get() + "_" + "pin" + str(self.pin_captured) + ".png"
        filename = f"{ic_name}_{self.ic_label.text().strip()}_pin{self.current_pin}.png"
        path = os.path.join(self.current_folder, filename)
        
        self.capture_requested.emit(path)

        if self.current_pin == self.pin_count.value():
            QtWidgets.QMessageBox.information(self, "Done", "All pins for this IC captured.")
        self.current_pin += 1
        self.update_status()

    def view_comparison(self):
        # Open simple viewer for now
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Comparison Image", "", "Images (*.png *.jpg)")
        if file_path:
             os.startfile(file_path) # Simple open in default viewer


class CurveTracerWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Configuración global de pyqtgraph
        self.connect_btn = None
        self.scope_checkbox = None
        self.baud_combo = None
        self.port_combo = None
        self.log = None
        self.imp_label = None
        self.volt_label = None
        self.freq_label = None
        pg.setConfigOptions(antialias=True)

        # Diccionarios de comandos (copiados de Functions para evitar dependencia de Tkinter)
        self.frequencies = {"5Hz": "1", "20Hz": "2", "50Hz": "3", "60Hz": "4", "200Hz": "5", "500Hz": "6", "2kHz": "7", "5kHz": "8"}
        self.voltages = {"200mV": "9", "3.3V": "10", "5V": "11", "9V": "12"}
        self.d_impedance = {"45R": "13", "415R": "14", "726R": "15", "1.5kR": "16"}
        self.frequency_dict = {"F1": "5Hz", "F2": "20Hz", "F3": "50Hz", "F4": "60Hz", "F5": "200Hz", "F6": "500Hz", "F7": "2kHz", "F8": "5kHz"}
        self.voltage_dict = {"V9": "200mV", "V10": "3.3V", "V11": "5V", "V12": "9V"}
        self.impedance_dict = {"R13": "45R", "R14": "415R", "R15": "726R", "R16": "1.5kR"}

        # Inicializar señales para comunicación thread-safe
        self.signals = WorkerSignals()
        self.signals.uart_message.connect(lambda msg: self.log_event(msg))
        self.signals.scope_message.connect(lambda msg: self.log_event(msg))
        self.signals.update_frequency.connect(self.update_frequency_ui)
        self.signals.update_voltage.connect(self.update_voltage_ui)
        self.signals.update_impedance.connect(self.update_impedance_ui)

        # Variables de conexión y hardware
        self.uart = None
        self.scope = None
        self.calibration = None
        self.connection_active = False
        self.scope_is_run = False
        self.scope_thread = None
        self.thread_uart = None

        # Lock para acceso thread-safe a datos del scope
        self.scope_lock = threading.Lock()

        # Configuración de ventana
        self.setWindowTitle("Curve Tracer - Qt6")
        self.resize(1200, 800)

        # Estado de datos
        self.x_signal = []
        self.y_signal = []
        self.x_signal = []
        self.y_signal = []
        #self.plot_style = "line" # "line" o "scatter"

        # Variables de configuración
        self.frequency = "5Hz"
        self.voltage = "200mV"
        self.impedance = "45R"
        self.use_scope = True

        # Referencias a RadioButtons
        self.freq_radios = {}
        self.volt_radios = {}
        self.imp_radios = {}

        # ---- Layout principal ----
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        
        # --- NUEVA ESTRUCTURA DEL LAYOUT ---
        # --- NUEVA ESTRUCTURA DEL LAYOUT (Iteración 2) ---
        # Main Layout (Horizontal split)
        main_layout = QtWidgets.QHBoxLayout(central_widget)

        # ---------------- LEFT PANEL (Content) ----------------
        left_panel_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(left_panel_layout, stretch=4)

        # 1. Plot (Top)
        self.plot_widget = pg.PlotWidget(title="V-I Trace")
        self.plot_widget.setLabel('left', 'Current (mA)')
        self.plot_widget.setLabel('bottom', 'Voltage (V)')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setYRange(-5, 5)
        self.plot_widget.setXRange(-5, 5)
        left_panel_layout.addWidget(self.plot_widget, stretch=3)
        
        # Initialize PlotItem immediately
        self.plot = self.plot_widget.getPlotItem()
        self.plot_curve = self.plot.plot(pen=None, symbol='o', symbolSize=2, symbolBrush='y')

        # --- PERSISTÊNCIA PRO (tem de vir AQUI) ---
        self.persistence_depth = 10
        self.persistence_buffer = [([], []) for _ in range(self.persistence_depth)]
        self.persistence_curves = []

        for i in range(self.persistence_depth):
            alpha = int(255 * (1 - i / self.persistence_depth))
            curve = self.plot.plot(
                pen=None,
                symbol='s',
                symbolSize=0.3,
                symbolBrush=(255, 255, 0, alpha)
            )
            self.persistence_curves.append(curve)

        # 2. Indicators (Middle) - Horizontal
        indicators_group = QtWidgets.QGroupBox("Measurements")
        indicators_layout = QtWidgets.QHBoxLayout()
        indicators_group.setLayout(indicators_layout)
        self.build_indicators(indicators_layout) # This adds V/F/R labels
        left_panel_layout.addWidget(indicators_group)

        # 3. Log (Bottom)
        metrics_label = QtWidgets.QLabel("Events Monitor:")
        left_panel_layout.addWidget(metrics_label)
        
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150) # Increased height
        left_panel_layout.addWidget(self.log_text, stretch=1)

        # ---------------- RIGHT PANEL (Controls) ----------------
        right_panel_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(right_panel_layout, stretch=0) # Changed stretch to 0
        
        # Controls Group
        controls_group = QtWidgets.QGroupBox("Controls")
        controls_group.setSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Preferred) # Force minimum width
        controls_layout = QtWidgets.QVBoxLayout() # Vertical Layout for the group
        controls_layout.setSpacing(5)           # Reduce spacing between groups
        controls_layout.setContentsMargins(5, 5, 5, 5) # Reduce margins
        controls_group.setLayout(controls_layout)
        
        # 1. Frequency Column
        freq_col_layout = QtWidgets.QVBoxLayout()
        freq_col_layout.addWidget(QtWidgets.QLabel("<b>Frequency:</b>"))
        self.build_frequency_controls(freq_col_layout)
        freq_col_layout.addStretch() # Push items up
        controls_layout.addLayout(freq_col_layout)
        
        # Separator line (Optional, using frame or spacing)
        # controls_layout.addSpacing(10)
        
        # 2. Voltage Column
        volt_col_layout = QtWidgets.QVBoxLayout()
        volt_col_layout.addWidget(QtWidgets.QLabel("<b>Voltage:</b>"))
        self.build_voltage_controls(volt_col_layout)
        volt_col_layout.addStretch()
        controls_layout.addLayout(volt_col_layout)
        
        # 3. Impedance Column
        imp_col_layout = QtWidgets.QVBoxLayout()
        imp_col_layout.addWidget(QtWidgets.QLabel("<b>Impedance:</b>"))
        self.build_impedance_controls(imp_col_layout)
        imp_col_layout.addStretch()
        controls_layout.addLayout(imp_col_layout)
        
        # Add the horizontal group to the right panel
        right_panel_layout.addWidget(controls_group)
        right_panel_layout.addStretch()

        # -----------------------------------------------------

        # --- PERSISTÊNCIA PRO (tem de vir AQUI) ---
        self.persistence_depth = 10

        self.persistence_buffer = [([], []) for _ in range(self.persistence_depth)]
        self.persistence_curves = []

        for i in range(self.persistence_depth):
            alpha = int(255 * (1 - i / self.persistence_depth))
            curve = self.plot.plot(
                pen=None,
                symbol='s',
                symbolSize=0.3,
                symbolBrush=(255, 255, 0, alpha)
            )
    

        # Menú
        self.build_menu()

        # IC Profile Dock
        self.ic_dock = QtWidgets.QDockWidget("IC Profile", self)
        self.ic_profile_widget = ICProfileWidget()
        self.ic_profile_widget.capture_requested.connect(self.save_trace_image)
        self.signals.trigger_capture.connect(self.ic_profile_widget.capture)  # Captura via serial
        self.ic_dock.setWidget(self.ic_profile_widget)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.ic_dock)
        self.ic_dock.hide()

        # Timer de actualización del gráfico
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(10)  # 20ms = ~50 FPS
    
    def closeEvent(self, event):
        """Handle window close event to clean up resources."""
        self.disconnecting_device()
        event.accept()

    # ----------------------- MENÚ -----------------------

    def build_menu(self):
        menubar = self.menuBar()

        ic_menu = menubar.addMenu("IC Profile")
        capture_action = ic_menu.addAction("Capture IC traces")
        capture_action.triggered.connect(lambda: self.ic_dock.show())
        
        close_profile_action = ic_menu.addAction("Close IC traces")
        close_profile_action.triggered.connect(lambda: self.ic_dock.hide())
        
        ic_menu.addSeparator()

        device_menu = menubar.addMenu("Device")
        device_menu.addAction("Connect...", self.connecting_window)
        device_menu.addAction("Disconnect", self.disconnecting_device)

        about_menu = menubar.addMenu("About")

    # ----------------------- CONTROLES -----------------------

    def build_frequency_controls(self, parent):
        group = QtWidgets.QGroupBox("Frequencies")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setSpacing(1)  # Reduce spacing between buttons
        layout.setContentsMargins(1, 1, 1, 1) # Reduce group margins

        frequencies = ["5Hz", "20Hz", "50Hz", "60Hz", "200Hz", "500Hz", "2kHz", "5kHz"]


        for f in frequencies:
            btn = QtWidgets.QRadioButton(f)
            self.freq_radios[f] = btn  # Store reference
            btn.toggled.connect(lambda checked, val=f: self.on_frequency(val) if checked else None)
            layout.addWidget(btn)
            if f == "5Hz":
                btn.setChecked(True)

        parent.addWidget(group)

    def update_frequency_ui(self, value):
        self.frequency = value
        self.freq_label.setText(value)
        if value in self.freq_radios:
            btn = self.freq_radios[value]
            was_blocked = btn.blockSignals(True)
            btn.setChecked(True)
            btn.blockSignals(was_blocked)

    def on_frequency(self, value):
        self.clear_persistence()
        self.frequency = value
        self.show_frequency(value)
        self.freq_label.setText(value)

    def build_voltage_controls(self, parent):
        group = QtWidgets.QGroupBox("Voltages")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setSpacing(1)
        layout.setContentsMargins(2, 2, 2, 2)

        voltages = ["200mV", "3.3V", "5V", "9V"]


        for v in voltages:
            btn = QtWidgets.QRadioButton(v)
            self.volt_radios[v] = btn  # Store reference
            btn.toggled.connect(lambda checked, val=v: self.on_voltage(val) if checked else None)
            layout.addWidget(btn)
            if v == "200mV":
                btn.setChecked(True)

        parent.addWidget(group)

    def update_voltage_ui(self, value):
        self.voltage = value
        self.volt_label.setText(value)
        if value in self.volt_radios:
            btn = self.volt_radios[value]
            was_blocked = btn.blockSignals(True)
            btn.setChecked(True)
            btn.blockSignals(was_blocked)

    def on_voltage(self, value):
        self.clear_persistence()
        self.voltage = value
        self.show_voltage(value)
        self.volt_label.setText(value)

    def build_impedance_controls(self, parent):
        group = QtWidgets.QGroupBox("Impedance")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setSpacing(1)
        layout.setContentsMargins(2, 2, 2, 2)

        impedance = ["45R", "415R", "726R", "1.5kR"]


        for imp in impedance:
            btn = QtWidgets.QRadioButton(imp)
            self.imp_radios[imp] = btn  # Store reference
            btn.toggled.connect(lambda checked, val=imp: self.on_impedance(val) if checked else None)
            layout.addWidget(btn)
            if imp == "45R":
                btn.setChecked(True)

        parent.addWidget(group)

    def update_impedance_ui(self, value):
        self.impedance = value
        self.imp_label.setText(value)
        if value in self.imp_radios:
            btn = self.imp_radios[value]
            was_blocked = btn.blockSignals(True)
            btn.setChecked(True)
            btn.blockSignals(was_blocked)

    def on_impedance(self, value):
        self.clear_persistence()
        self.impedance = value
        self.show_impedance(value)
        self.imp_label.setText(value)

    def build_indicators(self, parent):
        # Create labels
        self.freq_label = QtWidgets.QLabel("5Hz")
        self.volt_label = QtWidgets.QLabel("200mV")
        self.imp_label = QtWidgets.QLabel("45R")

        font = self.freq_label.font()
        font.setPointSize(14) # Reduced from 20 to 14
        self.freq_label.setFont(font)
        self.volt_label.setFont(font)
        self.imp_label.setFont(font)
        
        # 1. Frequency Column
        freq_layout = QtWidgets.QVBoxLayout()
        freq_layout.addWidget(QtWidgets.QLabel("Frequency"))
        freq_layout.addWidget(self.freq_label)
        parent.addLayout(freq_layout)
        
        parent.addSpacing(30)

        # 2. Voltage Column
        volt_layout = QtWidgets.QVBoxLayout()
        volt_layout.addWidget(QtWidgets.QLabel("Voltage"))
        volt_layout.addWidget(self.volt_label)
        parent.addLayout(volt_layout)
        
        parent.addSpacing(30)

        # 3. Impedance Column
        imp_layout = QtWidgets.QVBoxLayout()
        imp_layout.addWidget(QtWidgets.QLabel("Impedance"))
        imp_layout.addWidget(self.imp_label)
        parent.addLayout(imp_layout)
        
        parent.addStretch()

    def build_event_monitor(self, parent):
        group = QtWidgets.QGroupBox("Events monitor")
        layout = QtWidgets.QVBoxLayout(group)

        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet("""
            background-color: #000;
            color: #0f0;
            font-family: Consolas, monospace;
        """)

        layout.addWidget(self.log)
        parent.addWidget(group)

    def log_event(self, text):
        from datetime import datetime
        now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        self.log_text.append(f"{now} - {text}")

    # ----------------------- COMANDOS DE CONTROL -----------------------

    def show_frequency(self, value):
        if not self.connection_active or self.uart is None:
            # self.log_event("UART connection object isn't initiated yet")
            return

        # Envía comando
        cmd = self.frequencies[value]
        self.send_command(cmd)

        # Actualiza el osciloscopio
        if self.use_scope and self.scope is not None:
            if value == "5Hz":
                self.scope.set_sample_rate(102)
            elif value == "20Hz":
                self.scope.set_sample_rate(106)
            elif value in ("50Hz", "60Hz"):
                self.scope.set_sample_rate(110)
            elif value == "200Hz":
                self.scope.set_sample_rate(150)
            else:
                self.scope.set_sample_rate(1)

    def show_voltage(self, value):
        if not self.connection_active or self.uart is None:
            # self.log_event("UART connection object isn't initiated yet")
            return

        cmd = self.voltages[value]
        self.send_command(cmd)

        if self.use_scope and self.scope is not None:
            if value == "200mV":
                self.scope.set_ch1_voltage_range(10)
                self.scope.set_ch2_voltage_range(10)
            else:
                self.scope.set_ch1_voltage_range(1)
                self.scope.set_ch2_voltage_range(1)

    def show_impedance(self, value):
        if not self.connection_active or self.uart is None:
            # self.log_event("UART connection object isn't initiated yet")
            return

        cmd = self.d_impedance[value]
        self.send_command(cmd)

    def send_command(self, message):
        try:
            if self.uart is not None:
                self.uart.write(message.encode("utf-8"))
                self.log_event(f"Sending: {message}")
            else:
                self.log_event("UART connection object isn't initiated yet")
        except Exception as e:
            self.log_event(repr(e))

    # ----------------------- CONEXIÓN -----------------------

    def connecting_window(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Configure serial communication")
        dialog.setModal(True)
        dialog.resize(350, 100)

        layout = QtWidgets.QGridLayout(dialog)

        # PORTS
        layout.addWidget(QtWidgets.QLabel("Select Port:"), 0, 0)
        
        self.port_combo = PortComboBox()
        self.port_combo.popup_about_to_show.connect(self.refresh_ports)
        layout.addWidget(self.port_combo, 0, 1)

        # BAUD
        layout.addWidget(QtWidgets.QLabel("Select Baud Rate:"), 1, 0)
        self.baud_combo = QtWidgets.QComboBox()
        self.baud_combo.addItems(["2400", "4800", "9600", "14400", "19200", "57600", "115200"])
        self.baud_combo.setCurrentText("9600")
        layout.addWidget(self.baud_combo, 1, 1)

        # SCOPE CHECKBOX
        self.scope_checkbox = QtWidgets.QCheckBox("Connect Scope")
        self.scope_checkbox.setChecked(True)
        layout.addWidget(self.scope_checkbox, 2, 1)

        # CONNECT BUTTON
        self.connect_btn = QtWidgets.QPushButton("Connect")
        self.connect_btn.clicked.connect(lambda: self.connecting_device(dialog))
        layout.addWidget(self.connect_btn, 3, 1)

        # Initial refresh
        self.refresh_ports()

        dialog.exec()

    def refresh_ports(self):
        """Refresh the list of available COM ports and update connect button state."""
        current_selection = self.port_combo.currentText()
        self.port_combo.blockSignals(True)
        self.port_combo.clear()
        
        ports = [p.device for p in serial.tools.list_ports.comports()]
        
        if not ports:
            self.port_combo.addItems(["NO_PORTS"])
            self.connect_btn.setEnabled(False)
        else:
            self.port_combo.addItems(ports)
            self.connect_btn.setEnabled(True)
            
            # Restore previous selection if still available
            index = self.port_combo.findText(current_selection)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)
        
        self.port_combo.blockSignals(False)

    def connecting_device(self, dialog):
        port = self.port_combo.currentText()
        baud = int(self.baud_combo.currentText())
        self.use_scope = self.scope_checkbox.isChecked()

        try:
            self.uart = serial.Serial(port, baudrate=baud, timeout=0.1, write_timeout=0.1)
            self.connection_active = True

            # Thread de lectura UART
            self.thread_uart = Thread(target=self.read_from_port, daemon=True)
            self.thread_uart.start()

            self.send_command("hello")

        except Exception as e:
            self.log_event(repr(e))
            return

        # Iniciar scope
        if self.use_scope:
            self.starting_scope()
            if self.scope_is_run:
                self.log_event("Scope started")

        dialog.accept()

    def read_from_port(self):
        while self.connection_active:
            try:
                if self.uart.in_waiting > 0:
                    answer = self.uart.read_until().decode("utf-8").strip()
                    self.signals.uart_message.emit(f"Receiving: {answer}")

                    if answer.startswith("F"):
                        val = self.frequency_dict.get(answer)
                        if val:
                             self.signals.update_frequency.emit(val)

                    elif answer.startswith("V"):
                        val = self.voltage_dict.get(answer)
                        if val:
                             self.signals.update_voltage.emit(val)

                    elif answer.startswith("R"):
                        val = self.impedance_dict.get(answer)
                        if val:
                             self.signals.update_impedance.emit(val)

                    elif answer.startswith("cap"):
                        self.signals.uart_message.emit("Remote capture command received")
                        self.signals.trigger_capture.emit()  # thread-safe: GUI executa a captura
            except Exception as e:
                self.signals.uart_message.emit(repr(e))
                break

    def disconnecting_device(self):
        """Disconnect UART and stop scope capture."""

        # --- UART ---
        if self.uart is not None:
            self.send_command("bye")
            time.sleep(0.1)

            self.connection_active = False
            try:
                self.uart.close()
            except Exception as e:
                self.log_event(f"UART close error: {e}")

            time.sleep(0.1)
            self.log_event("UART disconnected")
        else:
            self.log_event("Nothing to disconnect")

        # --- SCOPE ---
        if self.scope is not None:
            self.scope_is_run = False

            if self.use_scope:
                try:
                    self.scope.stop_capture()
                    time.sleep(0.5)
                    self.scope.close_handle()
                    
                    if self.scope_thread and self.scope_thread.is_alive():
                        self.scope_thread.join(timeout=2.0)
                        
                    self.log_event("Scope stopped and closed")
                except Exception as e:
                    self.log_event(f"Scope error: {e}")

    # ----------------------- OSCILOSCOPIO -----------------------

    def starting_scope(self):
        """Configura e inicia la thread de captura del Hantek."""
        try:
            self.scope = Oscilloscope()
            self.scope.setup()

            if not self.scope.open_handle():
                self.log_event("Oscilloscope not detected")
                return

            # Firmware
            if not self.scope.is_device_firmware_present:
                self.scope.flash_firmware()

            # Calibración
            self.calibration = self.scope.get_calibration_values()

            # Interface y canales
            self.scope.set_interface(0)  # BULK
            self.scope.set_num_channels(2)
            self.scope.set_sample_rate(102)

            # Ganhos iniciales
            self.scope.set_ch1_voltage_range(10)
            self.scope.set_ch2_voltage_range(10)

            # Thread de captura
            self.scope_is_run = True
            self.scope_thread = Thread(target=self.get_data, daemon=True)
            self.scope_thread.start()

            self.log_event("Oscilloscope started")

        except Exception as e:
            self.log_event(f"Scope error: {e}")

    def get_data(self):
        """Captura contínua de los dos canales del Hantek."""
        try:
            self.scope.start_capture()
            self.scope.read_data(data_size=0xC00, raw=True)  # Descartar primer bloque

            while self.scope_is_run:
                raw_ch1, raw_ch2 = self.scope.read_data(data_size=0xC00, raw=True)

                if len(raw_ch1) != 0xC00 or len(raw_ch2) != 0xC00:
                    continue

                ch1 = self.scope.scale_read_data(raw_ch1, channel=1)
                ch2 = self.scope.scale_read_data(raw_ch2, channel=2)

                # Actualiza buffers de plot
                with self.scope_lock:
                    self.x_signal = ch1
                    self.y_signal = ch2

        except Exception as e:
            self.signals.scope_message.emit(f"Scope thread error: {e}")

    # ----------------------- ACTUALIZACIÓN DE GRÁFICO -----------------------

    def clear_persistence(self):
        # 3. Atualizar curvas
        if hasattr(self, 'persistence_curves'):
             if len(self.persistence_curves) < self.persistence_depth:
                return

        for i in range(self.persistence_depth):
            self.persistence_buffer[i] = ([], [])
            self.persistence_curves[i].setData([], [])


    def update_plot(self):
        with self.scope_lock:
            x = self.x_signal[:]
            y = self.y_signal[:]

        if not x or not y:
            return

        # 1. Empurrar o buffer (shift)
        for i in range(self.persistence_depth - 1, 0, -1):
            self.persistence_buffer[i] = self.persistence_buffer[i - 1]

        # 2. Inserir o frame novo no topo
        self.persistence_buffer[0] = (x, y)

        # 2b. Atualizar a curva PRINCIPAL (para garantir visualização imediata)
        if hasattr(self, 'plot_curve'):
            self.plot_curve.setData(x, y)

        # 3. Atualizar curvas
        # 3. Atualizar curvas
        if hasattr(self, 'persistence_curves'):
             if len(self.persistence_curves) < self.persistence_depth:
                # Force re-initialization if empty (Emergency fix attempt)
                if len(self.persistence_curves) == 0:
                     for i in range(self.persistence_depth):
                        alpha = int(255 * (1 - i / self.persistence_depth))
                        curve = self.plot.plot(pen=None, symbol='s', symbolSize=0.3, symbolBrush=(255, 255, 0, alpha))
                        self.persistence_curves.append(curve)
                return # Skip this frame, wait for next
        else:
             return

        for i in range(self.persistence_depth):
            px, py = self.persistence_buffer[i]
            self.persistence_curves[i].setData(px, py)

    def save_trace_image(self, path):
        """Save the current plot state to an image file."""
        exporter = pg.exporters.ImageExporter(self.plot)
        exporter.parameters()['width'] = 800
        exporter.export(path)
        self.log_event(f"Saved trace to {os.path.basename(path)}")


def main():
    app = QtWidgets.QApplication(sys.argv)
    win = CurveTracerWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
