# main.py

import logging
import pandas as pd
from datetime import datetime
import sys
import os

# Define the project root directly within main.py
# This ensures that main.py itself knows where the root of your project is,
# regardless of how it's executed, which helps Python find your modules.
project_root = '/content/drive/MyDrive/algo_trading_prototype'
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    # Note: If you modify this or any other module, you might need to
    # restart your Colab runtime to ensure changes are picked up due to Python's module caching.

# Now, import modules using their top-level package names relative to project_root
from config import settings
from utils import logger
from data import data_fetcher
from backtester import backtester
from analytics import ml_predictor
from sheets import google_sheets_manager
from utils import alerts # Bonus: Telegram alerts

# Setup logging. This needs to be called to configure loggers globally.
logger.setup_logging()
main_logger = logging.getLogger(__name__) # Get a specific logger for the main script

def run_algo_prototype():
    """
    Main function to run the algo-trading prototype.
    Orchestrates data fetching, strategy application, backtesting,
    ML prediction, and Google Sheets logging.
    """
    main_logger.info("Starting Algo-Trading Prototype...")

    # Initialize components
    sheets_manager = google_sheets_manager.GoogleSheetsManager()
    backtester_instance = backtester.Backtester()
    ml_predictor_instance = ml_predictor.MLPredictor(model_type='decision_tree') # Can be 'logistic_regression'

    all_trade_logs = pd.DataFrame() # To aggregate trade logs from all symbols
    symbol_pnl_results = {} # To store P&L summary per symbol
    ml_accuracies = {} # To store ML model accuracies per symbol

    # --- 1. Data Ingestion & ML Model Training ---
    main_logger.info(f"Fetching historical data for {settings.STOCK_SYMBOLS} for {settings.BACKTEST_DURATION_MONTHS} months...")
    historical_data = data_fetcher.get_historical_data(settings.STOCK_SYMBOLS, settings.BACKTEST_DURATION_MONTHS)

    if not historical_data:
        main_logger.error("No historical data fetched. Exiting.")
        return

    # Train ML model for each stock using its historical data
    main_logger.info("Preparing data and training ML model for each stock...")
    for symbol, df in historical_data.items():
        if not df.empty:
            ml_data = ml_predictor_instance.prepare_data_for_ml(df.copy())
            if not ml_data.empty:
                accuracy, _ = ml_predictor_instance.train_model(ml_data, settings.FEATURES, settings.TARGET)
                ml_accuracies[symbol] = accuracy
            else:
                main_logger.warning(f"Could not prepare ML data for {symbol}.")
        else:
            main_logger.warning(f"No data for {symbol} to train ML model.")

    main_logger.info(f"ML Model Accuracies: {ml_accuracies}")

    # --- 2. Run Backtest for each stock ---
    for symbol, df in historical_data.items():
        if df.empty:
            main_logger.warning(f"Skipping backtest for {symbol} due to no data.")
            continue

        main_logger.info(f"Running backtest for {symbol}...")
        results = backtester_instance.run_backtest(symbol, df.copy())
        if results:
            symbol_pnl_results[symbol] = {
                'initial_capital': results['initial_capital'],
                'final_capital': results['final_capital'],
                'total_pnl': results['total_pnl']
            }
            if not results['trade_log'].empty:
                # Concatenate trade logs from each symbol into one DataFrame
                all_trade_logs = pd.concat([all_trade_logs, results['trade_log']], ignore_index=True)
        else:
            main_logger.warning(f"Backtest for {symbol} yielded no results.")

    # --- 3. Google Sheets Automation ---
    # Log all aggregated trade signals
    if not all_trade_logs.empty:
        main_logger.info("Logging trade signals to Google Sheets...")
        sheets_manager.log_trade_signals(all_trade_logs)
        # Update win ratio based on all logs
        sheets_manager.update_win_ratio(all_trade_logs)
    else:
        main_logger.info("No trade logs to write to Google Sheets.")

    # Update summary P&L
    if symbol_pnl_results:
        main_logger.info("Updating summary P&L in Google Sheets...")
        sheets_manager.update_summary_pnl(symbol_pnl_results)
    else:
        main_logger.info("No summary P&L to write to Google Sheets.")

    # --- 4. Generate Current Buy/Sell Signals and ML Predictions ---
    main_logger.info("Generating current (latest date) buy/sell signals and ML predictions...")
    for symbol, df in historical_data.items():
        if df.empty:
            main_logger.warning(f"Cannot generate signal for {symbol}: no data.")
            continue

        # Get enough historical data points to calculate all indicators for the latest day
        required_rows_for_indicators = max(settings.RSI_PERIOD, settings.SHORT_MA_PERIOD, settings.LONG_MA_PERIOD) + 1 # +1 for current day's signal
        latest_data_for_signal = df.tail(required_rows_for_indicators).copy()

        if latest_data_for_signal.empty:
            main_logger.warning(f"Not enough recent data for {symbol} to generate current signal after indicator calculation.")
            continue

        # Re-run strategy on the latest data to get the current day's signal
        processed_latest_data = backtester_instance.strategy.generate_signals(latest_data_for_signal)

        # Check if the last row (current day) has valid signal/data
        if processed_latest_data.empty or processed_latest_data.iloc[-1].isnull().any():
            main_logger.warning(f"Could not generate clean signal for {symbol} for the latest date after processing.")
            current_signal = 0 # Default to hold if signal is unreliable
            current_close = df['Close'].iloc[-1] if not df.empty else 0
            current_date = df.index[-1].strftime('%Y-%m-%d') if not df.empty else "N/A"
        else:
            current_signal = processed_latest_data['Signal'].iloc[-1]
            current_close = processed_latest_data['Close'].iloc[-1]
            current_date = processed_latest_data.index[-1].strftime('%Y-%m-%d')

        signal_type = "HOLD"
        if current_signal == 1:
            signal_type = "BUY"
        elif current_signal == -1:
            signal_type = "SELL"

        main_logger.info(f"[{symbol}] Latest Strategy Signal ({current_date}): {signal_type} at {current_close:.2f}")

        # ML prediction for next day movement
        # Need enough data points for ML features (RSI, MACD, Volume) for the current day
        # `prepare_data_for_ml` handles dropping NaNs, so pass a sufficient window of recent data
        ml_prediction_input_data = df.tail(max(settings.RSI_PERIOD, 26) + 2).copy() # MACD needs up to 26 periods + 1 for next day shift
        if not ml_prediction_input_data.empty and ml_predictor_instance.trained:
            next_day_pred = ml_predictor_instance.predict_next_day_movement(ml_prediction_input_data, settings.FEATURES)
            ml_pred_text = "Up" if next_day_pred == 1 else ("Down/No Change" if next_day_pred == 0 else "N/A - Prediction Failed")
            main_logger.info(f"[{symbol}] Next Day ML Prediction: {ml_pred_text}")
        else:
            ml_pred_text = "N/A - Model Not Trained or Insufficient Data"
            main_logger.warning(f"[{symbol}] {ml_pred_text}")

        # Bonus: Telegram Alert Integration
        if current_signal != 0 or next_day_pred != -1: # Alert for strategy signals or if ML made a valid prediction
            alert_message = sheets_manager.get_signal_alerts(symbol, current_date, signal_type, current_close)
            alert_message += f"\nML Prediction (Next Day): {ml_pred_text}"
            alerts.send_telegram_message(alert_message)

    main_logger.info("Algo-Trading Prototype finished.")

if __name__ == "__main__":
    run_algo_prototype()
