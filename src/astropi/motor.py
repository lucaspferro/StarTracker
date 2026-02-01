import RPi.GPIO as GPIO
import time
import sys
import threading

# ==========================================
#      USER CONFIGURATION (Edit here)
# ==========================================

# Hardware
DIR_PIN = 21
STEP_PIN = 20
ENABLE_PIN = 16

# Mechanics (Adjust as your parts arrive)
PASSOS_MOTOR = 200      # Nema 17 standard
MICROSTEPS = 16         # A4988 Driver (all jumpers set)
REDUCAO_MECANICA = 1.0  # 1.0 = Direct Drive (Test). Change to 100.0, 256.0 later.

# Astronomy
DIA_SIDERAL_SEC = 86164.09  # Exact duration of one Earth rotation

# ==========================================
#      SYSTEM BRAIN (Do not edit)
# ==========================================

class AstroTracker:
    def __init__(self):
        # Pin Setup
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(DIR_PIN, GPIO.OUT)
        GPIO.setup(STEP_PIN, GPIO.OUT)
        GPIO.setup(ENABLE_PIN, GPIO.OUT)
        
        # Initial State
        self.tracking = False
        self.direction = 1 # 1 = Clockwise, 0 = Counter-Clockwise
        
        # Physics Calculations
        self.total_steps_per_rev = PASSOS_MOTOR * MICROSTEPS * REDUCAO_MECANICA
        self.delay_sidereal = DIA_SIDERAL_SEC / self.total_steps_per_rev
        
        # Disable motor on start (Safety)
        self.motor_power(False)

    def motor_power(self, state):
        """Turns motor current ON or OFF"""
        if state:
            GPIO.output(ENABLE_PIN, GPIO.LOW) # LOW = ON
            time.sleep(0.1) # Time to energize coils
        else:
            GPIO.output(ENABLE_PIN, GPIO.HIGH) # HIGH = OFF

    def run_tracking(self):
        """Main tracking loop (Runs in separate Thread)"""
        print(f"[INFO] Tracking Started.")
        print(f"[MATH] Calculated delay: {self.delay_sidereal:.5f}s per step")
        
        self.motor_power(True)
        GPIO.output(DIR_PIN, self.direction)
        
        while self.tracking:
            # Physical Step
            GPIO.output(STEP_PIN, GPIO.HIGH)
            time.sleep(0.00001) # Ultra-fast pulse (10us)
            GPIO.output(STEP_PIN, GPIO.LOW)
            
            # Drift Compensation
            start_time = time.perf_counter()
            while (time.perf_counter() - start_time) < self.delay_sidereal:
                if not self.tracking: break
                time.sleep(0.001) # Sleep in small chunks for fast response

        self.motor_power(False)
        print("[INFO] Tracking Stopped.")

    def rewind(self):
        """Rewinds the tracker to initial position (Fast)"""
        print("[ACTION] Rewinding...")
        self.motor_power(True)
        
        # Invert direction
        GPIO.output(DIR_PIN, not self.direction)
        
        # Smooth Acceleration (Ramp)
        speed = 0.005 # Start slow
        try:
            for _ in range(2000): # Number of steps to rewind (Adjust later)
                GPIO.output(STEP_PIN, GPIO.HIGH)
                time.sleep(0.00001)
                GPIO.output(STEP_PIN, GPIO.LOW)
                time.sleep(speed)
                
                # Accelerate to limit
                if speed > 0.0005:
                    speed -= 0.0001
                    
        except KeyboardInterrupt:
            pass
            
        self.motor_power(False)
        print("[INFO] Rewind complete.")

    def start(self):
        if not self.tracking:
            self.tracking = True
            # Creates a parallel process so motor doesn't freeze the menu
            self.thread = threading.Thread(target=self.run_tracking)
            self.thread.start()

    def stop(self):
        self.tracking = False
        if hasattr(self, 'thread'):
            self.thread.join()

    def cleanup(self):
        self.stop()
        GPIO.cleanup()
        print("\nSystem Shutdown.")

# ==========================================
#      INTERFACE (Main Menu)
# ==========================================

def main():
    tracker = AstroTracker()
    
    print("\n" * 50) # Clear screen
    print("=======================================")
    print("   ASTROPI TRACKER v1.0 - CONTROL")
    print("=======================================")
    print(f" Mechanical Reduction: {REDUCAO_MECANICA}x")
    print("=======================================")
    print(" [1] START Tracking ")
    print(" [2] STOP Tracking")
    print(" [3] REWIND")
    print(" [9] EXIT")
    print("=======================================")

    try:
        while True:
            cmd = input("Command >> ")
            
            if cmd == '1':
                tracker.start()
            elif cmd == '2':
                tracker.stop()
            elif cmd == '3':
                if tracker.tracking:
                    print("[ERROR] Stop tracking before rewinding!")
                else:
                    tracker.rewind()
            elif cmd == '9':
                break
            else:
                print("Invalid option.")
                
    except KeyboardInterrupt:
        pass
    finally:
        tracker.cleanup()

if __name__ == "__main__":
    main()