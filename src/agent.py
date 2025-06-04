import pandas as pd
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
import zipfile
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent, create_csv_agent
from langchain_core.prompts import ChatPromptTemplate
from src.prompt import prompt_improved, prompt
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

# DIAGNÓSTICO DOS DADOS
print("=== DIAGNÓSTICO DOS DADOS ===")
print(f"Shape do cabeçalho: {df_cabecalho.shape}")
print(f"Shape dos itens: {df_itens.shape}")
print("\nColunas do cabeçalho:")
print(df_cabecalho.columns.tolist())
print("\nColunas dos itens:")
print(df_itens.columns.tolist())

# Verificar se a coluna de valor existe e seu tipo
if 'VALOR NOTA FISCAL' in df_cabecalho.columns:
    print(f"\nTipo da coluna VALOR NOTA FISCAL: {df_cabecalho['VALOR NOTA FISCAL'].dtype}")
    print(f"Valores nulos: {df_cabecalho['VALOR NOTA FISCAL'].isnull().sum()}")
    print(f"Primeiros valores: {df_cabecalho['VALOR NOTA FISCAL'].head()}")
    print(f"Soma total: R$ {df_cabecalho['VALOR NOTA FISCAL'].sum():,.2f}")
else:
    print("\nColuna 'VALOR NOTA FISCAL' não encontrada!")

# Instância para carregar o modelo e criar a conexão com a provedora do modelo
llm = ChatGroq(model="deepseek-r1-distill-llama-70b")

# PROMPT MELHORADO PARA ANÁLISE FINANCEIRA
financial_prompt = ChatPromptTemplate.from_template(prompt)


def main():
    print("\n=== TESTE DIRETO DO PANDAS ===")
    valor_total_pandas = df_cabecalho['VALOR NOTA FISCAL'].sum()
    print(f"Valor total (Pandas direto): R$ {valor_total_pandas:,.2f}")
    print(f"Quantidade de registros: {len(df_cabecalho)}")
    
 
    print("\n=== TESTE COM AGENT CUSTOMIZADO ===")
    try:
        # Agent mais específico para esta tarefa
        agent_cabecalho = create_pandas_dataframe_agent(
            llm=llm,
            df=df_cabecalho,  # Apenas um DataFrame
            verbose=True,
            allow_dangerous_code=True,
            max_iterations=5,
            agent_type="zero-shot-react-description",
            return_intermediate_steps=False
        )
        chain = (
            financial_prompt
            | agent_cabecalho
        )
        
        res_custom = chain.invoke("Me diga o maior e o menor valor das notas fiscais e retorne o resultado formatado em moeda brasileira")
        print("Resultado agent customizado:", res_custom['output'])
        
    except Exception as e:
        print(f"Erro no agent customizado: {e}")
    
    print("\n=== ANÁLISE COMPARATIVA ===")
    print(f"Pandas direto: R$ {valor_total_pandas:,.2f}")
    print(f"Registros totais: {len(df_cabecalho)}")
    print(f"Primeiros 5 valores: {df_cabecalho['VALOR NOTA FISCAL'].head().tolist()}")
    print(f"Últimos 5 valores: {df_cabecalho['VALOR NOTA FISCAL'].tail().tolist()}")
    
    # Verificar se há problema de encoding ou sampling
    print(f"\nEstatísticas da coluna:")
    print(f"Média: R$ {df_cabecalho['VALOR NOTA FISCAL'].mean():,.2f}")
    print(f"Mediana: R$ {df_cabecalho['VALOR NOTA FISCAL'].median():,.2f}")
    print(f"Mínimo: R$ {df_cabecalho['VALOR NOTA FISCAL'].min():,.2f}")
    print(f"Máximo: R$ {df_cabecalho['VALOR NOTA FISCAL'].max():,.2f}")

