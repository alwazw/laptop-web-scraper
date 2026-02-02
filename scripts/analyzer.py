import sqlite3
from datetime import datetime

def generate_reports():
    print('\n=== Laptop Arbitrage Analysis Reports ===')
    print(f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

    # Connect to database
    try:
        from pathlib import Path
        db_path = str(Path(__file__).resolve().parents[1] / 'data' / 'arbitrage.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get component averages
        cursor.execute('SELECT * FROM component_daily_avg')
        avg_prices = cursor.fetchall()

        print('\n--- Component Daily Averages ---')
        if avg_prices:
            for row in avg_prices:
                # Assuming index 2 is name and 3 is price based on your snippet
                print(f'{row[2]}: ${row[3]:.2f}')
        else:
            print('No component averages found.')

        # Get laptop listings
        cursor.execute('SELECT * FROM listings')
        listings = cursor.fetchall()

        print('\n--- Laptop Listings (Top 5) ---')
        if listings:
            for i, row in enumerate(listings[:5], 1):
                # row[4] is title, row[5] is price, row[3] is platform
                print(f'{i}. {row[4][:50]}... - ${row[5]:.2f} ({row[3]})')
        else:
            print('No laptop listings found.')

        # Get products
        cursor.execute('SELECT * FROM products')
        products = cursor.fetchall()

        print('\n--- Products ---')
        if products:
            for i, row in enumerate(products[:5], 1):
                # row[1] Brand, row[2] Model, row[3] Specs
                print(f'{i}. {row[1]} {row[2]} ({row[3]})')
        else:
            print('No products found.')

        conn.close()

    except Exception as e:
        print(f'Error accessing database: {e}')

if __name__ == '__main__':
    generate_reports()