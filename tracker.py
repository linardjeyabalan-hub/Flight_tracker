import yaml
import sqlite3
from datetime import datetime


class GoogleFlightsProvider:

    def get_price(self, option):
        return 999


def load_config():

    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)


def save_price(option_name, price):

    conn = sqlite3.connect("prices.db")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            timestamp TEXT,
            option_name TEXT,
            price REAL
        )
    """)

    conn.execute(
        """
        INSERT INTO prices
        VALUES (?, ?, ?)
        """,
        (
            datetime.now().isoformat(),
            option_name,
            price
        )
    )

    conn.commit()
    conn.close()


def main():

    config = load_config()

    provider = GoogleFlightsProvider()

    for option in config["segments"]:

        print(f"Processing {option['name']}")

        price = provider.get_price(option)

        save_price(
            option["name"],
            price
        )


if __name__ == "__main__":
    main()