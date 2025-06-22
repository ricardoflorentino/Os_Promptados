# Os Promptados

Um projeto Python que utiliza agentes para processamento e análise de dados.

## Requisitos

- Python 3.x
- Dependências listadas em `requirements.txt`

## Instalação

1. Clone o repositório:

```bash
git clone https://github.com/ricardoflorentino/Os_Promptados.git
cd Os_Promptados
```

2. Crie um ambiente virtual (recomendado):

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate  # Windows
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

## Como configurar a Open AI Key

Crie um arquivo chamado .env no diretório e adicione por ex:

OPENAI_API_KEY=SUA_KEY_AQUI

## Como Executar

Para executar o projeto, use o comando:

```bash
streamlit run run.py
```

## Estrutura do Projeto

```
Os_Promptados/
├── src/
│   ├── agent.py         # Implementação dos agentes
│   ├── app.py          # Aplicação principal
│   ├── class_agents.py # Definições de classes dos agentes
│   ├── dataframes.py   # Manipulação de dados
│   ├── prompt.py       # Lógica de prompts
│   └── data/          # Diretório de dados
├── requirements.txt    # Dependências do projeto
└── run.py             # Ponto de entrada da aplicação
```

## Testando o Projeto

1. Certifique-se de que todas as dependências estão instaladas
2. Execute o arquivo principal:

```bash
streamlit run run.py
```

## Dependências Principais

- langchain==0.3.25
- numpy==2.2.6
- pandas==2.2.3
- python-dateutil==2.9.0.post0
- pytz==2025.2
- six==1.17.0
- tzdata==2025.2

## Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request
