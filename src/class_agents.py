from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from src.prompt import prefix, suffix
from langchain_groq import ChatGroq
from src.dataframes import df_cabecalho, df_itens

# Instância para carregar o modelo e criar a conexão com a provedora do modelo

llm = ChatGroq(model="llama-3.3-70b-versatile") # deepseek-r1-distill-llama-70b llama-3.1-8b-instant llama-3.3-70b-versatile
# llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)

# Classe para configurar os agentes
class agents:
    agent_cabecalho = create_pandas_dataframe_agent(
            llm=llm,
            df=df_cabecalho,  
            verbose=True,
            allow_dangerous_code=True,
            max_iterations=5,
            agent_type="zero-shot-react-description",
            return_intermediate_steps=False,
            prefix=prefix,
        )
    agent_itens = create_pandas_dataframe_agent(
        llm = llm,
        df= df_itens,
        verbose= True,
        allow_dangerous_code=True,
        max_iterations=5,
        return_intermediate_steps=False,
        prefix=prefix,
    )