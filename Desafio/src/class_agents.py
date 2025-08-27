from dotenv import load_dotenv
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI
from src.prompt import prefix_cabecalho, prefix_itens
from langchain_groq import ChatGroq
from src.dataframes import df_cabecalho, df_itens
# Instância para carregar o modelo e criar a conexão com a provedora do modelo
load_dotenv()

llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

# Classe para configurar os agentes
class agents:
    agent_cabecalho = create_pandas_dataframe_agent(
            llm=llm,
            df=df_cabecalho,  
            verbose=True,
            allow_dangerous_code=True,
            max_iterations=5,
            return_intermediate_steps=True,
            prefix=prefix_cabecalho,
        )
    agent_itens = create_pandas_dataframe_agent(
        llm = llm,
        df= df_itens,
        verbose= True,
        allow_dangerous_code=True,
        max_iterations=5,
        return_intermediate_steps=True,
        prefix=prefix_itens,
    )