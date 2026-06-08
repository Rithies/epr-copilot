# cost.py — Phase 2 closeout: unit economics (cost per query)

# Claude Sonnet 4.6 pricing, in US dollars PER MILLION tokens.
# Source: Anthropic's pricing page.
INPUT_PRICE_PER_M = 3.00     # $ per 1,000,000 input tokens
OUTPUT_PRICE_PER_M = 15.00   # $ per 1,000,000 output tokens

USD_TO_INR = 95.0            # live-ish rate; update when you like


def query_cost_inr(input_tokens, output_tokens):
    """Return the rupee cost of ONE Claude call, given its token counts."""
    input_cost_usd = (input_tokens / 1_000_000) * INPUT_PRICE_PER_M
    output_cost_usd = (output_tokens / 1_000_000) * OUTPUT_PRICE_PER_M
    total_usd = input_cost_usd + output_cost_usd
    return total_usd * USD_TO_INR


# This block only runs when you launch the file directly with `python3 cost.py`.
# It's our isolated test — like retrieve.py was for retrieval.
if __name__ == "__main__":
    # Pretend numbers, so we can check the arithmetic by hand:
    rupees = query_cost_inr(1000, 300)
    print(f"Example query (1000 in / 300 out): ₹{rupees:.4f}")