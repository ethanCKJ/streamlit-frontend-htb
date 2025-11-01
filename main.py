"""Main application entry point."""
import asyncio
import threading
import time
from loguru import logger

from data_ingestion import MultiExchangeAggregator
from arbitrage_detector import ArbitrageDetector
from ml_predictor import SpreadPredictor
from dashboard import ArbitrageDashboard


class ArbitrageSystem:
    """Main arbitrage detection system."""

    def __init__(self):
        # Initialize components
        self.detector = ArbitrageDetector()
        self.ml_predictor = SpreadPredictor()
        self.aggregator = MultiExchangeAggregator(self.on_price_update)
        self.dashboard = None

        # Control flags
        self.running = False
        self.training_interval = 300  # Train ML model every 5 minutes

    def on_price_update(self, price_data):
        """Callback for new price data."""
        # Update detector (which checks for arbitrage)
        self.detector.update_price(price_data)

    async def train_ml_model(self):
        """Periodically train the ML model on collected data."""
        while self.running:
            await asyncio.sleep(self.training_interval)

            logger.info("Training ML model on historical data...")

            symbols = ['BTC-USD', 'ETH-USD', 'SOL-USD']
            all_data = []

            for symbol in symbols:
                df = self.detector.get_historical_data(symbol)
                if not df.empty:
                    all_data.append(df)

            if all_data:
                import pandas as pd
                combined_df = pd.concat(all_data, ignore_index=True)

                if len(combined_df) > 100:
                    success = self.ml_predictor.train(combined_df)
                    if success:
                        logger.success("ML model training completed")

                        # Save model
                        self.ml_predictor.save("models/spread_predictor.pkl")
                else:
                    logger.warning("Not enough data for ML training yet")

    async def run_data_collection(self):
        """Run the data collection and arbitrage detection."""
        logger.info("Starting data collection and arbitrage detection...")
        await self.aggregator.start()

    def start_dashboard(self):
        """Start the web dashboard in a separate thread."""
        self.dashboard = ArbitrageDashboard(self.detector, self.ml_predictor)
        self.dashboard.run(host='0.0.0.0', port=8050, debug=False)

    async def run(self):
        """Run the complete system."""
        self.running = True

        logger.info("=" * 60)
        logger.info("🚀 CRYPTO ARBITRAGE DETECTION SYSTEM")
        logger.info("=" * 60)
        logger.info("Monitoring exchanges: Coinbase, Binance, Bitstamp")
        logger.info("Trading pairs: BTC-USD, ETH-USD, SOL-USD")
        logger.info("Dashboard: http://localhost:8050")
        logger.info("=" * 60)

        # Start dashboard in separate thread
        dashboard_thread = threading.Thread(target=self.start_dashboard, daemon=True)
        dashboard_thread.start()

        # Give dashboard time to start
        await asyncio.sleep(2)

        # Run data collection and ML training concurrently
        await asyncio.gather(
            self.run_data_collection(),
            self.train_ml_model(),
            return_exceptions=True
        )

    def stop(self):
        """Stop the system."""
        logger.info("Stopping arbitrage system...")
        self.running = False


def main():
    """Main entry point."""
    # Configure logger
    logger.add(
        "logs/arbitrage_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="INFO"
    )

    system = ArbitrageSystem()

    try:
        asyncio.run(system.run())
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        system.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
