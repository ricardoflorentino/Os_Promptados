import pandas as pd
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
import zipfile
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent, create_csv_agent
from langchain_core.prompts import ChatPromptTemplate
from src.prompt import prompt
import zipfile


base_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(base_dir, 'data', '202401_NFs.zip')

# Forma de carregar as chaves do arquivo .env(Criado para ocultar chaves importantes)
load_dotenv()

with zipfile.ZipFile(file_path, 'r') as zip_ref:
    with zip_ref.open('202401_NFs_Cabecalho.csv') as Cabecalho:
        df_cabecalho = pd.read_csv(Cabecalho)
    with zip_ref.open('202401_NFs_Itens.csv') as Itens:
        df_itens = pd.read_csv(Itens)


# Instância para carregar o modelo e criar a conexão com a provedora do modelo
llm = ChatGroq(model="deepseek-r1-distill-llama-70b") # llama-3.3-70b-versatile


prompt = ChatPromptTemplate.from_template(prompt)

agent_cabecalho = create_pandas_dataframe_agent(
    llm= llm,
    verbose=True,
    df=df_cabecalho,
    allow_dangerous_code=True,
    handle_parsing_errors = True
    # max_iterations=4096,
)

agent_itens = create_pandas_dataframe_agent(
    llm = llm,
    verbose=True,
    df = df_itens,
    allow_dangerous_code=True,
    handle_parsing_errors=True,
)

agent = create_pandas_dataframe_agent(
        llm=llm,
        df=[df_cabecalho, df_itens],  # Lista de DataFrames
        verbose=True,
        allow_dangerous_code=True,
        handle_parsing_errors=True,
        
        prefix="""
        Você tem acesso a dois DataFrames:
        - df[0] ou df_cabecalho: Contém dados do cabeçalho das Notas Fiscais
        - df[1] ou df_itens: Contém dados dos itens das Notas Fiscais
        
        Para acessar os DataFrames use:
        - df[0] para cabeçalho
        - df[1] para itens
        
        Você pode fazer joins, merges e análises cruzadas entre eles.
        """
)
 
chain = (
    prompt
    | agent
    
)

def main():
    # print(df_itens.head())

    # res = agent.invoke("Quantas notas para o COMANDO DA MARINHA")
    print(f"VALOR DAS NOTAS AQUI: R$ {df_cabecalho['VALOR NOTA FISCAL'].sum()}")
    res = chain.invoke("Qual é o valor total de todas as notas fiscais?")
    # print(res)


