import shopify
import json
import sqlite3
from pyVinted import Vinted
import re
import os
import time
import logging
from datetime import datetime
log_filename = datetime.now().strftime("log_%Y-%m-%d_%H-%M-%S.txt")

API_KEY = os.getenv("SHOPIFY_API_KEY")  # Pobranie klucza API z GitHub Secrets

# Konfiguracja logowania
# Update the logging configuration to support UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),  # Ensure UTF-8 encoding
        logging.StreamHandler()
    ]
)

log_handler = TimedRotatingFileHandler("server.log", when="midnight", interval=1, backupCount=7, encoding='utf-8')
log_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

logging.getLogger().addHandler(log_handler)


ses = shopify.Session('619d0b.myshopify.com', '2025-01', API_KEY)
shopify.ShopifyResource.activate_session(ses)
client = shopify.GraphQL()

# Function to adjust inventory
def adjust_inventory(inventory_item_id):
    graphql_query_correct = f"""
    mutation AdjustInventoryQuantities {{
        inventoryAdjustQuantities(input: {{
            reason: "correction",
            name: "available",
            changes: [
                {{
                    delta: -1,
                    inventoryItemId: "gid://shopify/InventoryItem/{inventory_item_id}",
                    locationId: "gid://shopify/Location/84567228746"
                }}
            ]
        }}) {{
            userErrors {{
                field
                message
            }}
            inventoryAdjustmentGroup {{
                createdAt
                reason
                referenceDocumentUri
                changes {{
                    name
                    delta
                }}
            }}
        }}
    }}
    """
    response = client.execute(graphql_query_correct)
    return response



def process_vinted_data():
    vinted = Vinted()
    items = vinted.items.search("https://www.vinted.pl/catalog?search_text=sneakilystore&time=1741101864", 100, 1)

    # Connect to SQLite database
    conn = sqlite3.connect("shopify_data.db")
    cursor = conn.cursor()

    # Create table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listings_vinted (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_produktu INTEGER UNIQUE
        )
    ''')

    # Fetch existing listings from database
    cursor.execute('SELECT id_produktu FROM listings_vinted')
    existing_listings = [row[0] for row in cursor.fetchall()]
    logging.info("Existing listings")
    logging.info(existing_listings)
    # Process new Vinted items
    actual_listings = []
    for item in items:
        match = re.search(r"Buty Sportowe\s*(?:[#S])?(\d+)", item.title)
        if match:
            id_produktu = match.group(1)
            actual_listings.append(id_produktu)
            if id_produktu not in existing_listings:
            # Add new items to database if not already present
                cursor.execute('''INSERT INTO listings_vinted (id_produktu) VALUES (?)''', (id_produktu,))
    conn.commit()
    # Identify missing products
    logging.info("Actual listings")
    logging.info(actual_listings)
    change_list = [id_produktu for id_produktu in existing_listings if id_produktu not in actual_listings]
    if change_list:
        for id_produktu in change_list:
            # Get inventory_item_id from listings_shopify
            cursor.execute('SELECT inventory_item_id FROM listings_shopify WHERE id_produktu = ?', (id_produktu,))
            inventory_item_id = cursor.fetchone()

            if inventory_item_id:
                response = adjust_inventory(inventory_item_id[0])

                if 'errors' not in response:
                    logging.info(f" Inventory corrected for product ID: {id_produktu}.")
                    cursor.execute('DELETE FROM listings_vinted WHERE id_produktu = ?', (id_produktu,))
                    logging.info(f" Removed from listings_vinted: {id_produktu}")
                else:
                    logging.error(f" Failed to adjust inventory for product ID: {id_produktu}. Error: {response['errors']}")
            else:
                logging.error(f" Inventory item not found for product ID: {id_produktu}.")

    else:
        logging.info(" No changes detected in Vinted listings.")

    # Commit and close database connection
    conn.commit()
    conn.close()

def process_shopify_data():
    conn = sqlite3.connect("shopify_data.db")  # Tworzy lub otwiera bazę
    cursor = conn.cursor()  # Tworzy obiekt kursora do zapytań SQL
    #other methods
    # graphql_query_correct = """
    # mutation AdjustInventoryQuantities {
    #   inventoryAdjustQuantities(input: {
    #     reason: "correction",
    #     name: "available",
    #     changes: [
    #       {
    #         delta: -1,
    #         inventoryItemId: "gid://shopify/InventoryItem/52337327472970",
    #         locationId: "gid://shopify/Location/84567228746"
    #       }
    #     ]
    #   }) {
    #     userErrors {
    #       field
    #       message
    #     }
    #     inventoryAdjustmentGroup {
    #       createdAt
    #       reason
    #       referenceDocumentUri
    #       changes {
    #         name
    #         delta
    #       }
    #     }
    #   }
    # }
    # """
    # graphql_query_sel = """
    # query GetAllInventoryItemIds {
    #   inventoryItems(first: 50) {
    #     edges {
    #       node {
    #         id
    #       }
    #     }
    #     pageInfo {
    #       hasNextPage
    #       endCursor
    #     }
    #   }
    # }
    # """
    # data = client.execute("""mutation inventoryAdjustQuantities($input: InventoryAdjustQuantitiesInput!) {
    #       inventoryAdjustQuantities(input: $input) {
    #         userErrors {
    #           field
    #           message
    #         }
    #         inventoryAdjustmentGroup {
    #           createdAt
    #           reason
    #           changes {
    #             name
    #             delta
    #           }
    #         }
    #       }
    #     }""", """"input": {
    #         "reason": "correction",
    #         "name": "available",
    #         "changes": [
    #           {
    #             "delta": -1,
    #             "inventoryItemId": "gid://shopify/InventoryItem/9633991983434",
    #             "locationId": "gid://shopify/Location/84567228746"
    #           }
    #         ]
    #       }""")
    # graphql_query_loc = """
    # query GetLocations {
    #   locations(first: 10) {
    #     edges {
    #       node {
    #         id
    #         name
    #         address {
    #           formatted
    #         }
    #       }
    #     }
    #     pageInfo {
    #       hasNextPage
    #       endCursor
    #     }
    #   }
    # }
    # """
    graphql_query_met = """
    query GetProductsWithInventoryAndMetafield {
      products(first: 250, query: "metafield:custom.id_product:*") {
        edges {
          node {
            id
            title
            metafield(namespace: "custom", key: "id_product") {
              value
            }
            variants(first: 10) {
              edges {
                node {
                  inventoryItem {
                    id
                  }
                }
              }
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """
    dd = client.execute(graphql_query_met)
    logging.info(dd)
    data = json.loads(dd)  # Parsowanie odpowiedzi JSON

    # Połączenie z bazą SQLite
    # Tworzenie tabeli listings_shopify (jeśli jeszcze nie istnieje)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listings_shopify (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_produktu TEXT,
            inventory_item_id TEXT
        )
    ''')

    # Tworzenie tabeli listings_vinted (jeśli jeszcze nie istnieje)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listings_vinted (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_produktu TEXT
        )
    ''')
    # Wstawianie danych do bazy
    for product in data["data"]["products"]["edges"]:
        node = product["node"]
        metafield = node["metafield"]["value"] if node.get("metafield") else None

        for variant in node["variants"]["edges"]:
            inventory_id = variant["node"]["inventoryItem"]["id"].split("/")[-1]

            # Sprawdzanie, czy inventory_item_id już istnieje w bazie
            cursor.execute('''SELECT 1 FROM listings_shopify WHERE inventory_item_id = ? LIMIT 1''', (inventory_id,))
            if cursor.fetchone():
                continue  # Jeśli przedmiot już istnieje, przejdź do następnego

            cursor.execute('''
                  INSERT INTO listings_shopify (id_produktu, inventory_item_id)
                  VALUES (?, ?)
              ''', (metafield, inventory_id))

        # Zapisanie zmian w bazie
    conn.commit()
    conn.close()
    logging.info("Dane z shopify zostały zapisane w bazie.")



def run_periodically():
    while True:
        logging.info("Przetwarzanie danych Shopify...")
        process_shopify_data()
        logging.info("Przetwarzanie danych Vinted...")
        process_vinted_data()
        logging.info("Czekam 5 minut przed kolejnym cyklem...")
        time.sleep(90)  # Czekaj 5 minut (300 sekund)

    # Uruchomienie cyklicznego procesu


run_periodically()
