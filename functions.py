import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

WF_BASE_URL = os.getenv("WEATHER_FORECAST_URL")
W_BASE_URL = os.getenv("WEATHER_BASE_URL")
W_API_KEY = os.getenv("WEATHER_API_KEY")

def get_weather_today(city: str):
    url=f"{W_BASE_URL}?q={city}&appid={W_API_KEY}&units=metric"
    response = requests.get(url)
    data = response.json()

    print(data['cod'])
    if data['cod'] != 200:
        return "City not found or API Error!"

    return data

def get_weather_forecast(city, date: str | None = None) :
    print(date)
    url = f"{WF_BASE_URL}?q={city}&appid={W_API_KEY}&units=metric"
    response = requests.get(url)
    data = response.json()

    if data['cod'] != "200":
        return "City not found or API Error!"

    for item in data['list']:
        if date in item['dt_txt']:
            return item
    
    return "Specific time slot not found in 5-day range"


EXCHANGE_RATE_API_KEY = os.getenv("EXCHANGE_RATE_API_KEY")
EXCHANGE_RATE_BASE_URL = os.getenv("EXCHANGE_RATE_BASE_URL")

def convert_currency(amount: float, from_currency: str, to_currency: str) :
    try:
        url= f"{EXCHANGE_RATE_BASE_URL}/{EXCHANGE_RATE_API_KEY}/latest/{from_currency.upper()}"
        response = requests.get(url)
        data = response.json()

        print(data)
        if data["result"] != "success":
            return {"error": f"API Error: {data.get('error-type', 'Unknown')}"}

        rates = data['conversion_rates']

        if to_currency.upper() not in rates :
            return {"error": f"Currency '{to_currency}' not supported."}

        rate = rates[to_currency.upper()]
        result = rate * amount 

        return {
            "amount" : amount,
            "from" : from_currency.upper(),
            "to" : to_currency.upper(),
            "rate" : rate,
            "result" : round(result, 2)
        }
    except Exception as e:
        return {"error" : str(e)}



def set_reminder(task: str, date: str, time: str):
    try:
        datetime.strptime(date, "%Y-%m-%d")
        datetime.strptime(time, "%H:%M")

        reminder = {
            "task": task,
            "date": date,
            "time": time,
            "status": "set"
        }
        # TODO: persist this somewhere (DB / calendar API) instead of returning only
        return reminder

    except ValueError as e:
        return {"error": f"Invalid date/time format: {str(e)}"}


RESTAURANT_BASE_URL = os.getenv("RESTAURANT_BASE_URL")
RESTAURANT_API_KEY = os.getenv("RESTAURANT_API_KEY")

def search_restaurant(city: str, cuisine: str | None = None, price_range: str | None = None):
    try:
        url = f"{RESTAURANT_BASE_URL}/search"
        params = {"city": city, "apikey": RESTAURANT_API_KEY}
        if cuisine:
            params["cuisine"] = cuisine
        if price_range:
            params["price_range"] = price_range

        response = requests.get(url, params=params)
        if response.status_code != 200:
            return {"error": f"API returned status {response.status_code}"}

        data = response.json()
        if not data.get("results"):
            return {"error": f"No restaurants found in '{city}'."}

        return {
            "city": city,
            "cuisine": cuisine,
            "price_range": price_range,
            "results": data["results"]
        }

    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
    except ValueError as e:
        return {"error": f"Invalid response from API: {str(e)}"}


MESSAGE_BASE_URL = os.getenv("MESSAGE_BASE_URL")
MESSAGE_API_KEY = os.getenv("MESSAGE_API_KEY")

def send_message(recipient: str, message: str):
    if not recipient or not recipient.strip():
        return {"error": "Recipient cannot be empty."}
    if not message or not message.strip():
        return {"error": "Message cannot be empty."}

    try:
        url = f"{MESSAGE_BASE_URL}/send"
        payload = {"to": recipient, "body": message, "apikey": MESSAGE_API_KEY}
        response = requests.post(url, json=payload)

        if response.status_code != 200:
            return {"error": f"Failed to send message, status {response.status_code}"}

        return {"recipient": recipient, "message": message, "status": "sent"}

    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
