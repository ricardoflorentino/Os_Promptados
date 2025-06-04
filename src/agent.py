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
        df = pd.read_csv(Cabecalho)


# Instância para carregar o modelo e criar a conexão com a provedora do modelo
llm = ChatGroq(model="deepseek-r1-distill-llama-70b") # llama-3.3-70b-versatile

# print(df.head())

prompt = ChatPromptTemplate.from_template(prompt)

agent = create_pandas_dataframe_agent(
    llm= llm,
    verbose=True,
    df=df,
    allow_dangerous_code=True,
    # max_iterations=4096,
)

chain = (
    prompt
    | agent
    
)

def main():
    # res = agent.invoke("Quantas notas para o COMANDO DA MARINHA")
    res = chain.invoke("Quantas notas emitidas em 2024-01-05")
    print(res)


