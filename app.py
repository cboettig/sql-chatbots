# This example does not use a langchain agent, 
# The langchain sql chain has knowledge of the database, but doesn't interact with it becond intialization.
# The output of the sql chain is parsed seperately and passed to `duckdb.sql()` by streamlit

import os
os.environ["WEBSOCKET_TIMEOUT_MS"] = "300000" # no effect

import streamlit as st
import geopandas as gpd
from shapely import wkb
import leafmap.foliumap as leafmap

import pydeck as pdk
def deck_map(gdf):
    st.write(
        pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v9",
            initial_view_state={
                "latitude": 35,
                "longitude": -100,
                "zoom": 3,
                "pitch": 50,
            },
            layers=[
                pdk.Layer(
                    "GeoJsonLayer",
                    gdf,
                    pickable=True,
                    stroked=True,
                    filled=True,
                    extruded=True,
                    elevation_scale=10,
                    get_fill_color=[2, 200, 100],
                    get_line_color=[0,0,0],
                    line_width_min_pixels=0,
                ),
            ],
        )
    )

def leaf_map(gdf):
    m = leafmap.Map(center=[35, -100], zoom=4, layers_control=True)
    m.add_gdf(gdf)
    return m.to_streamlit()


@st.cache_data
def query_database(response):
    return con.sql(response).to_pandas().head(25)

@st.cache_data
def get_geom(tbl):
    tbl['geometry'] = tbl['geometry'].apply(wkb.loads)
    gdf = gpd.GeoDataFrame(tbl, geometry='geometry')
    return gdf


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
            tbl = query_database(response)
            if 'geometry' in tbl:
                gdf = get_geom(tbl)
                leaf_map(gdf)
                n = len(gdf)
                st.write(f"matching features: {n}")
            st.dataframe(tbl)



# duckdb_sql fails but chatgpt3.5 succeeds with a query like:
# use the st_area function and st_GeomFromWKB functions to compute the area of the Shape column in the fee table, and then use that to compute the total area under each GAP_Sts category

# For most queries, duckdb_sql does much better than alternative open models though

# Federal agencies are identified as 'FED' in the Mang_Type column in the 'combined' data table. The Mang_Name column indicates the different agencies. Which federal agencies manage the greatest area of GAP_Sts 1 or 2 land?

# Federal agencies are identified as 'FED' in the Mang_Type column in the table named "fee". The Mang_Name column indicates the different agencies. List which managers manage the largest total areas that identified as GAP_Sts '1' or '2' ?