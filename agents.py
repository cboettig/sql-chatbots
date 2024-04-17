# This example does not use a langchain agent, 
# The langchain sql chain has knowledge of the database, but doesn't interact with it becond intialization.
# The output of the sql chain is parsed seperately and passed to `duckdb.sql()` by streamlit

import streamlit as st
import leafmap.foliumap as leafmap
import geopandas as gpd
from shapely import wkb

## Database connection
from sqlalchemy import create_engine
from langchain.sql_database import SQLDatabase
db_uri = "duckdb:///pad.duckdb"
engine = create_engine(db_uri, connect_args={'read_only': True})
db = SQLDatabase(engine, view_support=True)

import ibis
con = ibis.connect("duckdb://pad.duckdb", read_only=True)
con.load_extension("spatial")

# alternately using duckdb directly
#import duckdb
#con = duckdb.connect("pad.duckdb", read_only=True)
#con.install_extension("spatial")
#con.load_extension("spatial")

## ChatGPT Connection
from langchain_openai import ChatOpenAI 
chatgpt_llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, api_key=st.secrets["OPENAI_API_KEY"])
chatgpt4_llm = ChatOpenAI(model="gpt-4", temperature=0, api_key=st.secrets["OPENAI_API_KEY"])

# Requires ollama server running locally
from langchain_community.llms import Ollama
## # from langchain_community.llms import ChatOllama

models = {"duckdb-nsql": Ollama(model="duckdb-nsql", temperature=0),
          "sqlcoder": Ollama(model="sqlcoder", temperature=0),
          "zephyr": Ollama(model="zephyr", temperature=0),
          "gemma:7b": Ollama(model="gemma:7b", temperature=0),
          "codegemma": Ollama(model="codegemma", temperature=0),
          "llama2": Ollama(model="llama2", temperature=0),
          "chatgpt3.5": chatgpt_llm, 
          "chatgpt4": chatgpt4_llm}
with st.sidebar:
    choice = st.radio("Select an LLM:", models)
    llm = models[choice]

## A SQL Chain
from langchain.chains import create_sql_query_chain
chain = create_sql_query_chain(llm, db)

main = st.container()

## Does not preserve history
with main:
    if prompt := st.chat_input(key="chain"):
        st.chat_message("user").write(prompt)
        with st.chat_message("assistant"):
            response = chain.invoke({"question": prompt})
            st.write(response)
            tbl = con.sql(response).to_pandas()
            st.dataframe(dt)

# agent works only with open-ai.  needs to be told what table to use
from langchain.agents import create_sql_agent
from langchain_community.callbacks import StreamlitCallbackHandler

# codegemma -- we need different parser to extract the SQL part of the query
agent = create_sql_agent(llm, db=db, verbose=True)
# agent = create_sql_agent(llm, db=db, agent_type="openai-tools", verbose=True)

section = st.container()
if "messages" not in st.session_state:
    st.session_state["messages"] = []

with section:
    if user_query := st.chat_input():
        st.session_state.messages.append({"role": "user", "content": user_query})
        # st.chat_message("user").write(user_query)
        with st.chat_message("assistant"):
            st_cb = StreamlitCallbackHandler(st.container())
            response = agent.run(user_query, callbacks=[st_cb])
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.write(response)



# duckdb_sql fails but chatgpt3.5 succeeds with a query like:
# use the st_area function and st_GeomFromWKB functions to compute the area of the Shape column in the fee table, and then use that to compute the total area under each GAP_Sts category

# For most queries, duckdb_sql does much better than alternative open models though

# Federal agencies are identified as 'FED' in the Mang_Type column in the 'combined' data table. The Mang_Name column indicates the different agencies. Which federal agencies manage the greatest area of GAP_Sts 1 or 2 land?

# Federal agencies are identified as 'FED' in the Mang_Type column in the table named "fee". The Mang_Name column indicates the different agencies. List which managers manage the largest total areas that identified as GAP_Sts '1' or '2' ?