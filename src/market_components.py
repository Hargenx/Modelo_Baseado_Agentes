from dataclasses import dataclass
from typing import TYPE_CHECKING



if TYPE_CHECKING:
    from .economic_agents import Agente
    from src.market_environment import Mercado


@dataclass
class Ordem:
    tipo: str
    agente: "Agente"
    ativo: str
    preco_limite: float
    quantidade: int


@dataclass
class Transacao:
    comprador: "Agente"
    vendedor: "Agente"
    ativo: str
    quantidade: int
    preco_execucao: float

    def executar(self) -> None:
        valor_total = self.quantidade * self.preco_execucao
        self.comprador.caixa -= valor_total
        self.vendedor.caixa += valor_total
        self.comprador.carteira[self.ativo] += self.quantidade
        self.vendedor.carteira[self.ativo] -= self.quantidade


class OrderBook:
    def __init__(self):
        self.ordens_compra = {}
        self.ordens_venda = {}

    def adicionar_ordem(self, ordem: Ordem):
        ordens = self.ordens_compra if ordem.tipo == "compra" else self.ordens_venda
        ordens.setdefault(ordem.ativo, []).append(ordem)

    def executar_ordens(self, ativo: str, mercado: "Mercado"):
        if ativo in self.ordens_compra and ativo in self.ordens_venda:
            compras = self.ordens_compra[ativo]
            vendas = self.ordens_venda[ativo]
            compras.sort(key=lambda x: x.preco_limite, reverse=True)
            vendas.sort(key=lambda x: x.preco_limite)

            while (
                compras and vendas and compras[0].preco_limite >= vendas[0].preco_limite
            ):
                compra = compras[0]
                venda = vendas[0]
                preco_execucao = (compra.preco_limite + venda.preco_limite) / 2
                qtd_exec = min(compra.quantidade, venda.quantidade)

                transacao = Transacao(
                    compra.agente, venda.agente, ativo, qtd_exec, preco_execucao
                )
                transacao.executar()

                mercado.fii.preco_cota = preco_execucao
                compra.quantidade -= qtd_exec
                venda.quantidade -= qtd_exec

                if compra.quantidade == 0:
                    compras.pop(0)
                if venda.quantidade == 0:
                    vendas.pop(0)
