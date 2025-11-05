"""
Candles repository for database operations.
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
import pandas as pd
from app.core.models import Candle


class CandlesRepository:
    """Repository for candle data operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_candles(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Candle]:
        """Get candles from database."""
        query = self.db.query(Candle).filter(
            and_(
                Candle.symbol == symbol,
                Candle.timeframe == timeframe
            )
        )

        if start:
            query = query.filter(Candle.ts >= start)
        if end:
            query = query.filter(Candle.ts <= end)

        query = query.order_by(Candle.ts)

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_latest_candle(self, symbol: str, timeframe: str) -> Optional[Candle]:
        """Get most recent candle."""
        return self.db.query(Candle).filter(
            and_(
                Candle.symbol == symbol,
                Candle.timeframe == timeframe
            )
        ).order_by(Candle.ts.desc()).first()

    def candles_to_dataframe(self, candles: List[Candle]) -> pd.DataFrame:
        """Convert candles to DataFrame."""
        if not candles:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        data = {
            "timestamp": [c.ts for c in candles],
            "open": [c.open for c in candles],
            "high": [c.high for c in candles],
            "low": [c.low for c in candles],
            "close": [c.close for c in candles],
            "volume": [c.volume for c in candles]
        }

        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)
        return df

    def insert_candle(self, candle: Candle):
        """Insert a single candle."""
        self.db.add(candle)
        self.db.commit()

    def bulk_insert_candles(self, candles: List[Candle]):
        """Bulk insert candles."""
        self.db.bulk_save_objects(candles)
        self.db.commit()
