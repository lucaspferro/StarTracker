import RPi.GPIO as GPIO
import time
import threading
import logging

# ==========================================
#      HARDWARE CONFIGURATION
# ==========================================

# GPIO Pins (BCM)
DIR_PIN = 21
STEP_PIN = 20
ENABLE_PIN = 16

# Physics Constants
SIDEREAL_DAY_SEC = 86164.09  # Duration of one Earth rotation (23h 56m 4s)

# ==========================================
#      MECHANICAL CONFIGURATION
#      (Adjust these values carefully)
# ==========================================

MOTOR_STEPS = 200       # Nema 17 Standard (1.8 deg/step)
MICROSTEPS = 16         # Driver Setting (1/16)
GEAR_RATIO = 1.0        # 1.0 = Direct Drive. Change to 100.0, etc.

# ==========================================
#      LOGIC CLASS
# ==========================================

class AstroTracker:
    def __init__(self):
        """Initializes GPIO and calculates physics."""
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(DIR_PIN, GPIO.OUT)
        GPIO.setup(STEP_PIN, GPIO.OUT)
        GPIO.setup(ENABLE_PIN, GPIO.OUT)
        
        # State Variables
        self.tracking = False
        self.direction = 1  # 1 = Clockwise, 0 = Counter-Clockwise
        
        # Physics Calculation
        # Formula: (Steps * Microsteps * GearRatio)
        self.total_steps_per_rev = MOTOR_STEPS * MICROSTEPS * GEAR_RATIO
        
        # Calculate time between pulses for Sidereal rate
        self.delay_sidereal = SIDEREAL_DAY_SEC / self.total_steps_per_rev
        
        # Ensure motor is disabled (loose) on start to save power
        self.motor_power(False)

    def motor_power(self, state):
        """
        Controls the Driver's ENABLE pin.
        True  = Motor ON (Holding Torque, Current flowing)
        False = Motor OFF (Free spinning, No current)
        """
        if state:
            GPIO.output(ENABLE_PIN, GPIO.LOW)  # LOW enables the driver
            time.sleep(0.1) # Stabilization time
        else:
            GPIO.output(ENABLE_PIN, GPIO.HIGH) # HIGH disables the driver

    def run_tracking(self):
        """
        The main loop. Runs in a separate thread.
        Uses drift compensation for high precision.
        """
        logging.info("Starting tracking logic.")
        logging.info(f"Calculated Pulse Interval: {self.delay_sidereal:.6f} seconds")
        
        
        self.motor_power(True)
        GPIO.output(DIR_PIN, self.direction)
        
        while self.tracking:
            # 1. Send Pulse
            GPIO.output(STEP_PIN, GPIO.HIGH)
            time.sleep(0.00001) # Short pulse (10 microseconds)
            GPIO.output(STEP_PIN, GPIO.LOW)
            
            # 2. Precision Wait (Drift Compensation)
            # Instead of a simple sleep, we measure elapsed time.
            start_time = time.perf_counter()
            
            print(".", end="", flush=True)
            while (time.perf_counter() - start_time) < self.delay_sidereal:
                # Break early if user stopped tracking
                if not self.tracking: 
                    break
                # Sleep in tiny chunks to keep CPU usage low but response high
                time.sleep(0.001) 

        # Loop finished
        self.motor_power(False)
        
        logging.info("Tracking logic ended.")
    def rewind(self):
        """
        Rewinds the mount quickly to the start position.
        Uses a ramp (acceleration) to prevent stalling.
        """
        
        logging.info("Rewinding Sequence Initiated.")
        self.motor_power(True)
        
        # Invert Direction temporarily
        GPIO.output(DIR_PIN, not self.direction)
        
        # Acceleration Logic
        current_delay = 0.005 # Start slow
        min_delay = 0.0004    # Max speed limit
        
        try:
            # TODO: In the future, we can count steps to rewind exactly.
            # For now, we rewind a fixed amount (approx 90 degrees direct drive)
            steps_to_rewind = int(self.total_steps_per_rev / 4) 
            
            for _ in range(steps_to_rewind):
                GPIO.output(STEP_PIN, GPIO.HIGH)
                time.sleep(0.00001)
                GPIO.output(STEP_PIN, GPIO.LOW)
                
                time.sleep(current_delay)
                
                # Accelerate (Decrease delay)
                if current_delay > min_delay:
                    current_delay -= 0.00005
                    
        except KeyboardInterrupt:
            print("[WARN] Rewind interrupted by user.")
            
        self.motor_power(False)
        print("[INFO] Rewind Complete.")

    def start(self):
        """Starts the tracking thread."""
        if not self.tracking:
            self.tracking = True
            # Daemon=True means this thread dies if the main program dies
            self.thread = threading.Thread(target=self.run_tracking, daemon=True)
            self.thread.start()

    def stop(self):
        """Signals the tracking thread to stop."""
        self.tracking = False
        if hasattr(self, 'thread'):
            self.thread.join() # Wait for thread to finish cleanly
    def check_engine(self):
        """Performs a basic check of the motor system."""
        print("[CHECK] Performing system diagnostics...")
        self.motor_power(True)
        GPIO.output(DIR_PIN, self.direction)
        
        # Test a few steps
        for _ in range(10):
            GPIO.output(STEP_PIN, GPIO.HIGH)
            time.sleep(0.00001)
            GPIO.output(STEP_PIN, GPIO.LOW)
            time.sleep(0.1)  # Slow enough to observe
        
        self.motor_power(False)
        print("[CHECK] Diagnostics complete. Motor responded correctly.")

    def cleanup(self):
        """Releases GPIO resources."""
        self.stop()
        self.motor_power(False)
        print("[SYSTEM] GPIO Cleaned up. Exiting.")