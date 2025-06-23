# src/market_components.py

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from .economic_agents import Agente
    from .market_environment import Mercado


@dataclass
class Ordem:
    tipo: str  # "compra" ou "venda"
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


class LivroOrdens:
    """
    Livro de ordens (Order Book) para armazenar e executar ordens de compra e venda.
    """

    def __init__(self) -> None:
        self.ordens_compra: Dict[str, List[Ordem]] = {}
        self.ordens_venda: Dict[str, List[Ordem]] = {}

    def adicionar_ordem(self, ordem: Ordem) -> None:
        """
        Adiciona uma ordem ao livro, separando entre compra e venda.
        """
        destino = self.ordens_compra if ordem.tipo == "compra" else self.ordens_venda
        destino.setdefault(ordem.ativo, []).append(ordem)

    def executar_ordens(self, ativo: str, mercado: "Mercado") -> None:
        """
        Executa as ordens para um ativo, cruzando ordens de compra e venda.
        """
        if ativo not in self.ordens_compra or ativo not in self.ordens_venda:
            return

        compras = self.ordens_compra[ativo]
        vendas = self.ordens_venda[ativo]

        # Ordena as ordens: compras por maior preço, vendas por menor
        compras.sort(key=lambda ordem: ordem.preco_limite, reverse=True)
        vendas.sort(key=lambda ordem: ordem.preco_limite)

        while compras and vendas:
            melhor_compra = compras[0]
            melhor_venda = vendas[0]

            if melhor_compra.preco_limite < melhor_venda.preco_limite:
                break  # Não há mais match possível

            preco_execucao = (
                melhor_compra.preco_limite + melhor_venda.preco_limite
            ) / 2
            qtd_exec = min(melhor_compra.quantidade, melhor_venda.quantidade)

            transacao = Transacao(
                comprador=melhor_compra.agente,
                vendedor=melhor_venda.agente,
                ativo=ativo,
                quantidade=qtd_exec,
                preco_execucao=preco_execucao,
            )
            transacao.executar()

            # Atualiza o preço do ativo no mercado
            mercado.fii.preco_cota = preco_execucao

            # Atualiza quantidades remanescentes
            melhor_compra.quantidade -= qtd_exec
            melhor_venda.quantidade -= qtd_exec

            if melhor_compra.quantidade == 0:
                compras.pop(0)
            if melhor_venda.quantidade == 0:
                vendas.pop(0)
