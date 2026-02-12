import sqlite3
from datetime import datetime
from data_utils import fetch_latest_listings, get_latest_component_prices, get_historical_baseline, calculate_tev, get_connection, log_execution

def run_decision_engine():
    print('\n=== v2.0 Arbitrage Decision Engine ===')

    try:
        listings = fetch_latest_listings()
        latest_components = get_latest_component_prices()

        if listings.empty:
            print('No listings found to evaluate.')
            return

        items_processed = 0
        with get_connection() as conn:
            for _, row in listings.iterrows():
                # 1. Historical Baseline
                hist_baseline = get_historical_baseline(row['product_hash'])

                # 2. Dual-Valuation Calculation
                tev = calculate_tev(row, latest_components, hist_baseline)

                # 3. Strategy Evaluation
                margin = tev - row['listing_price']
                margin_pct = (margin / row['listing_price']) * 100 if row['listing_price'] > 0 else 0

                # Inventory strategy: Accept if margin > 10% and we have high confidence (historical price)
                status = 'evaluated'
                if margin_pct >= 10.0 and hist_baseline:
                    status = 'accepted'

                # 4. Log Decision
                conn.execute('''
                    INSERT INTO arbitrage_decisions (
                        strategy, product_hash, listing_id, chosen_valuation_method,
                        net_margin_pct, confidence_score, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    'inventory', row['product_hash'], row['id'],
                    'chassis' if hist_baseline else 'component',
                    round(margin_pct, 2), 1.0 if hist_baseline else 0.5, status
                ))
                items_processed += 1

            conn.commit()

        log_execution('analyzer_v2', 'success', items_processed)
        print(f'Decision engine processed {items_processed} listings.')

    except Exception as e:
        print(f'Error in decision engine: {e}')
        log_execution('analyzer_v2', 'failure', error_message=str(e))

if __name__ == '__main__':
    run_decision_engine()
