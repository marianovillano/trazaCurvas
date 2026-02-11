import sys
from PyHT6022.LibUsbScope import Oscilloscope
from threading import Thread
import threading

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Signal, QObject
import pyqtgraph as pg
import time
import serial
import serial.tools.list_ports


# Señales Qt para comunicación thread-safe
class WorkerSignals(QObject):
    """Señales para comunicación entre threads y la GUI"""
    uart_message = Signal(str)
    scope_message = Signal(str)


class CurveTracerWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Configuración global de pyqtgraph
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
        self.resize(900, 600)

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
        # Variables de configuración
        self.frequency = "5Hz"
        self.voltage = "200mV"
        self.impedance = "45R"
        self.use_scope = True

        # ---- Layout principal ----
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QHBoxLayout(central)

        # Área de gráfico
        self.plot_widget = pg.GraphicsLayoutWidget()
        main_layout.addWidget(self.plot_widget, 1)

        self.plot = self.plot_widget.addPlot()
        self.plot.showGrid(x=True, y=True)
        self.plot.setXRange(-5, 5)
        self.plot.setYRange(-5, 5)

        # --- Scatter principal ---
        self.curve = self.plot.plot()
        self.curve.setPen(None)
        self.curve.setSymbol('s')
        self.curve.setSymbolSize(0.5)
        self.curve.setSymbolBrush('y')

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

        # Panel de controles
        controls_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(controls_layout, 0)

        # Crear log e indicadores primero para evitar errores cuando los radio buttons se activen
        self.build_event_monitor(controls_layout)
        self.build_indicators(controls_layout)
        self.build_frequency_controls(controls_layout)
        self.build_voltage_controls(controls_layout)
        self.build_impedance_controls(controls_layout)

        controls_layout.addStretch()

        # Menú
        self.build_menu()

        # Timer de actualización del gráfico
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(10)  # 20ms = ~50 FPS

    # ----------------------- MENÚ -----------------------

    def build_menu(self):
        menubar = self.menuBar()

        ic_menu = menubar.addMenu("IC Profile")
        ic_menu.addSeparator()

        device_menu = menubar.addMenu("Device")
        device_menu.addAction("Connect...", self.connecting_window)
        device_menu.addAction("Disconnect", self.disconnecting_device)

        about_menu = menubar.addMenu("About")

    # ----------------------- CONTROLES -----------------------

    def build_frequency_controls(self, parent):
        group = QtWidgets.QGroupBox("Frequencies")
        layout = QtWidgets.QHBoxLayout(group)

        freqs = ["5Hz", "20Hz", "50Hz", "60Hz", "200Hz", "500Hz", "2kHz", "5kHz"]

        for f in freqs:
            btn = QtWidgets.QRadioButton(f)
            btn.toggled.connect(lambda checked, val=f: self.on_frequency(val) if checked else None)
            layout.addWidget(btn)
            if f == "5Hz":
                btn.setChecked(True)

        parent.addWidget(group)

    def on_frequency(self, value):
        self.clear_persistence()
        self.frequency = value
        self.show_frequency(value)
        self.freq_label.setText(value)

    def build_voltage_controls(self, parent):
        group = QtWidgets.QGroupBox("Voltages")
        layout = QtWidgets.QHBoxLayout(group)

        voltages = ["200mV", "3.3V", "5V", "9V"]

        for v in voltages:
            btn = QtWidgets.QRadioButton(v)
            btn.toggled.connect(lambda checked, val=v: self.on_voltage(val) if checked else None)
            layout.addWidget(btn)
            if v == "200mV":
                btn.setChecked(True)

        parent.addWidget(group)

    def on_voltage(self, value):
        self.clear_persistence()
        self.voltage = value
        self.show_voltage(value)
        self.volt_label.setText(value)

    def build_impedance_controls(self, parent):
        group = QtWidgets.QGroupBox("Impedance")
        layout = QtWidgets.QHBoxLayout(group)

        impedances = ["45R", "415R", "726R", "1.5kR"]

        for imp in impedances:
            btn = QtWidgets.QRadioButton(imp)
            btn.toggled.connect(lambda checked, val=imp: self.on_impedance(val) if checked else None)
            layout.addWidget(btn)
            if imp == "45R":
                btn.setChecked(True)

        parent.addWidget(group)

    def on_impedance(self, value):
        self.clear_persistence()
        self.impedance = value
        self.show_impedance(value)
        self.imp_label.setText(value)

    def build_indicators(self, parent):
        group = QtWidgets.QGroupBox("Indicators")
        layout = QtWidgets.QGridLayout(group)

        self.freq_label = QtWidgets.QLabel("5Hz")
        self.volt_label = QtWidgets.QLabel("200mV")
        self.imp_label = QtWidgets.QLabel("45R")

        font = self.freq_label.font()
        font.setPointSize(20)
        self.freq_label.setFont(font)
        self.volt_label.setFont(font)
        self.imp_label.setFont(font)

        layout.addWidget(QtWidgets.QLabel("Frequency"), 0, 0)
        layout.addWidget(self.freq_label, 1, 0)

        layout.addWidget(QtWidgets.QLabel("Voltage"), 2, 0)
        layout.addWidget(self.volt_label, 3, 0)

        layout.addWidget(QtWidgets.QLabel("Impedance"), 4, 0)
        layout.addWidget(self.imp_label, 5, 0)

        parent.addWidget(group)

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
        self.log.append(f"{now} - {text}")

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

        layout = QtWidgets.QGridLayout(dialog)

        # PORTS
        layout.addWidget(QtWidgets.QLabel("Select Port:"), 0, 0)
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if not ports:
            ports = ["NO_PORTS"]

        self.port_combo = QtWidgets.QComboBox()
        self.port_combo.addItems(ports)
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
        btn = QtWidgets.QPushButton("Connect")
        btn.clicked.connect(lambda: self.connecting_device(dialog))
        layout.addWidget(btn, 3, 1)

        dialog.exec()

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
                        self.frequency = self.frequency_dict[answer]
                        self.freq_label.setText(self.frequency)

                    elif answer.startswith("V"):
                        self.voltage = self.voltage_dict[answer]
                        self.volt_label.setText(self.voltage)

                    elif answer.startswith("R"):
                        self.impedance = self.impedance_dict[answer]
                        self.imp_label.setText(self.impedance)

                    elif answer.startswith("c"):
                        self.log_event("Remote capture command received")

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

        # 3. Atualizar curvas
        for i in range(self.persistence_depth):
            px, py = self.persistence_buffer[i]
            self.persistence_curves[i].setData(px, py)


    # def update_plot(self):
    #     with self.scope_lock:
    #         x = self.x_signal[:]
    #         y = self.y_signal[:]
    #
    #     if not x or not y:
    #         return
    #
    #     # Empurrar curvas antigas
    #     for i in range(self.persistence_depth - 1, 0, -1):
    #         old_x = self.persistence_curves[i - 1].xData
    #         old_y = self.persistence_curves[i - 1].yData
    #
    #         # Se não houver dados válidos, limpa
    #         if old_x is None or old_y is None:
    #             self.persistence_curves[i].setData([], [])
    #         else:
    #             self.persistence_curves[i].setData(old_x, old_y)
    #
    #     # Inserir curva nova no topo
    #     self.persistence_curves[0].setData(x, y)




    # def update_plot(self):
    #     with self.scope_lock:
    #         x = self.x_signal[:]
    #         y = self.y_signal[:]
    #
    #     if not x or not y:
    #         return
    #
    #     # Scatter real
    #     self.curve.setData(x, y)

def main():
    app = QtWidgets.QApplication(sys.argv)
    win = CurveTracerWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
