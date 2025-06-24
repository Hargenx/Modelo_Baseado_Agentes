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
        self.params = params or {}
        self.aluguel_fator = self.params.get("aluguel_factor", 0.005)
        self.desvio_normal = self.params.get("desvio_normal", 0.1)
        self.aluguel = self.valor * self.aluguel_fator

    def gerar_fluxo_aluguel(self) -> float:
        vacancia_ajustada = self.vacancia * (
            1 + np.random.normal(0, self.desvio_normal)
        )
        return self.aluguel * (1 - vacancia_ajustada)


class FII:
    def __init__(self, num_cotas: int, caixa: float, params: dict = None):
        self.num_cotas = num_cotas
        self.caixa = caixa
        self.params = params or {}
        self.imoveis: List[Imovel] = []
        self.preco_cota = 0.0
        self.historico_precos: List[float] = []
        self.historico_dividendos: List[float] = []

    def adicionar_imovel(self, imovel: Imovel) -> None:
        self.imoveis.append(imovel)

    def valor_patrimonial_por_cota(self) -> float:
        valor_imoveis = sum(imovel.valor for imovel in self.imoveis)
        total_patrimonio = self.caixa + valor_imoveis
        return total_patrimonio / self.num_cotas if self.num_cotas > 0 else 0

    def calcular_fluxo_total_aluguel(self) -> float:
        return sum(imovel.gerar_fluxo_aluguel() for imovel in self.imoveis)

    def distribuir_dividendos(self) -> float:
        fluxo_total = self.calcular_fluxo_total_aluguel()
        taxa_dividendo = self.params.get("dividendos_taxa", 0.95)
        taxa_caixa = self.params.get("dividendos_caixa_taxa", 0.05)

        dividendos_por_cota = (
            fluxo_total * taxa_dividendo / self.num_cotas if self.num_cotas > 0 else 0
        )
        self.historico_dividendos.append(dividendos_por_cota)
        self.caixa += fluxo_total * taxa_caixa
        return dividendos_por_cota

    def atualizar_imoveis_com_investimento(self, inflacao: float) -> None:
        fracao_investimento = self.params.get("investimento_fracao", 0.50)
        valor_investimento = fracao_investimento * self.caixa
        self.caixa -= valor_investimento

        if not self.imoveis:
            return

        investimento_unitario = valor_investimento / len(self.imoveis)
        novo_aluguel_fator = self.params.get("aluguel_factor_imovel", 0.005)

        for imovel in self.imoveis:
            imovel.valor *= 1 + inflacao
            imovel.valor += investimento_unitario
            imovel.aluguel = imovel.valor * novo_aluguel_fator

    def inicializar_historico_precos(self, dias: int = 30) -> List[float]:
        vp = self.valor_patrimonial_por_cota()
        self.preco_cota = vp
        self.historico_precos = [vp] * dias
        self.historico_dividendos.append(vp)
        return self.historico_precos
