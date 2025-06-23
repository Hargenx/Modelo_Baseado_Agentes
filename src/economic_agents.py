# src/economic_agents.py
import numpy as np
import random
from typing import TYPE_CHECKING, Optional, Dict, Any

if TYPE_CHECKING:
    from .market_environment import Mercado

from . import utils
from .market_components import Ordem


def calcular_preco_esperado_investidor(
    lf: float,
    beta: float,
    dividendos: float,
    historico_precos: np.ndarray,
    expectativa_inflacao: float,
    expectativa_premio: float,
    parametros_investidor: Dict[str, Any],
) -> float:
    x = lf / (np.exp(1) ** beta)
    z = (1 - beta) * (1 - lf)
    y = 1 - x - z

    preco_fundamentalista = 0.0
    if expectativa_premio > 0:
        preco_fundamentalista = (
            dividendos * 12 * (1 + expectativa_inflacao) / expectativa_premio
        )

    retorno_fundamentalista = 0.0
    if (
        len(historico_precos) > 0
        and historico_precos[-1] > 0
        and preco_fundamentalista > 0
    ):
        retorno_fundamentalista = np.log(preco_fundamentalista) - np.log(
            historico_precos[-1]
        )

    tipo_media = parametros_investidor.get("tipo_media_movel", "ema")
    parametros_mm = parametros_investidor.get("media_movel_params", {})
    mm_curta, mm_longa = utils.calcular_media_movel_tecnica(
        historico_precos, lf, tipo_media, parametros_mm
    )

    retorno_especulador = np.log(mm_curta / mm_longa) if mm_longa > 0 else 0.0
    retorno_ruido = np.random.normal(
        0, parametros_investidor.get("ruido_std_preco_esperado", 0.1)
    )

    retorno_total = (
        (x * retorno_fundamentalista) + (y * retorno_especulador) + (z * retorno_ruido)
    )

    preco_esperado = (
        historico_precos[-1] * np.exp(retorno_total)
        if len(historico_precos) > 0 and historico_precos[-1] > 0
        else 0.0
    )
    return preco_esperado


class Investidor:
    def __init__(
        self,
        id_investidor: int,
        lf: float,
        caixa: float,
        cotas: int,
        historico_precos: list,
        parametros: dict,
    ):
        self.id = id_investidor
        self.LF = lf
        self.caixa = caixa
        self.parametros = parametros
        piso = self.parametros.get("piso_prob_negociar", 0.3)
        fator = self.parametros.get("fator_lf_prob_negociar", 0.9)
        self.prob_negociar = np.clip(piso + fator * ((1 - self.LF) ** 2), 0.1, 1.0)

        self.carteira = {"FII": cotas}
        self.sentimento = 0.0
        self.RD = 0.0
        self.percentual_alocacao = 0.0

        self.historico_precos = np.array(historico_precos)
        self.historico_riqueza = np.array(
            [caixa + cotas * (historico_precos[-1] if historico_precos else 0)]
        )
        self.historico_sentimentos = []
        self.vizinhos = []

    def definir_vizinhos(self, todos_investidores: list, num_vizinhos: int):
        candidatos = [i for i in todos_investidores if i.id != self.id]
        self.vizinhos = random.sample(candidatos, min(num_vizinhos, len(candidatos)))

    def criar_ordem(self, mercado: "Mercado", parametros: dict) -> Optional[Ordem]:
        ativo = "FII"
        preco_mercado = mercado.fii.preco_cota
        if preco_mercado <= 0:
            return None

        dividendos = mercado.fii.historico_dividendos[-1]

        preco_esperado = calcular_preco_esperado_investidor(
            self.LF,
            parametros["beta"],
            dividendos,
            self.historico_precos,
            mercado.banco_central.expectativa_inflacao,
            mercado.banco_central.premio_risco,
            self.parametros,
        )

        peso_preco_esperado = parametros.get("peso_preco_esperado", 0.35)

        if preco_mercado < preco_esperado:
            qtd_min = parametros.get("quantidade_compra_min", 1)
            qtd_max = parametros.get("quantidade_compra_max", 30)
            cotas_desejadas = random.randint(qtd_min, qtd_max)
            valor_total = preco_mercado * cotas_desejadas
            if self.caixa >= valor_total:
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
                divisor = parametros.get("divisor_quantidade_venda", 5)
                qtd_max_venda = max(1, int(cotas_possuidas / divisor))
                return Ordem(
                    "venda", self, ativo, preco_limite, random.randint(1, qtd_max_venda)
                )

        return None

    def atualizar_historico(self, preco_fii: float):
        riqueza_atual = self.caixa + self.carteira.get("FII", 0) * preco_fii
        self.historico_riqueza = np.append(self.historico_riqueza, riqueza_atual)
        self.historico_precos = np.append(self.historico_precos, preco_fii)
