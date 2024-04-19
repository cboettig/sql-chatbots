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

## ChatGPT Connection
from langchain_openai import ChatOpenAI 

# Requires ollama server running locally
from langchain_community.llms import Ollama
## # from langchain_community.llms import ChatOllama

models = {
          "duckdb-nsql": Ollama(model="duckdb-nsql", temperature=0),
          "llama3:70b": Ollama(model="llama2:70b", temperature=0),
          "dbrx": Ollama(model="dbrx", temperature=0),
          "command-r-plus": Ollama(model="command-r-plus", temperature=0),
          "mixtral:8x22b":  Ollama(model="mixtral:8x22b", temperature=0),
          "wizardlm2:8x22b":  Ollama(model="wizardlm2:8x22b", temperature=0),
          "sqlcoder": Ollama(model="sqlcoder", temperature=0),
          "zephyr": Ollama(model="zephyr", temperature=0),
          "gemma:7b": Ollama(model="gemma:7b", temperature=0),
          "codegemma": Ollama(model="codegemma", temperature=0),
#          "chatgpt3.5": ChatOpenAI(model="gpt-3.5-turbo", temperature=0, api_key=st.secrets["OPENAI_API_KEY"]), 
#          "chatgpt4": ChatOpenAI(model="gpt-4", temperature=0, api_key=st.secrets["OPENAI_API_KEY"])
          }

map_tool = {
            "leafmap": leaf_map, 
            "deckgl": deck_map
            }

st.set_page_config(page_title="Protected Areas Database Chat", page_icon="🦜", layout="wide")
st.title("Protected Areas Database Chat")

with st.sidebar:
    choice = st.radio("Select an LLM:", models)
    llm = models[choice]
    map_choice = st.radio("Select mapping tool", map_tool)
    mapper = map_tool[map_choice]

    st.markdown("*Note: switching a large model will take a while to load at first.*")

## A SQL Chain
from langchain.chains import create_sql_query_chain
chain = create_sql_query_chain(llm, db)

main = st.container()
with main:

    '''
    The Protected Areas Database of the United States (PAD-US) is the official national inventory of
    America’s parks and other protected lands, and is published by the USGS Gap Analysis Project,
    [https://doi.org/10.5066/P9Q9LQ4B.](https://doi.org/10.5066/P9Q9LQ4B).  

    This interactive tool allows users to explore the dataset, as well as a range of biodiversity
    and climate indicators associated with each protected area. These indicators are integrated into 
    a single table format shown below.  The chatbot assistant can turn natural language queries into
    SQL queries based on the table schema.

    ##### Example Queries returning summary tables

    - What is the percent area in each gap code as a fraction of the total protected area?
    - The manager_type column indicates whether a manager is federal, state, local, private, or NGO.
      the manager_name column indicates the responsible agency (National Park Service, Bureau of Land Management,
      etc) in the case of federal manager types.  Which of the federal managers manage the most land in
      gap_code 1 or 2, as a fraction of the total area?

    When queries refer to specific managed areas, the chatbot can show those areas on an interactive map.
    Do to software limitations, these maps will show no more than 25 polygons, even if more areas match the
    requested search. The chatbot sometimes requires help identifying the right columns.  In order to create
    a map, the SQL query must also return the geometry column.  Conisder the following examples:

    ##### Example queries returning maps + tables

    - Show me all the national monuments (designation_type) in Utah. Include the geometry column
    - Show examples of Bureau of Land Management (manager_name) with the highest species richness? Include the geometry column
    - Which site has the overall highest range-size-rarity? Include the geometry column, manager_name, and IUCN category.

    '''

    # Super-minimal streamlit interface
    # Should almost surely adjust this to use chatbot state/memory
    chatbox, database = st.columns(2)
    with chatbox:           
        st.markdown("## 🦜 Chatbot:")
        st.markdown("Pick a question from above or write your own:")
        if prompt := st.chat_input(key="chain"):
            st.chat_message("user").write(prompt)
            with st.chat_message("assistant"):
                response = chain.invoke({"question": prompt})
                st.write(response)


    with database:
        st.markdown("## 🗄 Database Query:")

        query = st.text_input("paste SQL query here", "select manager_name from pad limit 1")

        # And manually do stuff with the chatbot's SQL code
        tbl = query_database(query)
        if 'geometry' in tbl:
            gdf = get_geom(tbl)
            mapper(gdf)
            n = len(gdf)
            st.write(f"matching features: {n}")
        st.dataframe(tbl)


st.divider()

with st.container():
    st.text("Database schema (top 3 rows)")
    tbl = tbl = query_database("select * from pad limit 3")
    st.dataframe(tbl)

# duckdb_sql fails but chatgpt3.5 succeeds with a query like:
# use the st_area function and st_GeomFromWKB functions to compute the area of the Shape column in the fee table, and then use that to compute the total area under each GAP_Sts category

# For most queries, duckdb_sql does much better than alternative open models though

# Federal agencies are identified as 'FED' in the Mang_Type column in the 'combined' data table. The Mang_Name column indicates the different agencies. Which federal agencies manage the greatest area of GAP_Sts 1 or 2 land?

# Federal agencies are identified as 'FED' in the Mang_Type column in the table named "fee". The Mang_Name column indicates the different agencies. List which managers manage the largest total areas that identified as GAP_Sts '1' or '2' ?