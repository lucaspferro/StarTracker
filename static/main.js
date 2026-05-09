// ==========================================
// WEBSOCKET
// ==========================================
const WS_URL = `ws://localhost:8000/ws`;
let   ws     = null;

const connDot   = document.getElementById("conn-dot");
const connLabel = document.getElementById("conn-label");

function connect() {
	ws = new WebSocket(WS_URL);

	ws.onopen = () => {
		connDot.className     = "badge-dot connected";
		connLabel.textContent = "CONNECTED";
		console.log("[WS] Connected");
	};

	ws.onclose = () => {
		connDot.className     = "badge-dot disconnected";
		connLabel.textContent = "DISCONNECTED";
		console.log("[WS] Disconnected — retrying in 2s...");
		setTimeout(connect, 2000);
	};

	ws.onerror = (e) => console.error("[WS] Error:", e);

	ws.onmessage = (event) => {
		const data = JSON.parse(event.data);
		updateTelemetry(data);
	};
}

function send(payload) {
	if (ws && ws.readyState === WebSocket.OPEN) {
		ws.send(JSON.stringify(payload));
	}
}

// ==========================================
// TELEMETRY
// ==========================================
const valTime  = document.getElementById("val-time");
const valAngle = document.getElementById("val-angle");
const valRpm   = document.getElementById("val-rpm");

function updateTelemetry(data) {
	if (data.tracking || data.manual) {
		valTime.textContent  = data.time.toFixed(2);
		valAngle.textContent = data.angle.toFixed(4);
		valRpm.textContent   = data.rpm.toFixed(5);
		valRpm.style.color   = "#22c55e";
	} else if (data.rewinding) {
		valRpm.textContent = "REWIND";
		valRpm.style.color = "#f59e0b";
	} else {
		valTime.textContent  = "0.00";
		valAngle.textContent = "0.0000";
		valRpm.textContent   = "0.00000";
		valRpm.style.color   = "#e2f0ff";
	}
}

// ==========================================
// UI ELEMENTS
// ==========================================
const status     = document.getElementById("status");
const angleInput = document.getElementById("initial-angle");
const chkManual  = document.getElementById("chk-manual");
const slider     = document.getElementById("slider");
const sliderVal  = document.getElementById("slider-val");
const btnStart   = document.getElementById("btn-start");
const btnStop    = document.getElementById("btn-stop");
const btnRewind  = document.getElementById("btn-rewind");
const btnReset   = document.getElementById("btn-reset");

// ==========================================
// HELPERS
// ==========================================
function setStatus(text, color) {
	status.textContent = text;
	status.style.color = color;
}

function resetRewindBtn() {
	btnRewind.textContent = "REWIND";
	btnRewind.classList.remove("active");
}

// ==========================================
// BUTTONS
// ==========================================
btnStart.addEventListener("click", () => {
	send({ cmd: "start", initial_angle: parseFloat(angleInput.value) || 10.0 });
	angleInput.disabled = true;
	chkManual.disabled  = true;
	btnRewind.disabled  = true;
	setStatus("TRACKING — ISOSCELES", "#22c55e");
});

btnStop.addEventListener("click", () => {
	send({ cmd: "stop" });
	angleInput.disabled = false;
	btnStart.disabled   = false;
	btnRewind.disabled  = false;
	chkManual.disabled  = false;
	resetRewindBtn();
	setStatus(
		chkManual.checked ? "MANUAL MODE ACTIVE" : "STOPPED",
		chkManual.checked ? "#f59e0b" : "#ef4444"
	);
});

btnRewind.addEventListener("click", () => {
	send({ cmd: "rewind" });

	if (btnRewind.classList.contains("active")) {
		resetRewindBtn();
		btnStart.disabled  = false;
		chkManual.disabled = false;
		setStatus("IDLE", "#4a7fa5");
	} else {
		btnRewind.textContent = "STOP REWIND";
		btnRewind.classList.add("active");
		btnStart.disabled  = true;
		chkManual.disabled = true;
		setStatus("REWINDING...", "#f59e0b");
	}
});

btnReset.addEventListener("click", () => {
	send({ cmd: "reset" });
	chkManual.checked     = false;
	chkManual.disabled    = false;
	slider.value          = 0;
	slider.disabled       = true;
	sliderVal.textContent = "0 RPM";
	angleInput.disabled   = false;
	angleInput.value      = "10.0";
	btnStart.disabled     = false;
	btnRewind.disabled    = false;
	resetRewindBtn();
	setStatus("RESET", "#64748b");
});

// ==========================================
// MANUAL SLEW
// ==========================================
chkManual.addEventListener("change", () => {
	if (chkManual.checked) {
		send({ cmd: "manual_start" });
		slider.disabled    = false;
		btnStart.disabled  = true;
		btnRewind.disabled = true;
		setStatus("MANUAL MODE ACTIVE", "#f59e0b");
	} else {
		send({ cmd: "manual_stop" });
		slider.value          = 0;
		slider.disabled       = true;
		sliderVal.textContent = "0 RPM";
		btnStart.disabled     = false;
		btnRewind.disabled    = false;
		setStatus("IDLE", "#4a7fa5");
	}
});

slider.addEventListener("input", () => {
	const val = parseInt(slider.value);
	sliderVal.textContent = (val >= 0 ? "+" : "") + val + " RPM";
	send({ cmd: "manual_rpm", rpm: val });
});

// efeito mola: solta o slider e volta para 0
slider.addEventListener("change", () => {
	slider.value          = 0;
	sliderVal.textContent = "0 RPM";
	send({ cmd: "manual_rpm", rpm: 0 });
});

// ==========================================
// START
// ==========================================
connect();