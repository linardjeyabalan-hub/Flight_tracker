from datetime import datetime
import json
import logging
import os
import sqlite3
import requests
import yaml

# Configure logging to write exclusively to execution.log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("execution.log", mode="a", encoding="utf-8")
    ],
)


class GoogleFlightsProvider:

    def __init__(self, api_key, config):
        self.api_key = api_key
        self.search_cfg = config.get("search_config", {})
        self.travelers = config.get("travelers", {})
        self.baggage = config.get("baggage", {})

    def _matches_flights(self, flight_option, target_flights):
        if not target_flights:
            return True
        if isinstance(target_flights, str):
            target_flights = [target_flights]
        actual_flights = [
            f.get("flight_number") for f in flight_option.get("flights", [])
        ]
        return all(tf in actual_flights for tf in target_flights)

    def _base_params(self, option):
        params = {
            "engine": self.search_cfg.get("engine", "google_flights"),
            "api_key": self.api_key,
            "type": option.get("type", 2),
            "currency": self.search_cfg.get("currency", "CHF"),
            "hl": self.search_cfg.get("hl", "en"),
            "adults": self.travelers.get("adults", 1),
            "children": self.travelers.get("children", 0),
            "bags": self.baggage.get("carry_on_bags", 0),
            "exclude_basic": str(
                self.baggage.get("exclude_basic_economy", False)
            ).lower(),
        }
        if option.get("include_airlines"):
            params["include_airlines"] = option["include_airlines"]
        return params

    def get_flight_data(self, option):
        search_type = option.get("type", 2)
        params = self._base_params(option)

        # --- MULTI-CITY (type: 3) ---
        if search_type == 3:
            legs = option.get("legs", [])
            params["multi_city_json"] = json.dumps([
                {
                    "departure_id": leg["departure_id"],
                    "arrival_id": leg["arrival_id"],
                    "date": leg["date"],
                }
                for leg in legs
            ])

            res1 = requests.get("https://serpapi.com/search", params=params).json()
            if "error" in res1:
                logging.error(f"API Error for {option['name']} (Leg 1): {res1['error']}")
                return None

            options1 = res1.get("best_flights", []) + res1.get("other_flights", [])
            for opt1 in options1:
                if self._matches_flights(opt1, legs[0].get("target_flight_number")):
                    token = opt1.get("departure_token")
                    flights1 = [f.get("flight_number", "") for f in opt1.get("flights", [])]

                    params2 = params.copy()
                    params2["departure_token"] = token
                    res2 = requests.get("https://serpapi.com/search", params=params2).json()
                    if "error" in res2:
                        logging.error(f"API Error for {option['name']} (Leg 2): {res2['error']}")
                        return None

                    google_url = res2.get("search_metadata", {}).get("google_flights_url")
                    options2 = res2.get("best_flights", []) + res2.get("other_flights", [])
                    for opt2 in options2:
                        if self._matches_flights(opt2, legs[1].get("target_flight_number")):
                            flights2 = [f.get("flight_number", "") for f in opt2.get("flights", [])]
                            return {
                                "price": opt2.get("price"),
                                "flights": " -> ".join(flights1 + flights2),
                                "url": google_url,
                            }

            logging.warning(f"No matching multi-city flight found for {option['name']}")
            return None

        # --- ONE-WAY (type: 2) OR ROUND-TRIP (type: 1) ---
        params["departure_id"] = option["departure_id"]
        params["arrival_id"] = option["arrival_id"]
        params["outbound_date"] = option["date"]
        if search_type == 1 and option.get("date_back"):
            params["return_date"] = option["date_back"]

        res = requests.get("https://serpapi.com/search", params=params).json()
        if "error" in res:
            logging.error(f"API Error for {option['name']}: {res['error']}")
            return None

        google_url = res.get("search_metadata", {}).get("google_flights_url")
        all_options = res.get("best_flights", []) + res.get("other_flights", [])
        for flight_opt in all_options:
            if self._matches_flights(flight_opt, option.get("target_flight_number")):
                matched_numbers = " -> ".join(
                    f.get("flight_number", "") for f in flight_opt.get("flights", [])
                )
                return {
                    "price": flight_opt.get("price"),
                    "flights": matched_numbers,
                    "url": google_url,
                }

        logging.warning(f"No matching flight found for {option['name']}")
        return None


def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def init_db():
    conn = sqlite3.connect("prices.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            run_id TEXT,
            timestamp TEXT,
            option_name TEXT,
            flights TEXT,
            price REAL,
            google_flights_url TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_price(run_id, option_name, flight_data):
    if not flight_data or flight_data.get("price") is None:
        logging.warning(f"Skipping DB insert for {option_name} (no data found).")
        return

    conn = sqlite3.connect("prices.db")
    conn.execute(
        """
        INSERT INTO prices (run_id, timestamp, option_name, flights, price, google_flights_url)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            datetime.now().isoformat(),
            option_name,
            flight_data["flights"],
            flight_data["price"],
            flight_data["url"],
        ),
    )
    conn.commit()
    conn.close()


def main():
    api_key = os.environ.get("SERPAPI_KEY", "a30b91f2a2448fb06a0a6778f92d2a9db971ca82d8eae4e748ac42cf927c9407")
    config = load_config()
    currency = config.get("search_config", {}).get("currency", "CHF")

    init_db()
    provider = GoogleFlightsProvider(api_key, config)

    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    logging.info(f"=== Starting flight tracker run ({run_id}) ===")

    one_way_total = 0

    for option in config["segments"]:
        logging.info(f"Processing {option['name']}...")
        flight_data = provider.get_flight_data(option)

        if flight_data:
            if option.get("type", 2) == 2:
                one_way_total += flight_data["price"]

            logging.info(f"  Flights: {flight_data['flights']}")
            logging.info(f"  Price:   {flight_data['price']} {currency}")
            logging.info(f"  URL:     {flight_data['url']}")
            save_price(run_id, option["name"], flight_data)

    logging.info(f"Sum of One-Way Tickets ({run_id}): {one_way_total} {currency}")
    logging.info(f"=== Finished run ({run_id}) ===\n")


if __name__ == "__main__":
    main()
