import os
import random
import traceback
import numpy as np
from multiprocessing import Pool
from typing import List

# Importações de outros módulos do projeto
from .economic_agents import Agente
from .financial_instruments import FII
from .market_components import OrderBook


def _processar_agente(agente_data_tuple):
    agente_obj, mercado_snapshot_dict, parametros_sentimento = agente_data_tuple
    try:
        agente_obj.calcular_sentimento_risco_alocacao(
            mercado_snapshot_dict, parametros_sentimento
        )
        agente_obj.calcular_expectativas(
            mercado_snapshot_dict["banco_central"],
            mercado_snapshot_dict["news"],
            parametros_sentimento,
        )
        return agente_obj
    except Exception as e:
        print(f"Erro processando agente {agente_obj.id}: {e}")
        traceback.print_exc()
        return None


class BancoCentral:
    def __init__(self, params: dict = None):
        params = params if params is not None else {}
        self.taxa_selic = params.get("taxa_selic", 0.15)
        self.expectativa_inflacao = params.get("expectativa_inflacao", 0.07)
        self.premio_risco = params.get("premio_risco", 0.08)


class Midia:
    def __init__(self, params: dict = None):
        params = params if params is not None else {}
        self.dias = params.get("num_dias", 252)
        self.valor_atual = params.get("valor_inicial", 0)
        self.sigma = params.get("sigma", 0.1)
        # As chaves do JSON são strings, convertemos para inteiros
        self.valores_fixos = {
            int(k): v for k, v in params.get("valores_fixos", {}).items()
        }
        self.t = 0
        self.historico = [self.valor_atual]

    def gerar_noticia(self):
        if self.t >= self.dias + 2:
            raise StopIteration("Fim da simulação de notícias.")

        self.t += 1

        if self.t in self.valores_fixos:
            self.valor_atual = self.valores_fixos[self.t]
        else:
            passo = np.random.normal(0, self.sigma)
            self.valor_atual = np.clip(self.valor_atual + passo, -3, 3)

        self.historico.append(self.valor_atual)
        return self.valor_atual


class Mercado:
    def __init__(
        self,
        agentes: List[Agente],
        fii: FII,
        banco_central: BancoCentral,
        midia: Midia,
        params: dict = None,
    ):
        self.agentes = agentes
        self.fii = fii
        self.banco_central = banco_central
        self.midia = midia
        self.params = params if params is not None else {}

        self.order_book = OrderBook()
        self.volatilidade_historica = self.params.get("volatilidade_inicial", 0.1)
        self.dividendos_frequencia = self.params.get("dividendos_frequencia", 21)
        self.atualizacao_imoveis_frequencia = self.params.get(
            "atualizacao_imoveis_frequencia", 126
        )

        self.news = 0
        self.historico_news = []
        self.dia_atual = 0

        num_procs = self.params.get("num_processos_paralelos", os.cpu_count() // 2 or 2)
        self.pool = Pool(processes=num_procs)

    def executar_dia(self, parametros_sentimento):
        self.dia_atual += 1

        try:
            self.news = self.midia.gerar_noticia()
            self.historico_news.append(self.news)
        except StopIteration:
            self.news = self.historico_news[-1] if self.historico_news else 0

        if self.dia_atual % self.dividendos_frequencia == 0:
            dividendos_por_cota = self.fii.distribuir_dividendos()
            for agente in self.agentes:
                agente.caixa += agente.carteira.get("FII", 0) * dividendos_por_cota
                agente.saldo = agente.caixa

        if self.dia_atual % self.atualizacao_imoveis_frequencia == 0:
            self.fii.atualizar_imoveis_investir(self.banco_central.expectativa_inflacao)

        mercado_snapshot = {
            "volatilidade_historica": self.volatilidade_historica,
            "news": self.news,
            "fii": self.fii,
            "banco_central": self.banco_central,
        }

        agentes_data_para_pool = [
            (agente, mercado_snapshot, parametros_sentimento) for agente in self.agentes
        ]

        agentes_atualizados = self.pool.map(_processar_agente, agentes_data_para_pool)
        self.agentes = [ag for ag in agentes_atualizados if ag is not None]

        self.order_book = OrderBook()
        for agente in self.agentes:
            if random.random() < agente.prob_negociar:
                ordem = agente.criar_ordem(self, parametros_sentimento)
                if ordem:
                    self.order_book.adicionar_ordem(ordem)

        self.order_book.executar_ordens("FII", self)

        self.fii.historico_precos.append(self.fii.preco_cota)
        for agente in self.agentes:
            agente.atualizar_historico(self.fii.preco_cota)

        # --- BLOCO CORRIGIDO ABAIXO ---
        # 10. Calcular Volatilidade Histórica para o PRÓXIMO dia
        if len(self.fii.historico_precos) > 1:
            window_vol = parametros_sentimento.get("window_volatilidade", 200)
            precos_np = np.array(self.fii.historico_precos)

            # Garante que não há preços <= 0 para o cálculo do log
            precos_validos = precos_np[precos_np > 0]

            if len(precos_validos) >= window_vol + 1:
                precos_janela = precos_validos[-(window_vol + 1) :]
                retornos_janela = np.diff(np.log(precos_janela))
                if len(retornos_janela) > 1:
                    self.volatilidade_historica = np.std(retornos_janela) * (252**0.5)
            elif len(precos_validos) > 1:
                retornos_janela = np.diff(np.log(precos_validos))
                if len(retornos_janela) > 1:
                    self.volatilidade_historica = np.std(retornos_janela) * (252**0.5)

        print(
            f"[Mercado] Dia {self.dia_atual}: Preço Fechamento: R${self.fii.preco_cota:,.2f}, Vol. Histórica (Prox Dia): {self.volatilidade_historica:.4f}"
        )

    def fechar_pool(self):
        self.pool.close()
        self.pool.join()
        print("Pool de processos fechado.")
