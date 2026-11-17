import requests
import yaml

API_KEY = "a30b91f2a2448fb06a0a6778f92d2a9db971ca82d8eae4e748ac42cf927c9407"  # Replace with your actual SerpApi key

with open("config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

search_cfg = config["search_config"]
travelers = config["travelers"]
baggage = config["baggage"]
segments = config["segments"]


def matches_flights(option, target_flights):
    if not target_flights:
        return True
    if isinstance(target_flights, str):
        target_flights = [target_flights]
    actual_flights = [f.get("flight_number") for f in option.get("flights", [])]
    return all(tf in actual_flights for tf in target_flights)


total_combined_price = 0
currency = search_cfg.get("currency", "CHF")

for seg in segments:
    params = {
        "engine": search_cfg.get("engine", "google_flights"),
        "api_key": API_KEY,
        "type": seg["type"],  
        "departure_id": seg["departure_id"],
        "arrival_id": seg["arrival_id"],
        "outbound_date": seg["date"],
        "currency": currency,
        "hl": search_cfg.get("hl", "en"),
        "adults": travelers.get("adults", 1),
        "children": travelers.get("children", 0),
        "bags": baggage.get("carry_on_bags", 0),
        "exclude_basic": str(baggage.get("exclude_basic_economy", False)).lower(),
    }

    if seg.get("include_airlines"):
        params["include_airlines"] = seg["include_airlines"]

    res = requests.get("https://serpapi.com/search", params=params).json()
    if "error" in res:
        print(f"[{seg['name']}] API Error: {res['error']}")
        continue

    options = res.get("best_flights", []) + res.get("other_flights", [])
    target = seg.get("target_flight_number")

    print(f"=== {seg['name']} ({seg['date']}) ===")
    matched = False

    for opt in options:
        if matches_flights(opt, target):
            matched = True
            flights = [f.get("flight_number") for f in opt.get("flights", [])]
            price = opt.get("price", 0)
            total_combined_price += price

            print(f"  Flights: {' -> '.join(flights)}")
            print(f"  One-Way Price (5 pax): {price} {currency}")
            print(f"  Baggage/Fare Notes: {opt.get('extensions', [])}")
            print(f"  Google Flights URL: {res.get('search_metadata', {}).get('google_flights_url')}\n")

    if not matched:
        print(f"  No match for {target}. Available flights:")
        for opt in options:
            print("   -", [f.get("flight_number") for f in opt.get("flights", [])], f"({opt.get('price')} {currency})")
        print()

print(f"Sum of Both One-Way Tickets: {total_combined_price} {currency}")
