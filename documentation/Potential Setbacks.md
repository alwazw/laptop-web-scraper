# Potential Setbacks

I have refined your idea to make it viable for a developer (or AI Agent) to build immediately.

Here is the strategic refinement before the code generation:

1. **The Anti-Bot Hurdle:** Amazon, Best Buy, and Dell have aggressive anti-scrapers. A simple Python request **will fail**. I have mandated **Playwright with Stealth** or a recommendation for a Scraping API in the README.
2. **The "Upgradeable" Problem:** Product listings rarely say "Ram is soldered."
    - *Logic Adjustment:* I added a heuristic check. If the RAM type is "LPDDR" or "Unified Memory" (Mac), it defaults to `Non-Upgradeable`. Otherwise, for the MVP, we assume upgradeable.
3. **Product Normalization:** Matching "Dell Latitude 5420" across sites is hard.
    - *Logic Adjustment:* I introduced a **Spec-Hash approach** (CPU + Screen Size + Resolution + Generation) to create the `unique_id` dynamically.
4. **Additional Sources:** For Canada, you are missing **Canada Computers** and **Newegg.ca** (crucial for component pricing) and **eBay.ca Refurbished** (often beats Best Buy Open Box).

**Regarding Deep Research:** You do **not** need Deep Research for this. The logic is clear; the challenge is strictly engineering execution. The standard model is perfect for generating this architecture.

Here are the files to give to Agent0.