from datetime import datetime
import sqlite3
import requests
import yaml


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

    def get_flight_data(self, option):
        params = {
            "engine": self.search_cfg.get("engine", "google_flights"),
            "api_key": self.api_key,
            "type": option.get("type", 2),  # Reads type per segment from config.yaml
            "departure_id": option["departure_id"],
            "arrival_id": option["arrival_id"],
            "outbound_date": option["date"],
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

        response = requests.get("https://serpapi.com/search", params=params)
        data = response.json()

        if "error" in data:
            print(f"API Error for {option['name']}: {data['error']}")
            return None
        
        google_url = data.get("search_metadata", {}).get("google_flights_url")
        all_options = data.get("best_flights", []) + data.get(
            "other_flights", []
        )
        target_flights = option.get("target_flight_number")

        for flight_opt in all_options:
            if self._matches_flights(flight_opt, target_flights):
                matched_numbers = " -> ".join(
                    f.get("flight_number", "")
                    for f in flight_opt.get("flights", [])
                )
                return {
                    "price": flight_opt.get("price"),
                    "flights": matched_numbers,
                    "url": google_url,
                }

        print(f"No matching flight found for {option['name']}")
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
        print(f"Skipping DB insert for {option_name} (no data found).")
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
    api_key = "a30b91f2a2448fb06a0a6778f92d2a9db971ca82d8eae4e748ac42cf927c9407"  # Replace with your SerpApi key
    config = load_config()
    currency = config.get("search_config", {}).get("currency", "CHF")

    init_db()
    provider = GoogleFlightsProvider(api_key, config)

    # Shared run_id links both segments from the same execution
    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    total_trip_price = 0

    for option in config["segments"]:
        print(f"Processing {option['name']}...")
        flight_data = provider.get_flight_data(option)

        if flight_data:
            total_trip_price += flight_data["price"]
            print(f"  -> Flights: {flight_data['flights']}")
            print(f"  -> Price:   {flight_data['price']} {currency}")
            print(f"  -> URL:     {flight_data['url']}")
            save_price(run_id, option["name"], flight_data)

    print(f"\nCombined Trip Total ({run_id}): {total_trip_price} {currency}")


if __name__ == "__main__":
    main()
