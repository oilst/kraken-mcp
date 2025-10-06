<p align="center">
  <img src="kraken_mcp_logo_alt2.png" alt="Kraken MCP logo" width="200">
</p>

# Kraken Pro MCP for Gemini CLI

This project provides a [FastMCP](https://gofastmcp.com/) server that exposes the Kraken Pro REST API as a set of tools for the Gemini CLI. This allows you to interact with your Kraken account, trade, and access market data directly from your terminal using natural language.

## Features

This server exposes a comprehensive set of tools for interacting with the Kraken API, including:

*   **Trading:** `add_order`, `cancel_order`, `amend_order`, `open_orders`, `cancel_all_orders_after`
*   **Market Data:** `server_time`, `system_status`, `asset_info`, `tradable_asset_pairs`, `ticker`, `ohlc`, `order_book`, `recent_trades`, `recent_spreads`

## Prerequisites

*   [Gemini CLI](https://github.com/google/gemini-cli)
*   [FastMCP](https://gofastmcp.com/) (`pip install fastmcp-cli`)
*   A Kraken Pro account with API keys.

## Installation

The recommended way to install this server for use with the Gemini CLI is using the `fastmcp` command-line tool.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/oilst/kraken-mcp.git
    cd kraken-mcp
    ```

2.  **Set up your environment variables:**
    Create a `.env` file in the project directory with your Kraken API keys:
    ```
    KRAKEN_API_KEY="your_public_key"
    KRAKEN_API_SECRET="your_private_base64_secret"
    ```

3.  **Install the server:**
    Run the following command to install the server, its dependencies, and make the tools available to the Gemini CLI:
    ```bash
    fastmcp install gemini-cli kraken-server.py 
    ```

## Usage

Once installed, you can use the tools directly in the Gemini CLI. Gemini will automatically detect the appropriate tool based on your prompt.

**Examples:**

*   "What is the current price of Bitcoin?" (uses the `ticker` tool)
*   "Place an order to buy 0.1 XBT at $50,000" (uses the `add_order` tool)
*   "Show me my open orders" (uses the `open_orders` tool)
*   "Cancel order XXXXX-XXXXX-XXXXXX" (uses the `cancel_order` tool)

## Tools

Here is a list of the available tools and their parameters.

### Trading Tools

*   `add_order(pair, side, ordertype, volume, price, ...)`: Place a new order.
*   `cancel_order(txid_or_userref)`: Cancel an open order.
*   `open_orders(userref, trades)`: Fetch open orders.
*   `amend_order(order_id, order_qty, limit_price, ...)`: Amend an open order.
*   `cancel_all_orders_after(timeout_seconds)`: Set a dead man's switch to cancel all orders.

### Market Data Tools

*   `server_time()`: Get the Kraken server time.
*   `system_status()`: Get the current system status.
*   `asset_info(assets, aclass)`: Get information about assets.
*   `tradable_asset_pairs(pairs, info)`: Get information about tradable pairs.
*   `ticker(pairs)`: Get ticker information.
*   `ohlc(pair, interval, since)`: Get OHLC data.
*   `order_book(pair, count)`: Get the order book.
*   `recent_trades(pair, since)`: Get recent trades.
*   `recent_spreads(pair, since)`: Get recent spreads.

For detailed information on the parameters for each tool, please refer to the docstrings in the `kraken-server.py` file.

## Disclaimer

Use this tool at your own risk. The author is not responsible for any financial losses. Always test with `validate=True` for the `add_order` tool before placing real orders.