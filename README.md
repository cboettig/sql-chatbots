# sql-chatbots

Exploring SQL construction using LLMs

## Installation

Install python dependencies

```
pip install -r requirements.txt
```

- Install `ollama` , run `ollama serve`.
- Download models with `ollama`: 

```
ollama pull duckdb-nsql
ollama pull llama2:70b
ollama pull gemma
ollama pull zephyr
ollama pull sqlcoder
ollama pull codegemma
```

(Choose whatever subset you like, `duckdb-nsql` seems to works best here.)

If you want to use OpenAI models, add the API key as a streamlit secret.  

Comment out models you don't want in the `app.py` st.radio selector.  

## Database setup

provide a duckdb database file or alter the app.py to read directly from parquet etc.

## Run app

```bash
streamlit run app.py
```

![](![screenshot of app](img/screenshot.png))