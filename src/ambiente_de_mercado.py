import os
import random
import traceback
import numpy as np
from multiprocessing import Pool
from typing import List, Dict, Any

from .instrumentos_financeiros import FII
from .componentes_de_mercado import LivroOrdens
from .agentes_economicos import Investidor, calcular_preco_esperado_investidor
from .fatores_de_ambiente import BancoCentral, Midia


def _processar_investidor(dados: Dict[str, Any]) -> Dict[str, Any]:
    try:
        lf = dados["literacia_financeira"]
        hist_precos = np.array(dados["historico_precos"])
        hist_riqueza = np.array(dados["historico_riqueza"])
        sentimento_ant = dados["sentimento"]
        sentimentos_vizinhos = dados["vizinhos_sentimentos"]
        params_sent = dados["parametros_sentimento"]
        params_investidor = dados["parametros_investidor"]
        mercado_snap = dados["mercado_snapshot"]
        bc_snap = dados["banco_central_snapshot"]

        peso_si = params_sent.get("peso_sentimento_inflacao", 0.9)
        exp_inflacao = bc_snap["expectativa_inflacao"] * (1 - sentimento_ant * peso_si)

        peso_sp = params_sent.get("peso_sentimento_expectativa", 0.9)
        exp_premio = bc_snap["premio_risco"] * (1 - sentimento_ant * peso_sp)

        i_social = (
            np.mean(np.nan_to_num(np.array(sentimentos_vizinhos)))
            if sentimentos_vizinhos
            else 0.0
        )

        preco_esperado = calcular_preco_esperado_investidor(
            lf,
            params_sent["beta"],
            mercado_snap["fii_dividendos_ultimo"],
            hist_precos,
            exp_inflacao,
            exp_premio,
            params_investidor,
        )

        preco_atual = hist_precos[-1] if len(hist_precos) > 0 else 0.0
        comp_retorno = (
            np.log(preco_esperado / preco_atual)
            if preco_atual > 0 and preco_esperado > 0
            else 0.0
        )

        n = 5
        comp_riqueza = (
            (hist_riqueza[-1] - hist_riqueza[-n]) / hist_riqueza[-n]
            if len(hist_riqueza) >= n and hist_riqueza[-n] != 0
            else 0.0
        )

        peso_r = params_investidor.get("peso_retorno_privada", 0.6)
        peso_w = params_investidor.get("peso_riqueza_privada", 0.4)
        ruido = np.random.normal(0, params_investidor.get("ruido_std_privada", 0.05))
        i_privado = peso_r * comp_retorno + peso_w * comp_riqueza + ruido

        a0, b0, c0 = params_sent["a0"], params_sent["b0"], params_sent["c0"]
        sentimento_bruto = (
            a0 * lf * i_privado
            + b0 * (1 - lf) * i_social
            + c0 * (1 - lf) * mercado_snap["news"]
        )
        sentimento_final = max(min(sentimento_bruto, 1), -1)

        volatilidade = mercado_snap["volatilidade_historica"]
        risco_decisao = (sentimento_final + 1) / 2 * volatilidade

        return {
            "id": dados["id"],
            "sentimento": sentimento_final,
            "RD": risco_decisao,
        }
    except Exception:
        traceback.print_exc()
        return None


class Mercado:
    def __init__(
        self,
        investidores: List[Investidor],
        fii: FII,
        banco_central: BancoCentral,
        midia: Midia,
        parametros: dict,
    ):
        self.investidores = investidores
        self.fii = fii
        self.banco_central = banco_central
        self.midia = midia
        self.parametros = parametros
        self.livro_ordens = LivroOrdens()
        self.volatilidade_historica = self.parametros.get("volatilidade_inicial", 0.1)
        self.freq_dividendos = self.parametros.get("dividendos_frequencia", 21)
        self.freq_atu_imoveis = self.parametros.get(
            "atualizacao_imoveis_frequencia", 126
        )
        self.news = 0
        self.dia_atual = 0
        self.pool = Pool(
            processes=self.parametros.get(
                "num_processos_paralelos", os.cpu_count() // 2 or 2
            )
        )

    def executar_dia(self, parametros_sentimento):
        self.dia_atual += 1
        try:
            self.news = self.midia.gerar_noticia()
        except StopIteration:
            self.news = 0

        if self.dia_atual % self.freq_dividendos == 0:
            dividendo = self.fii.distribuir_dividendos()
            for inv in self.investidores:
                inv.caixa += inv.carteira.get("FII", 0) * dividendo

        if self.dia_atual % self.freq_atu_imoveis == 0:
            self.fii.atualizar_imoveis_com_investimento(
                self.banco_central.expectativa_inflacao
            )

        mercado_snap = {
            "volatilidade_historica": self.volatilidade_historica,
            "news": self.news,
            "fii_dividendos_ultimo": self.fii.historico_dividendos[-1],
        }
        bc_snap = {
            "expectativa_inflacao": self.banco_central.expectativa_inflacao,
            "premio_risco": self.banco_central.premio_risco,
        }

        dados_investidores = [
            {
                "id": inv.id,
                "literacia_financeira": inv.LF,
                "sentimento": inv.sentimento,
                "historico_precos": inv.historico_precos.tolist(),
                "historico_riqueza": inv.historico_riqueza.tolist(),
                "vizinhos_sentimentos": [viz.sentimento for viz in inv.vizinhos],
                "mercado_snapshot": mercado_snap,
                "banco_central_snapshot": bc_snap,
                "parametros_sentimento": parametros_sentimento,
                "parametros_investidor": inv.parametros,
            }
            for inv in self.investidores
        ]

        resultados = self.pool.map(_processar_investidor, dados_investidores)
        investidores_dict = {inv.id: inv for inv in self.investidores}
        for res in resultados:
            if res and res["id"] in investidores_dict:
                inv = investidores_dict[res["id"]]
                inv.sentimento = res["sentimento"]
                inv.historico_sentimentos.append(res["sentimento"])
                inv.RD = res["RD"]

        self.livro_ordens = LivroOrdens()
        for inv in self.investidores:
            if random.random() < inv.prob_negociar:
                ordem = inv.criar_ordem(self, parametros_sentimento)
                if ordem:
                    self.livro_ordens.adicionar_ordem(ordem)

        self.livro_ordens.executar_ordens("FII", self)

        self.fii.historico_precos.append(self.fii.preco_cota)
        for inv in self.investidores:
            inv.atualizar_historico(self.fii.preco_cota)

        if len(self.fii.historico_precos) > 1:
            precos = np.array(self.fii.historico_precos)
            precos_validos = precos[precos > 0]
            if len(precos_validos) > 1:
                retornos = np.diff(np.log(precos_validos))
                self.volatilidade_historica = np.std(retornos) * (252**0.5)

    def fechar_pool(self):
        self.pool.close()
        self.pool.join()
