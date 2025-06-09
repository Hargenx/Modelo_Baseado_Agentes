import numpy as np
import matplotlib.pyplot as plt
import random
import os

from .financial_instruments import FII, Imovel
from .economic_agents import Agente
from .market_environment import Mercado, BancoCentral, Midia
from . import utils


def run_single_simulation(sim_params: dict, run_id: str):
    print(f"--- Iniciando Simulação: {run_id} ---")

    seed = sim_params["geral"].get("random_seed", 42)
    random.seed(seed)
    np.random.seed(seed)

    # Inicialização do FII e Imóveis
    fii = FII(
        num_cotas=sim_params["fii"]["num_cotas"],
        caixa=sim_params["fii"]["caixa_inicial"],
        params=sim_params["fii"],
    )
    for imovel_cfg in sim_params["imoveis_lista"]:
        imovel = Imovel(
            valor=imovel_cfg["valor"],
            vacancia=imovel_cfg["vacancia"],
            custo_manutencao=imovel_cfg["custo_manutencao"],
            params=imovel_cfg["params"],
        )
        fii.adicionar_imovel(imovel)

    hist_precos_inicial = fii.inicializar_historico(dias=30)

    # Criação dos Agentes
    agentes = []
    agente_params_gerais = sim_params["agente"]
    for i in range(agente_params_gerais["num_agentes"]):
        agente = Agente(
            id_agente=i,
            literacia_financeira=utils.gerar_literacia_financeira(
                agente_params_gerais["literacia_media"],
                agente_params_gerais["literacia_std"],
                0.2,
                1.0,
            ),
            caixa=agente_params_gerais["caixa_inicial"],
            cotas=(
                agente_params_gerais["cotas_iniciais_primeiro"]
                if i == 0
                else agente_params_gerais["cotas_iniciais_outros"]
            ),
            exp_inflacao=agente_params_gerais["expectativa_inflacao_inicial"],
            exp_premio=agente_params_gerais["expectativa_premio_inicial"],
            hist_precos=hist_precos_inicial,
            params=agente_params_gerais.get("params", {}),
        )
        agentes.append(agente)

    for agente in agentes:
        agente.definir_vizinhos(
            agentes, num_vizinhos=agente_params_gerais["num_vizinhos"]
        )

    # Criação do Ambiente de Mercado
    bc = BancoCentral(sim_params["banco_central"])
    midia = Midia({**sim_params["midia"], "num_dias": sim_params["geral"]["num_dias"]})
    mercado = Mercado(agentes, fii, bc, midia, sim_params["mercado"])

    # Loop da Simulação
    historico_precos_fii = []
    sentimento_medio_diario = []
    num_dias = sim_params["geral"]["num_dias"]

    for dia in range(1, num_dias + 1):
        print(f"Dia {dia}/{num_dias}")
        mercado.executar_dia(sim_params["parametros_sentimento_e_ordem"])
        sentimento_medio_diario.append(utils.calcular_sentimento_medio(mercado.agentes))
        historico_precos_fii.append(mercado.fii.preco_cota)

    mercado.fechar_pool()

    # Pós-processamento e Plotagem
    historico_precos_fii_np = np.array(historico_precos_fii)
    # log_returns = np.diff(np.log(historico_precos_fii_np[historico_precos_fii_np > 0]))

    # ... (cálculo da volatilidade rolante) ...

    # Salvar Gráficos
    if not os.path.exists("results/plots"):
        os.makedirs("results/plots")

    plot_path = f"results/plots/evolucao_preco_{run_id}.png"
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(range(num_dias), historico_precos_fii_np, label="Preço da Cota do FII")
    ax.set_title(f"Evolução do Preço do FII - {run_id}")
    ax.set_ylabel("Preço")
    ax.set_xlabel("Dias")
    ax.legend()
    plt.grid(True)
    plt.savefig(plot_path)
    plt.close(fig)

    # Retornar resultados chave
    results = {
        "preco_final_cota": fii.preco_cota,
        "caixa_final_fii": fii.caixa,
        "sentimento_medio_final": sentimento_medio_diario[-1],
        "plot_path": plot_path,
    }

    print(f"--- Simulação {run_id} Concluída ---")
    return results
