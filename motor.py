import sys
import time
import math
import threading
import RPi.GPIO as GPIO

from PyQt6.QtWidgets import *
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QLinearGradient

# ==========================================
# CONFIG
# ==========================================
DIR_PIN    = 21
STEP_PIN   = 20
ENABLE_PIN = 16

MOTOR_STEPS      = 200
MICROSTEPS       = 16
PASSOS_TOTAIS_REV = MOTOR_STEPS * MICROSTEPS

R_MM       = 300.0
P_MM       = 0.7
OM_RAD_MIN = 0.0043633

# ==========================================
# BACKEND
# ==========================================
class AstroTracker:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(DIR_PIN,    GPIO.OUT)
        GPIO.setup(STEP_PIN,   GPIO.OUT)
        GPIO.setup(ENABLE_PIN, GPIO.OUT)

        self.tracking      = False
        self.is_manual     = False
        self._rewind_event = threading.Event()
        self.manual_rpm    = 0.0
        self.direction     = 1
        self.start_time    = 0

        self.current_time_min = 0.0
        self.current_rpm      = 0.0
        self.current_angle    = 0.0

        self.motor_power(False)

    @property
    def is_rewinding(self):
        return self._rewind_event.is_set()

    def motor_power(self, state):
        GPIO.output(ENABLE_PIN, GPIO.LOW if state else GPIO.HIGH)
        if state:
            time.sleep(0.1)

    # --- ISOSCELES TRACKING ---
    def run_tracking(self):
        self.motor_power(True)
        GPIO.output(DIR_PIN, self.direction)
        self.start_time = time.perf_counter()

        while self.tracking:
            self.current_time_min = (time.perf_counter() - self.start_time) / 60.0
            w   = (OM_RAD_MIN * self.current_time_min) / 2.0
            vel = R_MM * OM_RAD_MIN * math.cos(w)

            self.current_rpm   = vel / P_MM
            self.current_angle = math.degrees(OM_RAD_MIN * self.current_time_min)

            passos_por_segundo = (self.current_rpm * PASSOS_TOTAIS_REV) / 60.0
            delay_passo        = 1.0 / passos_por_segundo

            GPIO.output(STEP_PIN, GPIO.HIGH)
            GPIO.output(STEP_PIN, GPIO.LOW)

            target = time.perf_counter() + delay_passo - 0.00001
            while time.perf_counter() < target:
                if not self.tracking:
                    break
                time.sleep(0.001)

        self.motor_power(False)

    # --- MANUAL MODE ---
    def run_manual(self):
        self.motor_power(True)

        while self.is_manual:
            rpm_alvo = self.manual_rpm

            if abs(rpm_alvo) < 0.1:
                self.current_rpm = 0.0
                time.sleep(0.05)
                continue

            self.current_rpm = rpm_alvo
            current_dir = self.direction if rpm_alvo > 0 else (0 if self.direction == 1 else 1)
            GPIO.output(DIR_PIN, current_dir)

            passos_por_seg = (abs(rpm_alvo) * PASSOS_TOTAIS_REV) / 60.0
            delay = 1.0 / passos_por_seg

            GPIO.output(STEP_PIN, GPIO.HIGH)
            time.sleep(0.00001)
            GPIO.output(STEP_PIN, GPIO.LOW)

            target = time.perf_counter() + delay - 0.00001
            while time.perf_counter() < target:
                if not self.is_manual or self.manual_rpm != rpm_alvo:
                    break
                time.sleep(0.0001)

        self.motor_power(False)

    # --- REWIND ---
    def run_rewind(self):
        print("[MOTOR] Starting rewind...")
        self.motor_power(True)

        dir_reverse = 0 if self.direction == 1 else 1
        GPIO.output(DIR_PIN, dir_reverse)

        while self._rewind_event.is_set():
            GPIO.output(STEP_PIN, GPIO.HIGH)
            time.sleep(0.00001)
            GPIO.output(STEP_PIN, GPIO.LOW)
            time.sleep(0.002)

        print("[MOTOR] Rewind stopped.")
        self.motor_power(False)

    # --- CONTROLS ---
    def start(self):
        if not self.tracking and not self.is_manual and not self.is_rewinding:
            self.tracking = True
            threading.Thread(target=self.run_tracking, daemon=True).start()

    def stop(self):
        self.tracking = False
        self._rewind_event.clear()
        self.current_rpm = 0.0

    def start_manual_mode(self):
        if not self.tracking and not self.is_manual and not self.is_rewinding:
            self.is_manual = True
            threading.Thread(target=self.run_manual, daemon=True).start()

    def stop_manual_mode(self):
        self.is_manual  = False
        self.manual_rpm = 0.0
        self.current_rpm = 0.0

    def start_rewind(self):
        if not self.tracking and not self.is_manual and not self.is_rewinding:
            self._rewind_event.set()
            threading.Thread(target=self.run_rewind, daemon=True).start()

    def reset(self):
        self.stop()
        self.stop_manual_mode()
        self.current_time_min = 0.0
        self.current_angle    = 0.0


# ==========================================
# WIDGETS
# ==========================================
class StatCard(QFrame):
    def __init__(self, label, unit=""):
        super().__init__()
        self.unit = unit
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a2744, stop:1 #111827);
                border: 1px solid #1e3a5f;
                border-radius: 14px;
            }
        """)
        self.setMinimumHeight(90)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        self.lbl = QLabel(label.upper())
        self.lbl.setStyleSheet("color:#4a7fa5; font-size:10px; font-weight:bold; letter-spacing:2px; background:transparent; border:none;")

        self.val = QLabel("0.00")
        self.val.setStyleSheet("color:#e2f0ff; font-size:22px; font-weight:bold; font-family:'Courier New'; background:transparent; border:none;")

        layout.addWidget(self.lbl)
        layout.addWidget(self.val)
        self.setLayout(layout)

    def set_value(self, v):
        self.val.setText(v)


class Divider(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.HLine)
        self.setStyleSheet("color:#1e3a5f; background:#1e3a5f; border:none; max-height:1px;")


# ==========================================
# MAIN WINDOW
# ==========================================
class TrackerGUI(QWidget):
    def __init__(self, tracker):
        super().__init__()
        self.tracker = tracker
        self._build_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self._refresh)
        self.timer.start(100)

    def _build_ui(self):
        #self.setWindowTitle("Observatory Control")
        self.setFixedSize(520, 580)
        self.setStyleSheet("""
            QWidget {
                background: #080f1e;
                color: #c9dff0;
                font-family: 'Segoe UI', sans-serif;
            }
            QGroupBox {
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 2px;
                color: #4a7fa5;
                border: 1px solid #1e3a5f;
                border-radius: 12px;
                margin-top: 14px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
            }
            QCheckBox {
                color: #8ab4cc;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #2a5075;
                background: #0f1e33;
            }
            QCheckBox::indicator:checked {
                background: #2563eb;
                border-color: #3b82f6;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #1a2f4a;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #2563eb;
                width: 18px;
                height: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: #2563eb;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal:disabled {
                background: #1a2f4a;
            }
        """)

        root = QVBoxLayout()
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # --- HEADER ---
        header = QHBoxLayout()
        title = QLabel("Observatory")
        title.setStyleSheet("font-size:22px; font-weight:bold; letter-spacing:4px; color:#e2f0ff; font-family:'Courier New';")
        sub = QLabel("OBSERVATORY CONTROL")
        sub.setStyleSheet("font-size:9px; letter-spacing:3px; color:#4a7fa5;")
        sub.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(sub)
        root.addLayout(header)

        # --- STATUS BAR ---
        self.status = QLabel("IDLE")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("""
            background: #0d1b2e;
            border: 1px solid #1e3a5f;
            border-radius: 8px;
            color: #4a7fa5;
            font-size: 12px;
            font-weight: bold;
            letter-spacing: 2px;
            padding: 7px;
        """)
        root.addWidget(self.status)

        # --- STAT CARDS ---
        grid = QGridLayout()
        grid.setSpacing(10)
        self.card_time  = StatCard("Elapsed",  "min")
        self.card_angle = StatCard("Angle",    "deg")
        self.card_rpm   = StatCard("Speed",    "rpm")
        grid.addWidget(self.card_time,  0, 0)
        grid.addWidget(self.card_angle, 0, 1)
        grid.addWidget(self.card_rpm,   1, 0, 1, 2)
        root.addLayout(grid)

        # --- MANUAL CONTROL ---
        manual_group = QGroupBox("MANUAL SLEW")
        ml = QVBoxLayout()
        ml.setSpacing(10)
        ml.setContentsMargins(14, 10, 14, 14)

        self.chk_manual = QCheckBox("Enable Manual Mode")
        self.chk_manual.stateChanged.connect(self._toggle_manual)
        ml.addWidget(self.chk_manual)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(-60)
        self.slider.setMaximum(60)
        self.slider.setValue(0)
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(self._slider_changed)
        self.slider.sliderReleased.connect(self._slider_released)

        self.lbl_rpm = QLabel("0 RPM")
        self.lbl_rpm.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_rpm.setStyleSheet("color:#4a7fa5; font-size:11px; font-family:'Courier New'; letter-spacing:1px;")

        ml.addWidget(self.slider)
        ml.addWidget(self.lbl_rpm)
        manual_group.setLayout(ml)
        root.addWidget(manual_group)

        # --- BUTTONS ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_start  = self._make_btn("START",   "#16a34a", "#15803d")
        self.btn_stop   = self._make_btn("STOP",    "#dc2626", "#b91c1c")
        self.btn_rewind = self._make_btn("REWIND",  "#d97706", "#b45309")
        self.btn_reset  = self._make_btn("RESET",   "#334155", "#1e293b")

        self.btn_start.clicked.connect(self._start)
        self.btn_stop.clicked.connect(self._stop)
        self.btn_rewind.clicked.connect(self._toggle_rewind)
        self.btn_reset.clicked.connect(self._reset)

        for b in [self.btn_start, self.btn_stop, self.btn_rewind, self.btn_reset]:
            btn_layout.addWidget(b)

        root.addLayout(btn_layout)
        self.setLayout(root)

    def _make_btn(self, text, bg, hover):
        b = QPushButton(text)
        b.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                color: white;
                font-weight: bold;
                font-size: 11px;
                letter-spacing: 1px;
                padding: 12px 6px;
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{
                background: {hover};
            }}
            QPushButton:disabled {{
                background: #1e293b;
                color: #334155;
            }}
        """)
        return b

    # ==========================================
    # UI LOGIC
    # ==========================================
    def _set_status(self, text, color):
        self.status.setText(text)
        self.status.setStyleSheet(f"""
            background: #0d1b2e;
            border: 1px solid #1e3a5f;
            border-radius: 8px;
            color: {color};
            font-size: 12px;
            font-weight: bold;
            letter-spacing: 2px;
            padding: 7px;
        """)

    def _reset_rewind_btn(self):
        self.btn_rewind.setText("REWIND")
        self.btn_rewind.setStyleSheet(self.btn_rewind.styleSheet().replace("#b45309", "#d97706").replace("#92400e", "#b45309"))
        # Rebuild cleanly
        self.btn_rewind.setStyleSheet("""
            QPushButton { background:#d97706; color:white; font-weight:bold;
                font-size:11px; letter-spacing:1px; padding:12px 6px;
                border-radius:8px; border:none; }
            QPushButton:hover { background:#b45309; }
            QPushButton:disabled { background:#1e293b; color:#334155; }
        """)

    def _toggle_rewind(self):
        print(f"[UI] Rewind clicked | is_rewinding={self.tracker.is_rewinding}")
        if self.tracker.is_rewinding:
            self.tracker.stop()
            self._reset_rewind_btn()
            self.btn_start.setEnabled(True)
            self.chk_manual.setEnabled(True)
            self._set_status("● IDLE", "#4a7fa5")
        else:
            if not self.tracker.tracking and not self.tracker.is_manual:
                self.tracker.start_rewind()
                self.btn_rewind.setText("■ STOP REWIND")
                self.btn_rewind.setStyleSheet("""
                    QPushButton { background:#92400e; color:white; font-weight:bold;
                        font-size:11px; letter-spacing:1px; padding:12px 6px;
                        border-radius:8px; border:none; }
                    QPushButton:hover { background:#78350f; }
                """)
                self.btn_start.setEnabled(False)
                self.chk_manual.setEnabled(False)
                self._set_status("« REWINDING...", "#f59e0b")

    def _start(self):
        self.tracker.start()
        self.chk_manual.setEnabled(False)
        self.btn_rewind.setEnabled(False)
        self._set_status("● TRACKING — ISOSCELES", "#22c55e")

    def _stop(self):
        self.tracker.stop()
        self._reset_rewind_btn()
        self.btn_start.setEnabled(True)
        self.btn_rewind.setEnabled(True)
        self.chk_manual.setEnabled(True)
        if self.chk_manual.isChecked():
            self._set_status("● MANUAL MODE ACTIVE", "#f59e0b")
        else:
            self._set_status("● STOPPED", "#ef4444")

    def _toggle_manual(self, state):
        if state == 2:
            self.tracker.start_manual_mode()
            self.slider.setEnabled(True)
            self.btn_start.setEnabled(False)
            self.btn_rewind.setEnabled(False)
            self._set_status("● MANUAL MODE ACTIVE", "#f59e0b")
        else:
            self.tracker.stop_manual_mode()
            self.slider.setValue(0)
            self.slider.setEnabled(False)
            self.btn_start.setEnabled(True)
            self.btn_rewind.setEnabled(True)
            self.lbl_rpm.setText("0 RPM")
            self._set_status("● IDLE", "#4a7fa5")

    def _slider_changed(self, value):
        self.lbl_rpm.setText(f"{value:+d} RPM")
        self.tracker.manual_rpm = float(value)

    def _slider_released(self):
        self.slider.setValue(0)

    def _reset(self):
        self.tracker.reset()
        self._reset_rewind_btn()
        self.chk_manual.setChecked(False)
        self.chk_manual.setEnabled(True)
        self.btn_start.setEnabled(True)
        self.btn_rewind.setEnabled(True)
        self._set_status("● RESET", "#64748b")

    def _refresh(self):
        if self.tracker.tracking or self.tracker.is_manual:
            self.card_time.set_value(f"{self.tracker.current_time_min:.2f}")
            self.card_angle.set_value(f"{self.tracker.current_angle:.4f}")
            self.card_rpm.set_value(f"{self.tracker.current_rpm:.5f}")
        elif self.tracker.is_rewinding:
            self.card_rpm.set_value("REWIND")
        else:
            self.card_time.set_value("0.00")
            self.card_angle.set_value("0.0000")
            self.card_rpm.set_value("0.00000")


# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    tracker = AstroTracker()
    window = TrackerGUI(tracker)
    window.show()

    try:
        sys.exit(app.exec())
    finally:
        print("\n[SYSTEM] Shutting down — cleaning up GPIO...")
        tracker.stop()
        tracker.stop_manual_mode()
        GPIO.output(ENABLE_PIN, GPIO.HIGH)
        GPIO.output(STEP_PIN,   GPIO.LOW)
        GPIO.output(DIR_PIN,    GPIO.LOW)
