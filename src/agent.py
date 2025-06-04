import pandas as pd
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
import zipfile

base_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(base_dir, 'data', '202401_NFs_Cabecalho.csv')

# Forma de carregar as chaves do arquivo .env(Criado para ocultar chaves importantes)
load_dotenv()



# Instância para carregar o modelo e criar a conexão com a provedora do modelo
llm = ChatGroq(model="llama3-70b-8192")

df = pd.read_csv(file_path)
print(df)

