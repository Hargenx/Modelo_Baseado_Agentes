# src/environment_factors.py
import numpy as np


class BancoCentral:
    def __init__(self, parametros: dict):
        self.taxa_selic = parametros.get("taxa_selic", 0.15)
        self.expectativa_inflacao = parametros.get("expectativa_inflacao", 0.07)
        self.premio_risco = parametros.get("premio_risco", 0.08)


class Midia:
    """
    Classe responsável por simular a influência da mídia ao longo dos dias de simulação.
    Pode receber valores fixos ou gerar ruído normalmente distribuído com sigma.
    """

    def __init__(self, parametros: dict):
        self.total_dias = parametros.get("num_dias", 252)
        self.valor_atual = parametros.get("valor_inicial", 0)
        self.sigma = parametros.get("sigma", 0.1)

        # Dicionário com valores fixos da mídia em determinados dias
        self.valores_fixos = {
            int(dia): valor
            for dia, valor in parametros.get("valores_fixos", {}).items()
        }

        self.dia_atual = 0
        self.historico_valores = [self.valor_atual]

    def gerar_noticia(self) -> float:
        if self.dia_atual >= self.total_dias:
            raise StopIteration("Fim da simulação de notícias da mídia.")

        self.dia_atual += 1

        # Se houver valor fixo para o dia, utiliza-o
        if self.dia_atual in self.valores_fixos:
            self.valor_atual = self.valores_fixos[self.dia_atual]
        else:
            variacao = np.random.normal(0, self.sigma)
            self.valor_atual = np.clip(self.valor_atual + variacao, -3, 3)

        self.historico_valores.append(self.valor_atual)
        return self.valor_atual
