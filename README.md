This Python module provides the GoogleSheetsManager class for seamless integration with Google Sheets, enabling automated trade logging and PnL (Profit and Loss) tracking within algorithmic trading workflows.

Key Capabilities

- Google Sheets Authentication – Connects securely using a service account credentials file and gspread with OAuth2 scopes for Sheets and Drive access.

- Automated Trade Logging – Appends trade data (timestamp, symbol, price, quantity, PnL, etc.) directly to the primary worksheet.

- PnL Summary Management – Creates or updates a dedicated summary worksheet showing total PnL per symbol. Automatically generates the worksheet if it doesn’t exist.

- Robust Error Handling & Logging – Leverages Python’s logging module for detailed success/error reporting, simplifying debugging in automated pipelines.

Typical Workflow

Initialize the manager with the path to your service account credentials.

- Run authenticate() to establish a connection with Google Sheets.

- Use log_trade() to record new trades in the log sheet.

- Call update_summary_pnl() to generate or refresh a consolidated PnL report.
