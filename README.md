# Algo-Trading-System-with-ML-Automation
This Python module provides the `GoogleSheetsManager` class to authenticate with Google Sheets via a service account, log trades, and update PnL summaries. It appends trade records, creates or updates summary sheets, and uses robust logging for easy integration into automated trading workflows.

This module provides a GoogleSheetsManager class for connecting to Google Sheets via a service account and performing trade logging and PnL summary updates.

Key Features:

    Google Sheets Authentication – Authenticates using a service account JSON credentials file and gspread with OAuth2 scopes for Sheets and Drive access.

    Trade Logging – Appends a single row of trade data (e.g., timestamp, symbol, price, quantity, PnL) to the first worksheet in a Google Sheet.

    PnL Summary Updating – Writes or updates a summary worksheet containing each trading symbol and its total PnL. Automatically creates the worksheet if it doesn’t exist.

    Error Handling & Logging – Uses Python’s logging module to log success and error messages, making it easy to track issues in automation workflows.

Typical Usage:

    Initialize the manager with the path to the service account credentials file.

    Call authenticate() to connect to Google Sheets.

    Use log_trade() to append trade records to your log sheet.

    Use update_summary_pnl() to write or refresh a consolidated PnL report.
