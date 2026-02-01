import RPi.GPIO as GPIO
import time
import sys
import threading

# ==========================================
#      CONFIGURAÇÕES DO USUÁRIO (Edite aqui)
# ==========================================

# Hardware
DIR_PIN = 21
STEP_PIN = 20
ENABLE_PIN = 16

# Mecânica (Ajuste conforme suas peças chegarem)
PASSOS_MOTOR = 200      # Nema 17 padrão
MICROSTEPS = 16         # Driver A4988 (todos jumpers ligados)
REDUCAO_MECANICA = 1.0  # 1.0 = Direto (Teste). Mude para 100.0, 256.0 depois.

# Astronomia
DIA_SIDERAL_SEC = 86164.09  # Duração exata de uma rotação da Terra

# ==========================================
#      CÉREBRO DO SISTEMA (Não mexa)
# ==========================================

class AstroTracker:
    def __init__(self):
        # Setup dos Pinos
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(DIR_PIN, GPIO.OUT)
        GPIO.setup(STEP_PIN, GPIO.OUT)
        GPIO.setup(ENABLE_PIN, GPIO.OUT)
        
        # Estado Inicial
        self.tracking = False
        self.direction = 1 # 1 = Horário, 0 = Anti-horário
        
        # Cálculos Físicos
        self.total_steps_per_rev = PASSOS_MOTOR * MICROSTEPS * REDUCAO_MECANICA
        self.delay_sidereal = DIA_SIDERAL_SEC / self.total_steps_per_rev
        
        # Desliga motor ao iniciar (Segurança)
        self.motor_power(False)

    def motor_power(self, state):
        """Liga ou Desliga a corrente do motor"""
        if state:
            GPIO.output(ENABLE_PIN, GPIO.LOW) # LOW = Ligado
            time.sleep(0.1) # Tempo para energizar bobinas
        else:
            GPIO.output(ENABLE_PIN, GPIO.HIGH) # HIGH = Desligado

    def run_tracking(self):
        """Loop principal de rastreamento (Roda em Thread separada)"""
        print(f"[INFO] Rastreamento Iniciado.")
        print(f"[MATH] Delay calculado: {self.delay_sidereal:.5f}s por passo")
        
        self.motor_power(True)
        GPIO.output(DIR_PIN, self.direction)
        
        while self.tracking:
            # Passo Físico
            GPIO.output(STEP_PIN, GPIO.HIGH)
            time.sleep(0.00001) # Pulso ultra-rápido (10us)
            GPIO.output(STEP_PIN, GPIO.LOW)
            
            # Compensação de Tempo (Drift Compensation)
            start_time = time.perf_counter()
            while (time.perf_counter() - start_time) < self.delay_sidereal:
                if not self.tracking: break
                time.sleep(0.001) # Dorme em fatias pequenas para resposta rápida

        self.motor_power(False)
        print("[INFO] Rastreamento Parado.")

    def rewind(self):
        """Rebobina o tracker para posição inicial (Rápido)"""
        print("[ACAO] Rebobinando...")
        self.motor_power(True)
        
        # Inverte direção
        GPIO.output(DIR_PIN, not self.direction)
        
        # Aceleração Suave (Rampa)
        velocidade = 0.005 # Começa lento
        try:
            for _ in range(2000): # Número de passos para voltar (Ajuste depois)
                GPIO.output(STEP_PIN, GPIO.HIGH)
                time.sleep(0.00001)
                GPIO.output(STEP_PIN, GPIO.LOW)
                time.sleep(velocidade)
                
                # Acelera até o limite
                if velocidade > 0.0005:
                    velocidade -= 0.0001
                    
        except KeyboardInterrupt:
            pass
            
        self.motor_power(False)
        print("[INFO] Rebobinagem concluída.")

    def start(self):
        if not self.tracking:
            self.tracking = True
            # Cria um processo paralelo para o motor não travar o menu
            self.thread = threading.Thread(target=self.run_tracking)
            self.thread.start()

    def stop(self):
        self.tracking = False
        if hasattr(self, 'thread'):
            self.thread.join()

    def cleanup(self):
        self.stop()
        GPIO.cleanup()
        print("\nSistema Desligado.")

# ==========================================
#      INTERFACE (Menu Principal)
# ==========================================

def main():
    tracker = AstroTracker()
    
    print("\n" * 50) # Limpa tela
    print("=======================================")
    print("   ASTROPI TRACKER v1.0 - CONTROL")
    print("=======================================")
    print(f" Redução Mecânica: {REDUCAO_MECANICA}x")
    print("=======================================")
    print(" [1] INICIAR Rastreamento (Sideral)")
    print(" [2] PARAR Rastreamento")
    print(" [3] REBOBINAR (Rewind)")
    print(" [9] SAIR")
    print("=======================================")

    try:
        while True:
            cmd = input("Comando >> ")
            
            if cmd == '1':
                tracker.start()
            elif cmd == '2':
                tracker.stop()
            elif cmd == '3':
                if tracker.tracking:
                    print("[ERRO] Pare o rastreamento antes de rebobinar!")
                else:
                    tracker.rewind()
            elif cmd == '9':
                break
            else:
                print("Opção inválida.")
                
    except KeyboardInterrupt:
        pass
    finally:
        tracker.cleanup()

if __name__ == "__main__":
    main()