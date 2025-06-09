import json
import os

from src.simulation_runner import run_single_simulation

if __name__ == "__main__":
    # Carregar parâmetros do arquivo JSON
    with open("config/parametros.json", "r", encoding="utf-8") as f:
        sim_params = json.load(f)

    # Definir um ID para esta execução
    run_id = "simulacao_base"

    # Criar diretórios de resultados, se não existirem
    if not os.path.exists("results"):
        os.makedirs("results")

    # Executar a simulação
    resultados = run_single_simulation(sim_params, run_id)

    # Exibir os resultados retornados
    print("\n--- Resultados Resumidos ---")
    for chave, valor in resultados.items():
        if isinstance(valor, float):
            print(f"{chave}: {valor:,.2f}")
        else:
            print(f"{chave}: {valor}")
    print(f"Gráfico salvo em: {resultados['plot_path']}")

    # ====================================================================
    # NOTA: Para rodar múltiplos cenários a partir de uma planilha,
    # você substituiria o código acima por um loop que lê cada linha
    # da planilha (usando pandas), ajusta o dicionário sim_params
    # para cada linha, define um run_id único e chama run_single_simulation.
    # Os resultados seriam então escritos de volta na planilha.
    # ====================================================================
