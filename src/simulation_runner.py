import numpy as np
import matplotlib.pyplot as plt
import random
import os

from .financial_instruments import FII, Imovel
from .economic_agents import Agente
from .market_environment import Mercado
from .environment_factors import BancoCentral, Midia
from . import utils


def run_single_simulation(sim_params: dict, run_id: str):
    print(f"--- Iniciando Simulação: {run_id} ---")

    seed = sim_params["geral"].get("random_seed", 42)
    random.seed(seed)
    np.random.seed(seed)

    # Inicialização (como antes)
    fii_cfg = sim_params["fii"]
    fii = FII(
        num_cotas=fii_cfg["num_cotas"], caixa=fii_cfg["caixa_inicial"], params=fii_cfg
    )
    for imovel_cfg in sim_params["imoveis_lista"]:
        fii.adicionar_imovel(Imovel(**imovel_cfg))

    hist_precos_inicial = fii.inicializar_historico(dias=30)

    agentes = []
    agente_cfg = sim_params["agente"]
    for i in range(agente_cfg["num_agentes"]):
        cotas_iniciais = (
            agente_cfg["cotas_iniciais_primeiro"]
            if i == 0
            else agente_cfg["cotas_iniciais_outros"]
        )
        agente = Agente(
            id_agente=i,
            lf=utils.gerar_literacia_financeira(
                agente_cfg["literacia_media"], agente_cfg["literacia_std"], 0.2, 1.0
            ),
            caixa=agente_cfg["caixa_inicial"],
            cotas=cotas_iniciais,
            hist_precos=hist_precos_inicial,
            params=agente_cfg.get("params", {}),
        )
        agentes.append(agente)
    for ag in agentes:
        ag.definir_vizinhos(agentes, num_vizinhos=agente_cfg["num_vizinhos"])

    bc = BancoCentral(sim_params["banco_central"])
    midia = Midia({**sim_params["midia"], "num_dias": sim_params["geral"]["num_dias"]})
    mercado = Mercado(agentes, fii, bc, midia, sim_params["mercado"])

    # Loop da Simulação
    num_dias = sim_params["geral"]["num_dias"]
    sentimento_medio_diario = []
    for dia in range(1, num_dias + 1):
        print(f"Executando Dia {dia}/{num_dias}")
        mercado.executar_dia(sim_params["parametros_sentimento_e_ordem"])
        sentimento_medio_diario.append(utils.calcular_sentimento_medio(mercado.agentes))

    mercado.fechar_pool()

    # --- COLETA DE RESULTADOS BRUTOS ---
    historico_precos_fii = np.array(mercado.fii.historico_precos[-num_dias:])
    log_returns = np.diff(np.log(historico_precos_fii[historico_precos_fii > 0]))

    window = sim_params["plot"]["window_volatilidade"]
    volatilidade_rolante = np.full_like(log_returns, np.nan)
    for i in range(window, len(log_returns)):
        volatilidade_rolante[i] = np.std(log_returns[i - window : i]) * (252**0.5)

    # --- RETORNANDO O DICIONÁRIO COMPLETO ---
    results = {
        "historico_precos_fii": historico_precos_fii,
        "log_returns": log_returns,
        "volatilidade_rolante": volatilidade_rolante,
        "sentimento_medio_diario": sentimento_medio_diario,
        "objeto_fii_final": mercado.fii,
        "lista_agentes_final": mercado.agentes,
    }

    print(f"--- Simulação {run_id} Concluída ---")
    return results
