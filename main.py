from langchain.agents import create_agent
from langchain_azure_ai.chat_models import AzureAIChatCompletionsModel
from langchain.tools import tool
import requests
from pydantic import BaseModel
import csv
import sqlite3
import pandas as pd

AZURE_URL = None
AZURE_KEY = None

llm = AzureAIChatCompletionsModel(
    endpoint=AZURE_URL,
    credential=AZURE_KEY,
    model="gpt-oss-120b",
)

df=pd.read_csv("recipes-2.csv")
conn = sqlite3.connect("recipes.db",check_same_thread=False)
df.to_sql("recipes", conn, if_exists="replace", index=False)
conn.execute("ALTER TABLE recipes ADD COLUMN Classification VARCHAR(200)")
# This updates the new column
conn.execute("UPDATE recipes SET Classification = 'Halal' WHERE RecipeIngredientParts NOT LIKE '%pork%'")

def get_ingredients(Name:str)->str:
    """Get the ingredients from given Name"""
    print(f"Getting ingredients for {Name}")
    query=f"""SELECT RecipeIngredientParts FROM recipes WHERE Name LIKE '{Name}%'"""
    resultsIngredients = pd.read_sql_query(query, conn)
    print(resultsIngredients)
    return resultsIngredients

    """Get the 5 foods from df for a given ingredient."""
    # Store DataFrame into SQL table
    print(f"Getting foods for ingredient {ingredient}")
    query = f"""SELECT Name FROM recipes WHERE RecipeIngredientParts LIKE '%{ingredient}%'"""
    result_food = pd.read_sql_query(query, conn)
    print(result_food['Name'].tolist()[:5])
    return result_food['Name'].tolist()[:5]

def getFoodClassify(classify:str)->list:
    """Get 5 food from df base on given classify"""
    print(f"Getting foods for {classify} classify.")
    query=f"""SELECT Name FROM recipes WHERE Classification = '{classify}'"""
    resultsFoodClassify = pd.read_sql_query(query, conn)
    print(resultsFoodClassify)
    return resultsFoodClassify

# Step 1: Define Input Schema
class WeatherInput(BaseModel):
    city: str

# Step 2: Helper to get city coordinates
def city_to_latlon(city):
    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    print(f"city: {city}")
    params = {"name": city, "count": 1}
    resp = requests.get(geo_url, params=params)
    resp.raise_for_status()
    results = resp.json().get("results")
    if not results:
        raise ValueError(f"Could not find coordinates for {city}")
    return results[0]["latitude"], results[0]["longitude"]

@tool
# Step 3: Fetch weather from NOAA NWS API
def get_noaa_weather(city: str) -> str:
    """Get the weather from the NOAA API for a given city in the USA"""
    try:
        lat, lon = city_to_latlon(city)
        print(f"Getting weather for {city}")
        points_url = f"https://api.weather.gov/points/{lat},{lon}"
        points_resp = requests.get(points_url, headers={"User-Agent": "LangChainExample"})
        points_resp.raise_for_status()
        forecast_url = points_resp.json()["properties"]["forecast"]
        forecast_resp = requests.get(forecast_url, headers={"User-Agent": "LangChainExample"})
        forecast_resp.raise_for_status()
        forecast = forecast_resp.json()
        # Get the first forecast period
        periods = forecast["properties"].get("periods")
        if not periods:
            return f"No forecast data for {city}."
        today = periods[0]
        open("weather.csv", "a").write(f"{today}\n")
        return (
            f"Weather for {city}: {today['detailedForecast']} "
            f"({today['temperature']}°{today['temperatureUnit']})"
        )
    except Exception as e:
        print(f"Error getting weather for {city}: {e}")
        return f"Error fetching weather for {city}: {e}"


# agent = create_agent(
#     model=llm,
#     tools=[get_noaa_weather],
#     system_prompt="You are an agent that is specialised in helping the user getting weather information"
# )
#
# result = agent.invoke(
#     {"messages": [{"role": "user", "content": "What is the weather like in Boston ?"}]},
# )
# print(result.get("messages", [])[-1])

agent1 = create_agent(
    model=llm,
    # tools=[getFood, get_ingredients],
    tools=[getFoodClassify],
    system_prompt="You are an agent that is specialised in getting Name information base on Classification"
    # system_prompt="You are an agent that is specialised in helping the user getting Name information base on ingredients"
)

resultFood = agent1.invoke(
    # {"messages": [{"role": "user", "content": "What Name has ingredients milk ? and what are the ingredients ?"}]},
    {"messages": [{"role": "user", "content": "What food is Vegetarian?"}]},
)

print(resultFood.get("messages", [])[-1])