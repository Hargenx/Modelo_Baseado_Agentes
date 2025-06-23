import numpy as np
import pandas as pd
from scipy.stats import truncnorm


def calcular_media_movel_tecnica(precos_historicos, lf, tipo_media, params_media):
    if not isinstance(precos_historicos, np.ndarray):
        precos_historicos = np.array(precos_historicos)

    if len(precos_historicos) == 0:
        return 0.0, 0.0

    dias_uteis_ano = params_media.get("dias_uteis_ano", 252)
    janela_curta_divisor = params_media.get("janela_curta_divisor", 4)

    omega = int(lf * dias_uteis_ano)
    if omega < 2:
        omega = 2

    janela_curta = max(2, int(omega / janela_curta_divisor))

    if tipo_media == "sma":
        media_curta = (
            np.mean(precos_historicos[-janela_curta:])
            if len(precos_historicos) >= janela_curta
            else precos_historicos[-1]
        )
        media_longa = (
            np.mean(precos_historicos[-omega:])
            if len(precos_historicos) >= omega
            else precos_historicos[-1]
        )
    else:
        serie_precos = pd.Series(precos_historicos[-omega:])
        if len(serie_precos) < 2:
            return precos_historicos[-1], precos_historicos[-1]
        alpha_short = 2 / (janela_curta + 1)
        alpha_long = 2 / (omega + 1)
        media_curta = serie_precos.ewm(alpha=alpha_short, adjust=False).mean().iloc[-1]
        media_longa = serie_precos.ewm(alpha=alpha_long, adjust=False).mean().iloc[-1]

    return media_curta, media_longa


def gerar_literacia_financeira(media, desvio, minimo, maximo):
    a, b = (minimo - media) / desvio, (maximo - media) / desvio
    return truncnorm.rvs(a, b, loc=float(media), scale=float(desvio))


def calcular_sentimento_medio(investidores: list) -> float:
    if not investidores:
        return 0.0
    sentimentos = np.array([investidor.sentimento for investidor in investidores])
    return np.mean(sentimentos)
