# **Modelo de Simulação de Mercado de FIIs (ABM)**

[](https://opensource.org/licenses/MIT)

## **Resumo**

Este repositório contém um **Modelo Baseado em Agentes (ABM)** para simular a dinâmica de preços e o comportamento dos investidores em um mercado de Fundos de Investimento Imobiliário (FIIs). O modelo incorpora uma microestrutura de mercado com um **livro de ordens (Order Book)**, agentes heterogêneos com diferentes estratégias (fundamentalista, grafista e ruído) e a influência de fatores externos como notícias da mídia e políticas do Banco Central.

O projeto foi estruturado para ser altamente configurável, permitindo que todos os parâmetros numéricos sejam ajustados através de um único arquivo de configuração, facilitando a execução de múltiplos cenários e experimentos.

## **Principais Características**

- **Modelo Baseado em Agentes:** Simula o comportamento individual de investidores com diferentes níveis de literacia financeira e estratégias.
- **Microestrutura de Mercado:** Utiliza um livro de ordens para casar ordens de compra e venda, determinando o preço de forma endógena.
- **Agentes Heterogêneos:** O processo de decisão de cada agente combina análise fundamentalista, grafista (usando médias móveis) e um componente de ruído.
- **Ambiente Dinâmico:** Fatores como notícias da mídia e políticas macroeconômicas (taxa SELIC, inflação) influenciam o sentimento e as expectativas dos agentes.
- **Alta Configurabilidade:** Todos os parâmetros do modelo, desde o número de agentes até os coeficientes de comportamento, são controlados via `config/parametros.json`.
- **Performance:** Utiliza paralelismo (`multiprocessing`) para otimizar o processamento diário dos agentes em simulações com grande número de participantes.
- **Análise de Resultados:** Gera gráficos da evolução de preços e volatilidade, e retorna um resumo dos principais resultados da simulação.

## **Estrutura do Projeto**

O projeto está organizado na seguinte estrutura de diretórios e arquivos:

```git
/ABM_FII_Projeto/
├── config/
│   └── parametros.json              # Arquivo de configuração central com todos os parâmetros
├── results/
│   └── plots/                       # Diretório para salvar os gráficos gerados
├── src/
│   ├── market_components.py         # Classes de microestrutura: Ordem, Transacao, OrderBook
│   ├── financial_instruments.py     # Classes de ativos: Imovel, FII
│   ├── economic_agents.py           # Classe principal: Agente
│   ├── market_environment.py        # Classes de ambiente: BancoCentral, Midia, Mercado
│   ├── utils.py                     # Funções auxiliares (médias móveis, geração de LF, etc.)
│   └── simulation_runner.py         # Orquestrador da lógica de simulação
├── main.py                          # Ponto de entrada principal para executar a simulação
└── requirements.txt                 # Lista de dependências do Python
```

## **Instalação e Execução**

### **Pré-requisitos**

- Python 3.8 ou superior

### **Passos**

1. **Clonar o Repositório**

    ```bash
    git clone <URL_DO_SEU_REPOSITORIO>
    cd ABM_FII_Projeto
    ```

2. **Instalar as Dependências**
    Crie um ambiente virtual (recomendado) e instale as bibliotecas necessárias.

    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

3. **Configurar a Simulação**
    Abra o arquivo `config/parametros.json`. Este é o painel de controle da sua simulação. Você pode ajustar qualquer valor para criar diferentes cenários experimentais.

    Por exemplo, para aumentar a propensão dos agentes a negociar, você pode aumentar o `piso_prob_negociar`:

    ```json
    "agente": {
        "params": {
            "piso_prob_negociar": 0.5, // Aumentado de 0.3 para 0.5
            // ... outros parâmetros
        }
    }
    ```

4. **Executar a Simulação**
    Para rodar uma única simulação com os parâmetros definidos no arquivo JSON, execute o script principal:

    ```bash
    python main.py
    ```

    O progresso da simulação será exibido no terminal.

5. **Verificar os Resultados**

      - Um resumo dos resultados será impresso no terminal ao final da execução.
      - Os gráficos gerados serão salvos automaticamente na pasta `results/plots/`.

## **Componentes do Modelo**

- **`Agente`**: O núcleo do modelo. Cada agente possui um nível de literacia financeira (LF), expectativas e um sentimento que guia suas decisões de compra e venda.
- **`FII` e `Imovel`**: Representam o ativo negociado e seus lastros imobiliários, que geram fluxo de caixa e dividendos.
- **`OrderBook`**: Implementa o mecanismo de mercado, recebendo ordens dos agentes e executando transações quando os preços de compra e venda se cruzam.
- **`Mercado`**: A classe orquestradora que gerencia o tempo (dias de simulação), coordena as ações dos agentes, a distribuição de dividendos e a execução do livro de ordens.
- **`BancoCentral` e `Midia`**: Simulam o ambiente externo, fornecendo choques macroeconômicos e de informação que afetam o comportamento dos agentes.

## **Executando Cenários e Experimentos**

Este projeto foi desenhado para facilitar a experimentação. Para rodar múltiplos cenários e criar um log de trabalho (como em uma planilha), você pode adaptar o `main.py` para:

1. Ler um arquivo CSV ou Excel com uma lista de parâmetros para cada linha (cada linha sendo um cenário).
2. Iterar sobre cada linha da planilha.
3. Para cada cenário, modificar o dicionário de parâmetros `sim_params`.
4. Chamar a função `run_single_simulation` com os parâmetros do cenário atual e um `run_id` único.
5. Coletar os resultados retornados e escrevê-los de volta na sua planilha, criando um log completo de todas as execuções.

## **Licença**

Este projeto está licenciado sob a Licença MIT. Veja o arquivo `LICENSE` para mais detalhes.
