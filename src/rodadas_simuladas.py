import numpy as np
import random

from .instrumentos_financeiros import FII, Imovel
from .agentes_economicos import Investidor
from .ambiente_de_mercado import Mercado
from .fatores_de_ambiente import BancoCentral, Midia
from . import utils


def run_single_simulation(sim_params: dict, run_id: str):
    print(f"--- Iniciando Simulação: {run_id} ---")

    seed = sim_params["geral"].get("random_seed", 42)
    random.seed(seed)
    np.random.seed(seed)

    # Inicialização do FII e imóveis
    fii_cfg = sim_params["fii"]
    fii = FII(
        num_cotas=fii_cfg["num_cotas"], caixa=fii_cfg["caixa_inicial"], params=fii_cfg
    )
    for imovel_cfg in sim_params["imoveis_lista"]:
        fii.adicionar_imovel(Imovel(**imovel_cfg))

    hist_precos_inicial = fii.inicializar_historico_precos(dias=30)

    # Inicialização dos investidores
    investidores = []
    investidor_cfg = sim_params["agente"]
    for i in range(investidor_cfg["num_agentes"]):
        cotas_iniciais = (
            investidor_cfg["cotas_iniciais_primeiro"]
            if i == 0
            else investidor_cfg["cotas_iniciais_outros"]
        )
        investidor = Investidor(
            id_investidor=i,
            lf=utils.gerar_literacia_financeira(
                investidor_cfg["literacia_media"],
                investidor_cfg["literacia_std"],
                0.2,
                1.0,
            ),
            caixa=investidor_cfg["caixa_inicial"],
            cotas=cotas_iniciais,
            historico_precos=hist_precos_inicial,
            parametros=investidor_cfg.get("params", {}),
        )
        investidores.append(investidor)
    for inv in investidores:
        inv.definir_vizinhos(investidores, num_vizinhos=investidor_cfg["num_vizinhos"])

    # Fatores ambientais
    bc = BancoCentral(sim_params["banco_central"])
    midia = Midia({**sim_params["midia"], "num_dias": sim_params["geral"]["num_dias"]})
    mercado = Mercado(investidores, fii, bc, midia, sim_params["mercado"])

    # Loop de simulação
    num_dias = sim_params["geral"]["num_dias"]
    sentimento_medio_diario = []
    for dia in range(1, num_dias + 1):
        print(f"Executando Dia {dia}/{num_dias}")
        mercado.executar_dia(sim_params["parametros_sentimento_e_ordem"])
        sentimento_medio_diario.append(
            utils.calcular_sentimento_medio(mercado.investidores)
        )

    mercado.fechar_pool()

    # Coleta de resultados brutos
    historico_precos_fii = np.array(mercado.fii.historico_precos[-num_dias:])
    log_returns = np.diff(np.log(historico_precos_fii[historico_precos_fii > 0]))

    window = sim_params["plot"]["window_volatilidade"]
    volatilidade_rolante = np.full_like(log_returns, np.nan)
    for i in range(window, len(log_returns)):
        volatilidade_rolante[i] = np.std(log_returns[i - window : i]) * (252**0.5)

    # Resultado completo
    results = {
        "historico_precos_fii": historico_precos_fii,
        "log_returns": log_returns,
        "volatilidade_rolante": volatilidade_rolante,
        "sentimento_medio_diario": sentimento_medio_diario,
        "objeto_fii_final": mercado.fii,
        "lista_investidores_final": mercado.investidores,
    }

    print(f"--- Simulação {run_id} Concluída ---")
    return results
