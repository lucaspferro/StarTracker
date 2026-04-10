import sys
import time
import math
import threading
import RPi.GPIO as GPIO
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont

# ==========================================
#      CONFIGURAÇÕES DE HARDWARE E FÍSICA
# ==========================================
DIR_PIN = 21
STEP_PIN = 20
ENABLE_PIN = 16

MOTOR_STEPS = 200       
MICROSTEPS = 16         
PASSOS_TOTAIS_REV = MOTOR_STEPS * MICROSTEPS

R_MM = 300.0          
P_MM = 0.7            
OM_RAD_MIN =  0.0043633 

CSS_STYLESHEET = """
    QGroupBox {
        font-weight: bold;
        border: 2px solid #444444;
        border-radius: 6px;
        margin-top: 15px;
        color: #0096DC;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top center;
        padding: 0 10px;
    }
    QPushButton {
        border-radius: 4px;
        padding: 10px;
        font-weight: bold;
    }
    QComboBox {
        background-color: #121214;
        border: 1px solid #444444;
        padding: 5px;
        color: white;
    }
"""
# ==========================================
#      CLASSE DO TRACKER (BACKEND)
# ==========================================
class AstroTracker:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(DIR_PIN, GPIO.OUT)
        GPIO.setup(STEP_PIN, GPIO.OUT)
        GPIO.setup(ENABLE_PIN, GPIO.OUT)

        self.tracking = False
        
        self.direction = 1  
        
        self.start_time = 0
        
        self.current_time_min = 0.0
        self.current_rpm = 0.0
        self.current_angle = 0.0

        # Inicia com o motor DESTRAVADO
        self.motor_power(False)

    def motor_power(self, state):
        if state:
            GPIO.output(ENABLE_PIN, GPIO.LOW)  # Engata (Trava)
            time.sleep(0.1) 
        else:
            GPIO.output(ENABLE_PIN, GPIO.HIGH) # Libera (Roda Livre)

    def run_tracking(self):
        self.motor_power(True)
        GPIO.output(DIR_PIN, self.direction)
        self.start_time = time.perf_counter()

        while self.tracking:
            self.current_time_min = (time.perf_counter() - self.start_time) / 60.0
            
            # Cálculo Isósceles
            w_t_sobre_2 = (OM_RAD_MIN * self.current_time_min) / 2.0
            vel_linear_mm_min = R_MM * OM_RAD_MIN * math.cos(w_t_sobre_2)
            self.current_rpm = vel_linear_mm_min / P_MM
            self.current_angle = math.degrees(OM_RAD_MIN * self.current_time_min)
            
            passos_por_segundo = (self.current_rpm * PASSOS_TOTAIS_REV) / 60.0
            delay_passo = 1.0 / passos_por_segundo

            # Pulso
            GPIO.output(STEP_PIN, GPIO.HIGH)
            time.sleep(0.00001)
            GPIO.output(STEP_PIN, GPIO.LOW)

            # Espera precisa
            target_time = time.perf_counter() + delay_passo - 0.00001
            while time.perf_counter() < target_time:
                if not self.tracking:
                    break
                time.sleep(0.0001) 

        self.motor_power(False)

    def start(self):
        if not self.tracking:
            self.tracking = True
            self.thread = threading.Thread(target=self.run_tracking, daemon=True)
            self.thread.start()

    def stop(self):
        self.tracking = False
        if hasattr(self, 'thread'):
            self.thread.join()
        self.motor_power(False)
        self.current_rpm = 0.0

# ==========================================
#      INTERFACE GRÁFICA (FRONTEND PyQt6)
# ==========================================
class TrackerGUI(QWidget):
    def __init__(self, tracker):
        super().__init__()
        self.tracker = tracker
        self.initUI()

        # Timer para atualizar a tela a cada 200 milissegundos
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(200)

    def initUI(self):
        self.setWindowTitle('AstroZeca: Barn Door Tracker')
        self.setFixedSize(400, 300)
        self.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")

        layout = QVBoxLayout()

        # Título
        lbl_title = QLabel("Controle Equatorial")
        lbl_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter) # Atualizado para PyQt6
        layout.addWidget(lbl_title)

        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine) # Atualizado para PyQt6
        line.setStyleSheet("color: #444444;")
        layout.addWidget(line)

        # Status Labels
        self.lbl_status = QLabel("Status: PARADO (Motor Livre)")
        self.lbl_status.setFont(QFont("Arial", 12))
        self.lbl_status.setStyleSheet("color: #ff5555;")
        layout.addWidget(self.lbl_status)

        self.lbl_time = QLabel("Tempo: 0.00 min")
        self.lbl_time.setFont(QFont("Arial", 14))
        layout.addWidget(self.lbl_time)

        self.lbl_angle = QLabel("Ângulo: 0.00°")
        self.lbl_angle.setFont(QFont("Arial", 14))
        layout.addWidget(self.lbl_angle)

        self.lbl_rpm = QLabel("Velocidade: 0.0000 RPM")
        self.lbl_rpm.setFont(QFont("Arial", 14))
        self.lbl_rpm.setStyleSheet("color: #55ff55;")
        layout.addWidget(self.lbl_rpm)

        # Botões
        btn_layout = QHBoxLayout()
        
        self.btn_start = QPushButton("▶ INICIAR TRACKING")
        self.btn_start.setStyleSheet("background-color: #2E8B57; padding: 15px; font-weight: bold; color: white;")
        self.btn_start.clicked.connect(self.start_tracking)
        
        self.btn_stop = QPushButton("⏸ PARAR")
        self.btn_stop.setStyleSheet("background-color: #B22222; padding: 15px; font-weight: bold; color: white;")
        self.btn_stop.clicked.connect(self.stop_tracking)

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def start_tracking(self):
        self.tracker.start()
        self.lbl_status.setText("Status: RASTREANDO (Motor Travado)")
        self.lbl_status.setStyleSheet("color: #55ff55;")

    def stop_tracking(self):
        self.tracker.stop()
        self.lbl_status.setText("Status: PARADO (Motor Livre)")
        self.lbl_status.setStyleSheet("color: #ff5555;")

    def update_ui(self):
        if self.tracker.tracking:
            self.lbl_time.setText(f"Tempo: {self.tracker.current_time_min:.2f} min")
            self.lbl_angle.setText(f"Ângulo: {self.tracker.current_angle:.4f}°")
            self.lbl_rpm.setText(f"Velocidade: {self.tracker.current_rpm:.5f} RPM")
        elif self.tracker.current_rpm == 0.0:
            self.lbl_rpm.setText("Velocidade: 0.0000 RPM")

# ==========================================
#      EXECUÇÃO DO PROGRAMA
# ==========================================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    app.setStyleSheet(CSS_STYLESHEET)
    
    GPIO.setmode(GPIO.BCM) # Garante modo antes de iniciar
    
    meu_tracker = AstroTracker()
    janela = TrackerGUI(meu_tracker)
    janela.show()
    
    try:
        # 2. Executa o loop da janela
        sys.exit(app.exec())
    finally:
        print("\n[SYSTEM] Encerrando interface...")
        
        meu_tracker.stop()
        
        GPIO.setwarnings(False)
        GPIO.setup(ENABLE_PIN, GPIO.OUT)
        GPIO.setup(STEP_PIN, GPIO.OUT)
        GPIO.setup(DIR_PIN, GPIO.OUT)
        
        GPIO.output(ENABLE_PIN, GPIO.HIGH)
        
        GPIO.output(STEP_PIN, GPIO.LOW)
        GPIO.output(DIR_PIN, GPIO.LOW)
        
        print("[SYSTEM] Pinos travados em estado seguro. Motor Livre.")
