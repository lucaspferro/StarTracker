import sys
import time
# O ponto (.) significa "desta mesma pasta, importe o arquivo motor"
from .motor import AstroTracker

def main():
    # Instancia a classe que controla o hardware
    tracker = AstroTracker()
    
    # Limpa a tela (visual)
    print("\n" * 50) 
    
    print("=======================================")
    print("   ASTROPI TRACKER - CONTROLE")
    print("=======================================")
    # Acessa a variável REDUCAO_MECANICA lá da classe para mostrar na tela
    print(f" Redução Configurada: {tracker.total_steps_per_rev / (200*16)}x")
    print("=======================================")
    print(" [1] INICIAR Rastreamento (Sideral)")
    print(" [2] PARAR Rastreamento")
    print(" [3] REBOBINAR (Rewind)")
    print(" [4] Check engine")
    print(" [9] SAIR DO SISTEMA")
    print("=======================================")

    try:
        while True:
            # Pega o comando do usuário
            cmd = input("\nComando >> ")
            
            if cmd == '1':
                tracker.start()
            
            elif cmd == '2':
                tracker.stop()
            
            elif cmd == '3':
                if tracker.tracking:
                    print(" [ERRO] Pare o rastreamento antes de rebobinar!")
                else:
                    tracker.rewind()
            elif cmd == '4':
                tracker.check_engine()
            elif cmd == '9':
                print("Saindo...")
                break
            
            else:
                print("Opção inválida. Tente 1, 2, 3 ou 9.")
                
    except KeyboardInterrupt:
        # Se o usuário apertar CTRL+C, ele cai aqui
        print("\nInterrupção forçada detectada.")
    
    finally:
        # Isso SEMPRE roda ao fechar, garantindo que o motor desligue
        tracker.cleanup()

# Isso permite rodar o arquivo diretamente se necessário
if __name__ == "__main__":
    main()