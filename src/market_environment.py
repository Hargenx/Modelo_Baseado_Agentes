import os
import random
import traceback
import numpy as np
from multiprocessing import Pool
from typing import List, Dict, Any

from .financial_instruments import FII
from .market_components import OrderBook
from .economic_agents import Agente, calcular_preco_esperado_agente
from .environment_factors import BancoCentral, Midia


def _processar_agente_para_pool(agente_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        lf = agente_data["literacia_financeira"]
        hist_precos = np.array(agente_data["historico_precos"])
        hist_riqueza = np.array(agente_data["historico_riqueza"])
        sentimento_anterior = agente_data["sentimento"]
        vizinhos_sentiments = agente_data["vizinhos_sentiments_snapshot"]
        params_sentimento = agente_data["parametros_sentimento"]
        params_agente = agente_data["agente_params"]
        mercado_snapshot = agente_data["mercado_snapshot"]
        bc_snapshot = agente_data["banco_central_snapshot"]

        # 1. Calcular expectativas
        peso_si = params_sentimento.get("peso_sentimento_inflacao", 0.9)
        exp_inflacao = bc_snapshot["expectativa_inflacao"] * (
            1 - sentimento_anterior * peso_si
        )
        peso_sp = params_sentimento.get("peso_sentimento_expectativa", 0.9)
        exp_premio = bc_snapshot["premio_risco"] * (1 - sentimento_anterior * peso_sp)

        # 2. Calcular I_social
        i_social = (
            np.mean(np.nan_to_num(np.array(vizinhos_sentiments)))
            if vizinhos_sentiments
            else 0.0
        )

        # 3. Calcular I_privada (usando a função auxiliar)
        preco_esperado = calcular_preco_esperado_agente(
            lf,
            params_sentimento["beta"],
            mercado_snapshot["fii_dividendos_ultimo"],
            hist_precos,
            exp_inflacao,
            exp_premio,
            params_agente,
        )
        preco_atual = hist_precos[-1] if len(hist_precos) > 0 else 0.0
        comp_retorno = (
            np.log(preco_esperado / preco_atual)
            if preco_atual > 0 and preco_esperado > 0
            else 0.0
        )
        n_riqueza = 5
        comp_riqueza = (
            (hist_riqueza[-1] - hist_riqueza[-n_riqueza]) / hist_riqueza[-n_riqueza]
            if len(hist_riqueza) >= n_riqueza and hist_riqueza[-n_riqueza] != 0
            else 0.0
        )
        peso_r = params_agente.get("peso_retorno_privada", 0.6)
        peso_w = params_agente.get("peso_riqueza_privada", 0.4)
        ruido = np.random.normal(0, params_agente.get("ruido_std_privada", 0.05))
        i_privado = peso_r * comp_retorno + peso_w * comp_riqueza + ruido

        # 4. Calcular sentimento e risco
        a0, b0, c0 = (
            params_sentimento["a0"],
            params_sentimento["b0"],
            params_sentimento["c0"],
        )
        s_bruto = (
            a0 * lf * i_privado
            + b0 * (1 - lf) * i_social
            + c0 * (1 - lf) * mercado_snapshot["news"]
        )
        sentimento_final = max(min(s_bruto, 1), -1)

        vol_percebida = mercado_snapshot["volatilidade_historica"]
        rd_agente = (sentimento_final + 1) / 2 * vol_percebida

        return {
            "id": agente_data["id"],
            "sentimento": sentimento_final,
            "RD": rd_agente,
        }
    except Exception:
        traceback.print_exc()
        return None


class Mercado:
    def __init__(
        self,
        agentes: List[Agente],
        fii: FII,
        banco_central: BancoCentral,
        midia: Midia,
        params: dict,
    ):
        self.agentes = agentes
        self.fii = fii
        self.banco_central = banco_central
        self.midia = midia
        self.params = params
        self.order_book = OrderBook()
        self.volatilidade_historica = self.params.get("volatilidade_inicial", 0.1)
        self.dividendos_frequencia = self.params.get("dividendos_frequencia", 21)
        self.atualizacao_imoveis_frequencia = self.params.get(
            "atualizacao_imoveis_frequencia", 126
        )
        self.news = 0
        self.dia_atual = 0
        self.pool = Pool(
            processes=self.params.get(
                "num_processos_paralelos", os.cpu_count() // 2 or 2
            )
        )

    def executar_dia(self, parametros_sentimento):
        self.dia_atual += 1
        try:
            self.news = self.midia.gerar_noticia()
        except StopIteration:
            self.news = 0

        if self.dia_atual % self.dividendos_frequencia == 0:
            dividendos_por_cota = self.fii.distribuir_dividendos()
            for agente in self.agentes:
                agente.caixa += agente.carteira.get("FII", 0) * dividendos_por_cota

        if self.dia_atual % self.atualizacao_imoveis_frequencia == 0:
            self.fii.atualizar_imoveis_investir(self.banco_central.expectativa_inflacao)

        # Preparar dados para o pool
        mercado_snapshot = {
            "volatilidade_historica": self.volatilidade_historica,
            "news": self.news,
            "fii_dividendos_ultimo": self.fii.historico_dividendos[-1],
        }
        banco_central_snapshot = {
            "expectativa_inflacao": self.banco_central.expectativa_inflacao,
            "premio_risco": self.banco_central.premio_risco,
        }
        agentes_data = [
            {
                "id": ag.id,
                "literacia_financeira": ag.LF,
                "sentimento": ag.sentimento,
                "historico_precos": ag.historico_precos.tolist(),
                "historico_riqueza": ag.historico_riqueza.tolist(),
                "vizinhos_sentiments_snapshot": [v.sentimento for v in ag.vizinhos],
                "mercado_snapshot": mercado_snapshot,
                "banco_central_snapshot": banco_central_snapshot,
                "parametros_sentimento": parametros_sentimento,
                "agente_params": ag.params,
            }
            for ag in self.agentes
        ]

        # Sincronizar resultados
        resultados_pool = self.pool.map(_processar_agente_para_pool, agentes_data)
        agentes_dict = {ag.id: ag for ag in self.agentes}
        for res in resultados_pool:
            if res and res["id"] in agentes_dict:
                ag = agentes_dict[res["id"]]
                ag.sentimento = res["sentimento"]
                ag.historico_sentimentos.append(res["sentimento"])
                ag.RD = res["RD"]

        # Partes sequenciais
        self.order_book = OrderBook()
        for agente in self.agentes:
            if random.random() < agente.prob_negociar:
                ordem = agente.criar_ordem(self, parametros_sentimento)
                if ordem:
                    self.order_book.adicionar_ordem(ordem)

        self.order_book.executar_ordens("FII", self)

        # Atualizações de fim de dia
        self.fii.historico_precos.append(self.fii.preco_cota)
        for agente in self.agentes:
            agente.atualizar_historico(self.fii.preco_cota)

        if len(self.fii.historico_precos) > 1:
            precos_validos = np.array(self.fii.historico_precos)
            precos_validos = precos_validos[precos_validos > 0]
            if len(precos_validos) > 1:
                retornos = np.diff(np.log(precos_validos))
                self.volatilidade_historica = np.std(retornos) * (252**0.5)

    def fechar_pool(self):
        self.pool.close()
        self.pool.join()
