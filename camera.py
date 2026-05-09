import os
import time
import subprocess
import threading

class CameraControl:
    def __init__(self):
        self.running = False
        self.camera_detected = False
        
    def detect_camera(self):
        """Verifica se a câmera está conectada e configura para salvar no Cartão SD."""
        
        # --- NOVO: ANTISSEQUESTRO ---
        # Mata os processos do Linux que tentam usar a câmera como Pen Drive
        print("[CAM] Liberando a porta USB do sistema...")
        try:
            subprocess.run(['pkill', '-f', 'gvfs-gphoto2-volume-monitor'], stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'gvfsd-gphoto2'], stderr=subprocess.DEVNULL)
            time.sleep(1) # Dá 1 segundo para o sistema liberar a porta
        except:
            pass
        # ----------------------------

        try:
            # 1. Detecta a câmera
            result = subprocess.check_output(['gphoto2', '--auto-detect'])
            output = result.decode('utf-8')
            
            if "Canon" in output or "Nikon" in output or "Sony" in output:
                self.camera_detected = True
                
                # 2. FORÇA salvar no Cartão de Memória (Capture Target = 1)
                try:
                    subprocess.run(
                        ['gphoto2', '--set-config', 'capturetarget=1'], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL
                    )
                    print("[CAM] Configurado para salvar no CARTÃO SD.")
                except:
                    print("[CAM] Aviso: Não foi possível definir local de salvamento.")
                
                return True
            return False
        except:
            return False
    def capture_image(self):
        """Disparo simples (salva no cartão)."""
        if not self.camera_detected and not self.detect_camera():
            print("[ERRO] Câmera desconectada.")
            return

        print(f"[CAM] Disparando foto única...")
        # --capture-image: Tira a foto e mantém no cartão (Sem download)
        subprocess.run(['gphoto2', '--capture-image'])
        print("[CAM] Foto salva no cartão.")

    def run_intervalometer(self, count, duration):
        """
        Intervalômetro com Lógica Dupla:
        - Tempos curtos: Deixa a câmera fazer.
        - Tempos longos (BULB): Usa o comando nativo bulb=1 da Canon.
        """
        self.running = True
        print(f"\n[CAM] INICIANDO SESSÃO: {count} fotos de {duration}s")
        
        for i in range(1, count + 1):
            if not self.running: 
                print("[CAM] Sessão interrompida pelo usuário.")
                break
                
            print(f"----------------------------------------")
            print(f"[CAM] Foto {i}/{count} - Expondo por {duration}s...")
            
            start_time = time.time()
            
            try:
                if duration < 30:
                    # LÓGICA 1: TEMPOS CURTOS (< 30s)
                    # A câmera deve estar configurada manualmente para 1", 5", 10", etc.
                    subprocess.run(['gphoto2', '--capture-image'], check=True)
                    
                    while (time.time() - start_time) < duration:
                        if not self.running: return
                        time.sleep(0.5)
                        
                else:
                    # LÓGICA 2: MODO BULB NATIVO CANON (>= 30s)
                    # O dial físico da T5 OBRIGATORIAMENTE no M, rodinha no BULB
                    
                    # 1. Abre o obturador
                    subprocess.run(['gphoto2', '--set-config', 'bulb=1'], check=True)
                    
                    # 2. Espera o tempo exato
                    while (time.time() - start_time) < duration:
                        if not self.running:
                            subprocess.run(['gphoto2', '--set-config', 'bulb=0']) # Fecha se cancelar
                            return
                        time.sleep(0.5)
                        
                    # 3. Fecha o obturador
                    subprocess.run(['gphoto2', '--set-config', 'bulb=0'], check=True)
                
            except subprocess.CalledProcessError:
                print("[ERRO] Falha no disparo. Resetando status do obturador...")
                # Tenta forçar o fechamento do obturador caso dê erro
                subprocess.run(['gphoto2', '--set-config', 'bulb=0'], stderr=subprocess.DEVNULL)
            
            wait_time = 3 
            print(f"[CAM] Gravando no cartão (aguarde {wait_time}s)...")
            time.sleep(wait_time)
            
        self.running = False
        print("----------------------------------------")
        print("[CAM] Sessão Finalizada com Sucesso!")
    def stop(self):
        self.running = False
