import numpy as np


class BancoCentral:
    def __init__(self, params: dict):
        self.taxa_selic = params.get("taxa_selic", 0.15)
        self.expectativa_inflacao = params.get("expectativa_inflacao", 0.07)
        self.premio_risco = params.get("premio_risco", 0.08)


class Midia:
    def __init__(self, params: dict):
        self.dias = params.get("num_dias", 252)
        self.valor_atual = params.get("valor_inicial", 0)
        self.sigma = params.get("sigma", 0.1)
        self.valores_fixos = {
            int(k): v for k, v in params.get("valores_fixos", {}).items()
        }
        self.t = 0
        self.historico = [self.valor_atual]

    def gerar_noticia(self):
        if self.t >= self.dias:
            raise StopIteration("Fim da simulação de notícias.")
        self.t += 1
        if self.t in self.valores_fixos:
            self.valor_atual = self.valores_fixos[self.t]
        else:
            passo = np.random.normal(0, self.sigma)
            self.valor_atual = np.clip(self.valor_atual + passo, -3, 3)
        self.historico.append(self.valor_atual)
        return self.valor_atual
