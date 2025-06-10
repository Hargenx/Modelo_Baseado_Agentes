import json
import os
import numpy as np
import matplotlib.pyplot as plt
from src.simulation_runner import run_single_simulation

if __name__ == "__main__":
    with open("config/parametros.json", "r", encoding="utf-8") as f:
        sim_params = json.load(f)

    run_id = "simulacao_completa"
    os.makedirs("results/plots", exist_ok=True)

    # Executar a simulação e receber o dicionário completo de resultados
    resultados = run_single_simulation(sim_params, run_id)

    # --- EXIBIÇÃO FINAL (Lógica movida para cá) ---
    print("\n--- Resultados Finais ---")

    # Extrair os dados do dicionário de resultados
    fii = resultados["objeto_fii_final"]
    agentes = resultados["lista_agentes_final"]
    historico_precos_fii = resultados["historico_precos_fii"]
    volatilidade_rolante = resultados["volatilidade_rolante"]
    num_dias = sim_params["geral"]["num_dias"]

    # Imprimir o resumo
    print(f"Preço Final da Cota: R${fii.preco_cota:,.2f}")
    print(f"Caixa Final do FII: R${fii.caixa:,.2f}")
    for agente in agentes:
        riqueza_final = agente.caixa + agente.carteira.get("FII", 0) * fii.preco_cota
        print(
            f"Agente {agente.id}: Caixa: R${agente.caixa:,.2f}, Sentimento: {agente.sentimento:.2f}, Riqueza: R${riqueza_final:,.2f}"
        )

    # Gerar e mostrar os gráficos
    print("\nGerando gráficos...")
    dias_array = np.arange(num_dias)
    fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    ax[0].plot(dias_array, historico_precos_fii, label="Preço da Cota do FII")
    ax[0].set_title("Evolução do Preço do FII")
    ax[0].set_ylabel("Preço")
    ax[0].legend()
    ax[0].grid(True)

    # Ajuste para plotar a volatilidade corretamente
    dias_vol = np.arange(len(volatilidade_rolante)) + (
        num_dias - len(volatilidade_rolante)
    )
    ax[1].plot(
        dias_vol,
        volatilidade_rolante,
        label=f"Volatilidade Rolante ({sim_params['plot']['window_volatilidade']} dias)",
        color="orange",
    )
    ax[1].set_title("Volatilidade Rolante dos Retornos Logarítmicos")
    ax[1].set_ylabel("Volatilidade")
    ax[1].set_xlabel("Dias")
    ax[1].legend()
    ax[1].grid(True)

    plt.tight_layout()

    # Salvar e mostrar o gráfico
    plot_path = f"results/plots/{run_id}_final_plot.png"
    plt.savefig(plot_path)
    print(f"Gráfico salvo em: {plot_path}")
    plt.show()  # Mostra o gráfico na tela ao executar o script
