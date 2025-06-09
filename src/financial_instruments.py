import numpy as np
from typing import List


class Imovel:
    def __init__(
        self,
        valor: float,
        vacancia: float,
        custo_manutencao: float,
        params: dict = None,
    ):
        self.valor = valor
        self.vacancia = vacancia
        self.custo_manutencao = custo_manutencao
        self.params = params if params is not None else {}
        self.aluguel_factor = self.params.get("aluguel_factor", 0.005)
        self.desvio_normal = self.params.get("desvio_normal", 0.1)
        self.aluguel = self.valor * self.aluguel_factor

    def gerar_fluxo_aluguel(self) -> float:
        return self.aluguel * (
            1 - self.vacancia * (1 + np.random.normal(0, self.desvio_normal))
        )


class FII:
    def __init__(self, num_cotas: int, caixa: float, params: dict = None):
        self.num_cotas = num_cotas
        self.caixa = caixa
        self.params = params if params is not None else {}
        self.imoveis: List[Imovel] = []
        self.preco_cota = 0.0
        self.historico_precos = []
        self.historico_dividendos = []

    def adicionar_imovel(self, imovel: Imovel) -> None:
        self.imoveis.append(imovel)

    def valor_patrimonial_por_acao(self) -> float:
        if not self.imoveis:
            return self.caixa / self.num_cotas if self.num_cotas > 0 else 0
        total_valor_imoveis = sum(imovel.valor for imovel in self.imoveis)
        return (self.caixa + total_valor_imoveis) / self.num_cotas

    def calcular_fluxo_aluguel(self) -> float:
        return sum(imovel.gerar_fluxo_aluguel() for imovel in self.imoveis)

    def distribuir_dividendos(self) -> float:
        fluxo_aluguel = self.calcular_fluxo_aluguel()
        dividendos_rate = self.params.get("dividendos_taxa", 0.95)
        caixa_rate = self.params.get("dividendos_caixa_taxa", 0.05)

        dividendos = (
            fluxo_aluguel * dividendos_rate / self.num_cotas
            if self.num_cotas > 0
            else 0
        )
        self.historico_dividendos.append(dividendos)
        self.caixa += fluxo_aluguel * caixa_rate
        return dividendos

    def atualizar_imoveis_investir(self, inflacao: float) -> None:
        investimento_fracao = self.params.get("investimento_fracao", 0.50)
        valor_investir = investimento_fracao * self.caixa
        self.caixa -= valor_investir

        num_imoveis = len(self.imoveis)
        investimento_por_imovel = valor_investir / num_imoveis if num_imoveis > 0 else 0

        aluguel_factor = self.params.get("aluguel_factor_imovel", 0.005)

        for imovel in self.imoveis:
            imovel.valor *= 1 + inflacao
            imovel.valor += investimento_por_imovel
            imovel.aluguel = imovel.valor * aluguel_factor

    def inicializar_historico(self, dias: int = 30) -> list:
        self.historico_precos = []
        vp = self.valor_patrimonial_por_acao()
        self.preco_cota = vp
        self.historico_dividendos.append(vp)
        for _ in range(dias):
            self.historico_precos.append(vp)
        return self.historico_precos
