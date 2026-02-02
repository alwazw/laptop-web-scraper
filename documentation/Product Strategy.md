# Product Strategy

# Product Logic Refinements

## 1. The "Stripped Down" Logic

The original request asked to lookup the "matching today's avg price" if the item is upgradeable.
**Refinement:** We calculate the value of the *included* parts.
*Example:* A Dell Laptop comes with 16GB RAM and is listed for $500.

- We look up the daily cost of 16GB RAM (e.g., $40).
- We look up the daily cost of the SSD (e.g., $50).
- **Stripped Price:** $500 - $40 - $50 = $410.
- **Why:** This tells you the "Base Chassis Cost." If you buy it for $500, strip the parts, and sell the chassis, or if you upgrade it, you know your base entry point.

## 2. RAM/SSD Model Matching

- **Problem:** Listings often say "16GB RAM" but don't specify "DDR4" vs "DDR5".
- **Solution:** The CPU generation is the key.
    - Intel 8th-11th Gen = Assume DDR4.
    - Intel 12th+ / Ultra = Assume DDR5 (mostly).
    - The scraper regex logic must extract the CPU generation to assign the correct RAM price tier.

## 3. Arbitrage Logic

- The "Dropshipping Cost" report logic has been simplified to:
    - `IF (Amazon_Price - BestBuy_Price) > (BestBuy_Price * 1.15 + Shipping)`
    - *1.15 accounts for 15% marketplace fees.*
    - This ensures you don't lose money on fees.

## 4. Sources Added

- **Canada Computers:** Added because they often have aggressive sales on open-box that beat Best Buy.
- **Newegg.ca:** Essential for the RAM/SSD pricing baseline as Amazon prices fluctuate wildly due to third-party sellers.