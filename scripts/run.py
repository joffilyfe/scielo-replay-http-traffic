import os
import time


for connections in [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75]:
    print("=" * 80)
    print(f"Iniciando o teste com a quantidade {connections} de conexões")
    os.system(
        f"python main.py logs/1000-urls-para-testes.log https://new.scielo.br --connections {connections} --dont-wait-until-request-time --output-file resultados-dos-testes-de-stress/{connections}-conexoes.csv"
    )
    print("Dormindo 60 segundos para então iniciar uma nova bateria de testes")
    time.sleep(60)
    print("=" * 80)
