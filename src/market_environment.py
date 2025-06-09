import os
import random
import traceback
import numpy as np
from multiprocessing import Pool
from typing import List, Dict, Any

# Importações de outros módulos do projeto
from .economic_agents import Agente
from .financial_instruments import FII
from .market_components import OrderBook
from . import utils


# --- FUNÇÃO DE PROCESSAMENTO PARALELO ---
# Esta função agora é independente. Ela recebe apenas dicionários e listas,
# realiza todos os cálculos e retorna um dicionário de resultados.
def _processar_agente_para_pool(agente_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Extrai todos os dados necessários do dicionário
        lf = agente_data["literacia_financeira"]
        hist_precos = np.array(agente_data["historico_precos"])
        hist_riqueza = np.array(agente_data["historico_riqueza"])
        sentimento_anterior = agente_data["sentimento"]
        vizinhos_sentiments = agente_data["vizinhos_sentiments_snapshot"]

        # Parâmetros de sentimento e do agente
        params_sentimento = agente_data["parametros_sentimento"]
        params_agente = agente_data["agente_params"]

        # Snapshots do mercado e BC
        mercado_snapshot = agente_data["mercado_snapshot"]
        bc_snapshot = agente_data["banco_central_snapshot"]

        # --- Lógica de cálculo (movida de volta para cá, mas de forma segura) ---

        # 1. Calcular expectativas do agente
        exp_inflacao_agente = bc_snapshot["expectativa_inflacao"] * (
            1 - sentimento_anterior * params_agente.get("peso_sentimento_inflacao", 0.9)
        )
        exp_premio_agente = bc_snapshot["premio_risco"] * (
            1
            - sentimento_anterior
            * params_agente.get("peso_sentimento_expectativa", 0.9)
        )

        # 2. Calcular I_social
        i_social = (
            np.mean(np.nan_to_num(np.array(vizinhos_sentiments)))
            if vizinhos_sentiments
            else 0.0
        )

        # 3. Calcular I_privada
        preco_esperado = utils.calcular_preco_esperado_agente(
            lf,
            hist_precos,
            params_sentimento["beta"],
            mercado_snapshot["fii_dividendos_ultimo"],
            params_agente,
            exp_inflacao_agente,
            exp_premio_agente,
        )

        preco_atual = hist_precos[-1] if len(hist_precos) > 0 else 0.0

        comp_retorno = 0.0
        if preco_atual > 0 and preco_esperado > 0:
            comp_retorno = np.log(preco_esperado / preco_atual)

        comp_riqueza = 0.0
        n_riqueza = 5
        if len(hist_riqueza) >= n_riqueza and hist_riqueza[-n_riqueza] != 0:
            comp_riqueza = (hist_riqueza[-1] - hist_riqueza[-n_riqueza]) / hist_riqueza[
                -n_riqueza
            ]

        peso_retorno = params_agente.get("peso_retorno_privada", 0.8)
        peso_riqueza = params_agente.get("peso_riqueza_privada", 0.4)
        ruido_privada = np.random.normal(
            0, params_agente.get("ruido_std_privada", 0.05)
        )

        i_privado = (
            peso_retorno * comp_retorno + peso_riqueza * comp_riqueza + ruido_privada
        )

        # 4. Calcular sentimento final
        a0, b0, c0 = (
            params_sentimento["a0"],
            params_sentimento["b0"],
            params_sentimento["c0"],
        )
        s_bruto = round(
            a0 * lf * i_privado
            + b0 * (1 - lf) * i_social
            + c0 * (1 - lf) * mercado_snapshot["news"],
            4,
        )
        sentimento_final = max(min(s_bruto, 1), -1)

        # 5. Calcular alocação de risco
        vol_percebida = mercado_snapshot["volatilidade_historica"]
        rd_agente = (sentimento_final + 1) / 2 * vol_percebida
        perc_alocacao = rd_agente / vol_percebida if vol_percebida > 0 else 0

        return {
            "id": agente_data["id"],
            "sentimento": sentimento_final,
            "expectativa_inflacao": exp_inflacao_agente,
            "expectativa_premio": exp_premio_agente,
            "RD": rd_agente,
            "percentual_alocacao": perc_alocacao,
        }

    except Exception as e:
        print(f"Erro processando agente {agente_data.get('id', -1)}: {e}")
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

        # --- CORREÇÃO PRINCIPAL: CRIAÇÃO DE SNAPSHOTS SIMPLES ---
        mercado_snapshot = {
            "volatilidade_historica": self.volatilidade_historica,
            "news": self.news,
            "fii_dividendos_ultimo": (
                self.fii.historico_dividendos[-1]
                if self.fii.historico_dividendos
                else 0.0
            ),
        }
        banco_central_snapshot = {
            "expectativa_inflacao": self.banco_central.expectativa_inflacao,
            "premio_risco": self.banco_central.premio_risco,
        }

        agentes_data_para_pool = []
        for agente in self.agentes:
            agente_data = {
                "id": agente.id,
                "literacia_financeira": agente.LF,
                "sentimento": agente.sentimento,
                "historico_precos": agente.historico_precos.tolist(),
                "historico_riqueza": agente.historico_riqueza.tolist(),
                "vizinhos_sentiments_snapshot": [v.sentimento for v in agente.vizinhos],
                "mercado_snapshot": mercado_snapshot,
                "banco_central_snapshot": banco_central_snapshot,
                "parametros_sentimento": parametros_sentimento,
                "agente_params": agente.params,
            }
            agentes_data_para_pool.append(agente_data)

        agentes_dados_atualizados = self.pool.map(
            _processar_agente_para_pool, agentes_data_para_pool
        )

        agentes_dict = {ag.id: ag for ag in self.agentes}
        for dados in agentes_dados_atualizados:
            if dados and dados["id"] in agentes_dict:
                agente = agentes_dict[dados["id"]]
                agente.sentimento = dados["sentimento"]
                agente.historico_sentimentos.append(dados["sentimento"])
                agente.expectativa_inflacao = dados["expectativa_inflacao"]
                agente.expectativa_premio = dados["expectativa_premio"]
                agente.RD = dados["RD"]
                agente.percentual_alocacao = dados["percentual_alocacao"]
        # ----------------------------------------------------------------

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

        if len(self.fii.historico_precos) > 1:
            window_vol = parametros_sentimento.get("window_volatilidade", 200)
            precos_np = np.array(self.fii.historico_precos)
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
