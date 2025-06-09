import numpy as np
import random
from typing import Optional

from .market_components import Ordem
from . import utils

class Agente:
    def __init__(
        self,
        id_agente,
        literacia_financeira,
        caixa,
        cotas,
        exp_inflacao,
        exp_premio,
        hist_precos,
        params,
    ):
        self.id = id_agente
        self.LF = literacia_financeira
        self.caixa = caixa
        self.cotas = cotas
        self.params = params if params is not None else {}

        piso_prob = self.params.get("piso_prob_negociar", 0.3)
        fator_lf_prob = self.params.get("fator_lf_prob_negociar", 0.9)
        self.prob_negociar = np.clip(
            piso_prob + fator_lf_prob * ((1 - self.LF) ** 2), 0.1, 1.0
        )

        self.saldo = caixa
        self.carteira = {"FII": cotas}
        self.sentimento = 0.0
        self.RD = 0.0
        self.percentual_alocacao = 0.0
        self.expectativa_inflacao = exp_inflacao
        self.expectativa_premio = exp_premio

        self.historico_precos = np.array(hist_precos)
        self.historico_riqueza = np.array(
            [caixa + cotas * (hist_precos[-1] if hist_precos else 0)]
        )
        self.historico_sentimentos = []
        self.vizinhos = []

    def definir_vizinhos(self, todos_agentes: list, num_vizinhos: int):
        candidatos = [agente for agente in todos_agentes if agente.id != self.id]
        self.vizinhos = random.sample(candidatos, min(num_vizinhos, len(candidatos)))

    def calcular_preco_esperado(self, beta, dividendos):
        x = self.LF / (np.exp(1) ** beta)
        z = (1 - beta) * (1 - self.LF)
        y = 1 - x - z

        preco_fundamentalista = (
            dividendos * 12 * (1 + self.expectativa_inflacao) / self.expectativa_premio
        )

        retorno_fundamentalista = 0.0
        if (
            len(self.historico_precos) > 0
            and self.historico_precos[-1] > 0
            and preco_fundamentalista > 0
        ):
            retorno_fundamentalista = np.log(preco_fundamentalista) - np.log(
                self.historico_precos[-1]
            )

        tipo_media = self.params.get("tipo_media_movel", "ema")
        media_movel_params = self.params.get("media_movel_params", {})

        mm_short, mm_long = utils.calcular_media_movel_tecnica(
            self.historico_precos, self.LF, tipo_media, media_movel_params
        )

        retorno_especulador = 0.0
        if mm_long > 0:
            retorno_especulador = np.log(mm_short / mm_long)

        ruido_std = self.params.get("ruido_std", 0.1)
        retorno_ruido = np.random.normal(0, ruido_std)

        retorno_expectativa = (
            (x * retorno_fundamentalista)
            + (y * retorno_especulador)
            + (z * retorno_ruido)
        )

        preco_esperado = 0.0
        if len(self.historico_precos) > 0 and self.historico_precos[-1] > 0:
            preco_esperado = self.historico_precos[-1] * np.exp(retorno_expectativa)

        return preco_esperado

    def calcular_I_privada(self, n, beta, dividendos):
        peso_retorno = self.params.get("peso_retorno_privada", 0.8)
        peso_riqueza = self.params.get("peso_riqueza_privada", 0.4)
        ruido_std_privada = self.params.get("ruido_std_privada", 0.05)

        preco_esperado = self.calcular_preco_esperado(beta, dividendos)
        preco_atual = (
            self.historico_precos[-1] if len(self.historico_precos) > 0 else 0.0
        )

        componente_retorno = 0.0
        if preco_atual > 0 and preco_esperado > 0:
            componente_retorno = np.log(preco_esperado / preco_atual)

        componente_riqueza = 0.0
        if len(self.historico_riqueza) >= n and self.historico_riqueza[-n] != 0:
            variacao_riqueza = (
                self.historico_riqueza[-1] - self.historico_riqueza[-n]
            ) / self.historico_riqueza[-n]
            componente_riqueza = variacao_riqueza

        I_privada = (
            peso_retorno * componente_retorno
            + peso_riqueza * componente_riqueza
            + np.random.normal(0, ruido_std_privada)
        )
        return I_privada

    def calcular_I_social(self):
        if not self.vizinhos:
            return 0.0
        sentimentos_vizinhos = np.array(
            [
                (
                    np.mean(v.historico_sentimentos[-3:])
                    if len(v.historico_sentimentos) >= 3
                    else (
                        np.mean(v.historico_sentimentos)
                        if v.historico_sentimentos
                        else 0.0
                    )
                )
                for v in self.vizinhos
            ]
        )
        return np.mean(np.nan_to_num(sentimentos_vizinhos))

    def calcular_sentimento_risco_alocacao(
        self, mercado_snapshot: dict, parametros: dict
    ) -> None:
        # Note que agora o primeiro argumento é o dicionário do snapshot

        I_privado = self.calcular_I_privada(
            n=5,
            beta=parametros["beta"],
            dividendos=mercado_snapshot["fii"].historico_dividendos[
                -1
            ],  # Acessando via dicionário
        )
        I_social = self.calcular_I_social()

        volatilidade_percebida = mercado_snapshot[
            "volatilidade_historica"
        ]  # Acessando via dicionário
        news = mercado_snapshot["news"]  # Acessando via dicionário

        a_i = parametros["a0"] * self.LF
        b_i = parametros["b0"] * (1 - self.LF)
        c_i = parametros["c0"] * (1 - self.LF)

        S_bruto = round(a_i * I_privado + b_i * I_social + c_i * news, 4)
        self.sentimento = max(min(S_bruto, 1), -1)
        self.historico_sentimentos.append(self.sentimento)

        self.RD = (self.sentimento + 1) / 2 * volatilidade_percebida
        self.percentual_alocacao = (
            self.RD / volatilidade_percebida if volatilidade_percebida > 0 else 0
        )

    def calcular_expectativas(self, banco_central, noticias, parametros):
        peso_sentimento_inflacao = parametros.get("peso_sentimento_inflacao", 0.9)
        self.expectativa_inflacao = banco_central.expectativa_inflacao * (
            1 - self.sentimento * peso_sentimento_inflacao
        )

        peso_sentimento_expectativa = parametros.get("peso_sentimento_expectativa", 0.9)
        self.expectativa_premio = banco_central.premio_risco * (
            1 - self.sentimento * peso_sentimento_expectativa
        )

    def criar_ordem(self, mercado, parametros) -> Optional[Ordem]:
        ativo = "FII"
        preco_mercado = mercado.fii.preco_cota
        if preco_mercado <= 0:
            return None

        dividendos_atuais = mercado.fii.historico_dividendos[-1]

        preco_esperado = self.calcular_preco_esperado(
            beta=parametros["beta"], dividendos=dividendos_atuais
        )

        peso_preco_esperado = parametros.get("peso_preco_esperado", 0.3)

        if preco_mercado < preco_esperado:
            qtd_min = parametros.get("quantidade_compra_min", 1)
            qtd_max = parametros.get("quantidade_compra_max", 10)
            cotas_desejadas = random.randint(qtd_min, qtd_max)
            valor_necessario = preco_mercado * cotas_desejadas

            if self.saldo >= valor_necessario:
                preco_limite = (
                    1 - peso_preco_esperado
                ) * preco_mercado + peso_preco_esperado * preco_esperado
                return Ordem("compra", self, ativo, preco_limite, cotas_desejadas)

        elif preco_mercado > preco_esperado:
            cotas_possuidas = self.carteira.get(ativo, 0)
            if cotas_possuidas > 0:
                preco_limite = (
                    1 - peso_preco_esperado
                ) * preco_mercado + peso_preco_esperado * preco_esperado
                divisor_venda = parametros.get("divisor_quantidade_venda", 5)
                qtd_venda_max = max(1, int(cotas_possuidas / divisor_venda))
                return Ordem(
                    "venda", self, ativo, preco_limite, random.randint(1, qtd_venda_max)
                )

        return None

    def atualizar_historico(self, preco_fii):
        riqueza_atual = self.caixa + self.carteira.get("FII", 0) * preco_fii
        self.historico_riqueza = np.append(self.historico_riqueza, riqueza_atual)
        self.historico_precos = np.append(self.historico_precos, preco_fii)
