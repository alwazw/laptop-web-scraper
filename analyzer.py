import sqlite3
from datetime import datetime
from contextlib import closing
from data_utils import (
    fetch_latest_listings, get_latest_component_prices, get_historical_baseline,
    calculate_tev, get_connection, log_execution, calculate_triangulated_margin,
    get_historical_avg
)

def run_decision_engine():
    print('\n=== v2.0 Arbitrage Decision Engine ===')

    items_processed = 0
    try:
        listings = fetch_latest_listings()
        latest_components = get_latest_component_prices()

        if listings.empty:
            print('No listings found to evaluate.')
            log_execution('analyzer_v2', 'success', 0, error_message='No listings found')
            return

        with closing(get_connection()) as conn:
            for _, row in listings.iterrows():
                # 1. Historical Baseline & Market Ref
                hist_baseline = get_historical_baseline(row['product_hash'])
                market_ref = get_historical_avg(row['product_hash'], days=30) or hist_baseline or row['listing_price']

                # 2. Triangulated Logic for Dropshipping/Resale
                # Assume potential sell price is the market reference (conservative)
                net_profit, margin_pct, is_unrealistic = calculate_triangulated_margin(
                    buy_price=row['listing_price'],
                    sell_price=market_ref,
                    market_ref_price=market_ref
                )

                # 3. Dual-Valuation Calculation (Intrinsic)
                tev, _, _ = calculate_tev(row, latest_components, hist_baseline)

                # Inventory strategy: Accept if margin > 10% or Net Profit is strong
                status = 'evaluated'
                if margin_pct >= 10.0 and not is_unrealistic:
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
        log_execution('analyzer_v2', 'failure', items_found=items_processed, error_message=str(e))

if __name__ == '__main__':
    run_decision_engine()
