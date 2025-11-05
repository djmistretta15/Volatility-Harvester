"""
Data ingestion - fetch and store OHLCV candles.
"""
from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd
from sqlalchemy.orm import Session
from app.adapters.exchange_base import ExchangeAdapter
from app.core.models import Candle
from app.db.database import get_db_context
import logging

logger = logging.getLogger(__name__)


class DataIngester:
    """
    Fetches OHLCV data from exchanges and stores in database.
    """

    def __init__(self, exchange: ExchangeAdapter, symbol: str):
        self.exchange = exchange
        self.symbol = symbol

    async def fetch_candles(
        self,
        timeframe: str,
        since: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Candle]:
        """
        Fetch candles from exchange.

        Args:
            timeframe: Candle timeframe (1m, 5m, 15m, 1h, etc.)
            since: Start time
            limit: Maximum number of candles

        Returns:
            List of Candle objects
        """
        try:
            raw_candles = await self.exchange.get_ohlcv(
                symbol=self.symbol,
                timeframe=timeframe,
                since=since,
                limit=limit
            )

            candles = []
            for raw in raw_candles:
                candle = Candle(
                    symbol=self.symbol,
                    ts=raw["timestamp"],
                    open=raw["open"],
                    high=raw["high"],
                    low=raw["low"],
                    close=raw["close"],
                    volume=raw["volume"],
                    source=self.exchange.__class__.__name__,
                    timeframe=timeframe
                )
                candles.append(candle)

            logger.info(f"Fetched {len(candles)} {timeframe} candles for {self.symbol}")
            return candles

        except Exception as e:
            logger.error(f"Failed to fetch candles: {e}")
            return []

    def store_candles(self, candles: List[Candle], db: Session):
        """
        Store candles in database.

        Args:
            candles: List of candles to store
            db: Database session
        """
        if not candles:
            return

        try:
            # Bulk insert (skip duplicates)
            for candle in candles:
                # Check if exists
                existing = db.query(Candle).filter(
                    Candle.symbol == candle.symbol,
                    Candle.ts == candle.ts,
                    Candle.timeframe == candle.timeframe
                ).first()

                if not existing:
                    db.add(candle)

            db.commit()
            logger.info(f"Stored {len(candles)} candles")

        except Exception as e:
            logger.error(f"Failed to store candles: {e}")
            db.rollback()

    async def backfill_candles(
        self,
        timeframe: str,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ):
        """
        Backfill historical candles.

        Args:
            timeframe: Candle timeframe
            start_date: Start date
            end_date: End date (default: now)
        """
        if end_date is None:
            end_date = datetime.utcnow()

        logger.info(f"Backfilling {timeframe} candles from {start_date} to {end_date}")

        # Fetch in chunks
        chunk_size = 1000
        current_date = start_date

        total_fetched = 0

        while current_date < end_date:
            candles = await self.fetch_candles(
                timeframe=timeframe,
                since=current_date,
                limit=chunk_size
            )

            if not candles:
                break

            with get_db_context() as db:
                self.store_candles(candles, db)

            total_fetched += len(candles)

            # Move to next chunk
            last_ts = candles[-1].ts
            current_date = last_ts + timedelta(minutes=1)

            # Avoid rate limits
            await asyncio.sleep(0.5)

        logger.info(f"Backfill complete: {total_fetched} candles fetched")

    def load_candles_from_db(
        self,
        timeframe: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: Optional[Session] = None
    ) -> pd.DataFrame:
        """
        Load candles from database as DataFrame.

        Args:
            timeframe: Candle timeframe
            start_date: Start date (optional)
            end_date: End date (optional)
            db: Database session (optional)

        Returns:
            DataFrame with columns [timestamp, open, high, low, close, volume]
        """
        def _load(session: Session) -> pd.DataFrame:
            query = session.query(Candle).filter(
                Candle.symbol == self.symbol,
                Candle.timeframe == timeframe
            )

            if start_date:
                query = query.filter(Candle.ts >= start_date)
            if end_date:
                query = query.filter(Candle.ts <= end_date)

            query = query.order_by(Candle.ts)

            candles = query.all()

            if not candles:
                logger.warning(f"No candles found for {self.symbol} {timeframe}")
                return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

            data = {
                "timestamp": [c.ts for c in candles],
                "open": [c.open for c in candles],
                "high": [c.high for c in candles],
                "low": [c.low for c in candles],
                "close": [c.close for c in candles],
                "volume": [c.volume for c in candles]
            }

            return pd.DataFrame(data)

        if db:
            return _load(db)
        else:
            with get_db_context() as session:
                return _load(session)


# Async import
import asyncio
