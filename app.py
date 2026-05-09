import time
import math
import json
import asyncio
import threading

# --- GPIO: troca por mock se nao estiver no Pi ---
try:
	import RPi.GPIO as GPIO
	ON_PI = True
except ImportError:
	ON_PI = False
	print("[WARN] RPi.GPIO nao encontrado — rodando em modo simulado")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# ==========================================
# CONFIG
# ==========================================
DIR_PIN    = 21
STEP_PIN   = 20
ENABLE_PIN = 16

MOTOR_STEPS       = 200
MICROSTEPS        = 16
PASSOS_TOTAIS_REV = MOTOR_STEPS * MICROSTEPS

R_MM       = 300.0
P_MM       = 0.7
OM_RAD_MIN = 0.0043633

# ==========================================
# GPIO MOCK (para desenvolvimento fora do Pi)
# ==========================================
if not ON_PI:
	class _GPIO:
		BCM = OUT = HIGH = LOW = 0
		def setmode(self, *a): pass
		def setwarnings(self, *a): pass
		def setup(self, *a): pass
		def output(self, *a): pass
		def cleanup(self): pass
	GPIO = _GPIO()

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

		self.initial_angle_deg = 10.0
		self.current_time_min  = 0.0
		self.current_rpm       = 0.0
		self.current_angle     = 0.0

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

		initial_deg = self.initial_angle_deg
		initial_rad = math.radians(initial_deg)

		while self.tracking:
			self.current_time_min = (time.perf_counter() - self.start_time) / 60.0

			w   = initial_rad / 2.0 + (OM_RAD_MIN * self.current_time_min) / 2.0
			vel = R_MM * OM_RAD_MIN * math.cos(w)

			self.current_rpm   = vel / P_MM
			self.current_angle = initial_deg + math.degrees(OM_RAD_MIN * self.current_time_min)

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
			time.sleep(0.0005)

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
		self.is_manual   = False
		self.manual_rpm  = 0.0
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

	def telemetry(self):
		return {
			"time":      round(self.current_time_min, 2),
			"angle":     round(self.current_angle, 4),
			"rpm":       round(self.current_rpm, 5),
			"tracking":  self.tracking,
			"manual":    self.is_manual,
			"rewinding": self.is_rewinding,
		}

	def cleanup(self):
		self.stop()
		self.stop_manual_mode()
		GPIO.output(ENABLE_PIN, GPIO.HIGH)
		GPIO.output(STEP_PIN,   GPIO.LOW)
		GPIO.output(DIR_PIN,    GPIO.LOW)
		GPIO.cleanup()


# ==========================================
# WEBSOCKET MANAGER
# ==========================================
class ConnectionManager:
	"""Gerencia todas as conexoes WebSocket abertas."""

	def __init__(self):
		self.active: list[WebSocket] = []

	async def connect(self, ws: WebSocket):
		await ws.accept()
		self.active.append(ws)
		print(f"[WS] Client connected — total: {len(self.active)}")

	def disconnect(self, ws: WebSocket):
		self.active.remove(ws)
		print(f"[WS] Client disconnected — total: {len(self.active)}")

	async def broadcast(self, data: dict):
		payload = json.dumps(data)
		dead = []
		for ws in self.active:
			try:
				await ws.send_text(payload)
			except Exception:
				dead.append(ws)
		for ws in dead:
			self.active.remove(ws)


# ==========================================
# APP
# ==========================================
tracker = AstroTracker()
manager = ConnectionManager()
app     = FastAPI(title="AstroZeca Observatory Control")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
	return FileResponse("static/index.html")


# --- TELEMETRY LOOP ---
@app.on_event("startup")
async def start_telemetry():
	async def loop():
		while True:
			if manager.active:
				await manager.broadcast(tracker.telemetry())
			await asyncio.sleep(0.1)

	asyncio.create_task(loop())


@app.on_event("shutdown")
async def shutdown():
	tracker.cleanup()


# ==========================================
# WEBSOCKET ENDPOINT
# ==========================================
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
	await manager.connect(ws)
	try:
		while True:
			raw  = await ws.receive_text()
			data = json.loads(raw)
			cmd  = data.get("cmd")

			if cmd == "start":
				tracker.initial_angle_deg = float(data.get("initial_angle", 10.0))
				tracker.start()

			elif cmd == "stop":
				tracker.stop()

			elif cmd == "rewind":
				if tracker.is_rewinding:
					tracker.stop()
				else:
					tracker.start_rewind()

			elif cmd == "reset":
				tracker.reset()

			elif cmd == "manual_start":
				tracker.start_manual_mode()

			elif cmd == "manual_stop":
				tracker.stop_manual_mode()

			elif cmd == "manual_rpm":
				tracker.manual_rpm = float(data.get("rpm", 0.0))

			else:
				print(f"[WS] Unknown command: {cmd}")

	except WebSocketDisconnect:
		manager.disconnect(ws)


# ==========================================
# ENTRY POINT
# ==========================================
if __name__ == "__main__":
	import uvicorn
	uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)