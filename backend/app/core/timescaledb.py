"""
TimescaleDB setup and utilities for time-series data.

TimescaleDB is a PostgreSQL extension for time-series data that provides:
- Automatic partitioning by time
- Continuous aggregates
- Compression
- Retention policies

This module provides setup and utility functions for TimescaleDB integration.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class TimescaleDBSetup:
    """
    TimescaleDB setup and configuration.

    Handles:
    - Extension installation
    - Hypertable creation
    - Continuous aggregates
    - Retention policies
    - Compression policies
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize TimescaleDB setup.

        Args:
            db: SQLAlchemy async session.
        """
        self.db = db

    async def install_extension(self) -> bool:
        """
        Install TimescaleDB extension.

        Returns:
            True if successful.
        """
        try:
            await self.db.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb;"))
            await self.db.commit()
            logger.info("TimescaleDB extension installed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to install TimescaleDB extension: {e}")
            await self.db.rollback()
            return False

    async def create_hypertable(
        self,
        table_name: str,
        time_column: str = "timestamp",
        chunk_time_interval: str = "1 day"
    ) -> bool:
        """
        Convert a table to a hypertable.

        Args:
            table_name: Name of the table.
            time_column: Name of the time column.
            chunk_time_interval: Chunk time interval (e.g., '1 day', '7 days').

        Returns:
            True if successful.
        """
        try:
            # Check if already a hypertable
            check_query = text("""
                SELECT 1 FROM timescaledb_information.hypertables
                WHERE hypertable_name = :table_name
            """)
            result = await self.db.execute(check_query, {"table_name": table_name})
            if result.scalar():
                logger.info(f"Table {table_name} is already a hypertable")
                return True

            # Create hypertable
            create_query = text(f"""
                SELECT create_hypertable(
                    '{table_name}',
                    '{time_column}',
                    chunk_time_interval => INTERVAL '{chunk_time_interval}',
                    if_not_exists => TRUE
                );
            """)
            await self.db.execute(create_query)
            await self.db.commit()

            logger.info(f"Created hypertable {table_name} with {chunk_time_interval} chunks")
            return True

        except Exception as e:
            logger.error(f"Failed to create hypertable {table_name}: {e}")
            await self.db.rollback()
            return False

    async def setup_customer_events_hypertable(self) -> bool:
        """Setup hypertable for customer_events table."""
        return await self.create_hypertable(
            table_name="customer_events",
            time_column="timestamp",
            chunk_time_interval="1 day"
        )

    async def setup_conversion_events_hypertable(self) -> bool:
        """Setup hypertable for conversion_events table."""
        return await self.create_hypertable(
            table_name="conversion_events",
            time_column="conversion_timestamp",
            chunk_time_interval="1 day"
        )

    async def setup_touchpoints_hypertable(self) -> bool:
        """Setup hypertable for attribution_touchpoints table."""
        return await self.create_hypertable(
            table_name="attribution_touchpoints",
            time_column="touchpoint_timestamp",
            chunk_time_interval="1 day"
        )

    async def setup_mmm_daily_hypertable(self) -> bool:
        """Setup hypertable for mmm_channel_daily table."""
        return await self.create_hypertable(
            table_name="mmm_channel_daily",
            time_column="date",
            chunk_time_interval="7 days"
        )

    async def setup_all_hypertables(self) -> Dict[str, bool]:
        """Setup all hypertables for analytics tables."""
        results = {}

        results["customer_events"] = await self.setup_customer_events_hypertable()
        results["conversion_events"] = await self.setup_conversion_events_hypertable()
        results["attribution_touchpoints"] = await self.setup_touchpoints_hypertable()
        results["mmm_channel_daily"] = await self.setup_mmm_daily_hypertable()

        return results

    # ============== Continuous Aggregates ==============

    async def create_continuous_aggregate(
        self,
        view_name: str,
        table_name: str,
        time_bucket: str,
        time_column: str,
        aggregations: List[Dict[str, str]],
        group_by_columns: Optional[List[str]] = None
    ) -> bool:
        """
        Create a continuous aggregate view.

        Args:
            view_name: Name of the materialized view.
            table_name: Source table name.
            time_bucket: Time bucket interval (e.g., '1 hour', '1 day').
            time_column: Time column name.
            aggregations: List of aggregation definitions.
                Each dict should have: {"function": "sum", "column": "value", "alias": "total_value"}
            group_by_columns: Additional columns to group by.

        Returns:
            True if successful.
        """
        try:
            # Build aggregation expressions
            agg_exprs = []
            for agg in aggregations:
                func = agg["function"]
                col = agg["column"]
                alias = agg["alias"]
                agg_exprs.append(f"{func}({col}) as {alias}")

            # Build GROUP BY clause
            group_cols = [f"time_bucket('{time_bucket}', {time_column})"]
            if group_by_columns:
                group_cols.extend(group_by_columns)

            group_by_clause = ", ".join(group_cols)

            # Create materialized view
            create_query = text(f"""
                CREATE MATERIALIZED VIEW IF NOT EXISTS {view_name}
                WITH (timescaledb.continuous) AS
                SELECT
                    time_bucket('{time_bucket}', {time_column}) as bucket,
                    {", ".join(group_by_columns) if group_by_columns else ""}
                    {", ".join(agg_exprs)}
                FROM {table_name}
                GROUP BY {group_by_clause}
                WITH NO DATA;
            """)

            await self.db.execute(create_query)
            await self.db.commit()

            logger.info(f"Created continuous aggregate {view_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create continuous aggregate {view_name}: {e}")
            await self.db.rollback()
            return False

    async def create_conversion_metrics_hourly(self) -> bool:
        """Create hourly conversion metrics continuous aggregate."""
        return await self.create_continuous_aggregate(
            view_name="conversion_metrics_hourly",
            table_name="conversion_events",
            time_bucket="1 hour",
            time_column="conversion_timestamp",
            aggregations=[
                {"function": "count", "column": "*", "alias": "conversion_count"},
                {"function": "sum", "column": "conversion_value", "alias": "total_value"},
                {"function": "avg", "column": "conversion_value", "alias": "avg_value"}
            ],
            group_by_columns=["organization_id", "conversion_type"]
        )

    async def create_touchpoint_metrics_daily(self) -> bool:
        """Create daily touchpoint metrics continuous aggregate."""
        return await self.create_continuous_aggregate(
            view_name="touchpoint_metrics_daily",
            table_name="attribution_touchpoints",
            time_bucket="1 day",
            time_column="touchpoint_timestamp",
            aggregations=[
                {"function": "count", "column": "*", "alias": "touchpoint_count"},
                {"function": "sum", "column": "cost", "alias": "total_cost"},
                {"function": "avg", "column": "engagement_score", "alias": "avg_engagement"}
            ],
            group_by_columns=["organization_id", "channel"]
        )

    async def create_attribution_metrics_daily(self) -> bool:
        """Create daily attribution metrics continuous aggregate."""
        return await self.create_continuous_aggregate(
            view_name="attribution_metrics_daily",
            table_name="attributions",
            time_bucket="1 day",
            time_column="calculated_at",
            aggregations=[
                {"function": "sum", "column": "attributed_value", "alias": "total_attributed"},
                {"function": "avg", "column": "weight", "alias": "avg_weight"},
                {"function": "count", "column": "*", "alias": "attribution_count"}
            ],
            group_by_columns=["organization_id", "model_type"]
        )

    # ============== Retention Policies ==============

    async def add_retention_policy(
        self,
        table_name: str,
        drop_after: str
    ) -> bool:
        """
        Add retention policy to a hypertable.

        Args:
            table_name: Name of the hypertable.
            drop_after: Interval after which to drop chunks (e.g., '90 days').

        Returns:
            True if successful.
        """
        try:
            policy_query = text(f"""
                SELECT add_retention_policy(
                    '{table_name}',
                    drop_after => INTERVAL '{drop_after}'
                );
            """)
            await self.db.execute(policy_query)
            await self.db.commit()

            logger.info(f"Added retention policy to {table_name}: drop after {drop_after}")
            return True

        except Exception as e:
            logger.error(f"Failed to add retention policy to {table_name}: {e}")
            await self.db.rollback()
            return False

    async def setup_retention_policies(self) -> Dict[str, bool]:
        """Setup retention policies for all analytics tables."""
        results = {}

        # Keep raw events for 90 days
        results["customer_events"] = await self.add_retention_policy(
            "customer_events", "90 days"
        )

        # Keep conversions for 2 years
        results["conversion_events"] = await self.add_retention_policy(
            "conversion_events", "2 years"
        )

        # Keep touchpoints for 1 year
        results["attribution_touchpoints"] = await self.add_retention_policy(
            "attribution_touchpoints", "1 year"
        )

        # Keep MMM daily data for 3 years
        results["mmm_channel_daily"] = await self.add_retention_policy(
            "mmm_channel_daily", "3 years"
        )

        return results

    # ============== Compression Policies ==============

    async def add_compression_policy(
        self,
        table_name: str,
        compress_after: str,
        segment_by: Optional[List[str]] = None
    ) -> bool:
        """
        Add compression policy to a hypertable.

        Args:
            table_name: Name of the hypertable.
            compress_after: Interval after which to compress chunks.
            segment_by: Columns to segment by for compression.

        Returns:
            True if successful.
        """
        try:
            # Enable compression
            segment_clause = ""
            if segment_by:
                segment_clause = f", segmentby => ARRAY{segment_by}"

            enable_query = text(f"""
                ALTER TABLE {table_name} SET (
                    timescaledb.compress{segment_clause}
                );
            """)
            await self.db.execute(enable_query)

            # Add compression policy
            policy_query = text(f"""
                SELECT add_compression_policy(
                    '{table_name}',
                    compress_after => INTERVAL '{compress_after}'
                );
            """)
            await self.db.execute(policy_query)
            await self.db.commit()

            logger.info(f"Added compression policy to {table_name}: compress after {compress_after}")
            return True

        except Exception as e:
            logger.error(f"Failed to add compression policy to {table_name}: {e}")
            await self.db.rollback()
            return False

    async def setup_compression_policies(self) -> Dict[str, bool]:
        """Setup compression policies for analytics tables."""
        results = {}

        # Compress customer events after 7 days, segment by organization
        results["customer_events"] = await self.add_compression_policy(
            "customer_events",
            compress_after="7 days",
            segment_by=["organization_id"]
        )

        # Compress touchpoints after 30 days
        results["attribution_touchpoints"] = await self.add_compression_policy(
            "attribution_touchpoints",
            compress_after="30 days",
            segment_by=["organization_id", "channel"]
        )

        return results

    # ============== Refresh Policies ==============

    async def add_refresh_policy(
        self,
        view_name: str,
        start_offset: str,
        end_offset: str,
        schedule_interval: str
    ) -> bool:
        """
        Add refresh policy to a continuous aggregate.

        Args:
            view_name: Name of the materialized view.
            start_offset: How far back to refresh.
            end_offset: How far forward to refresh.
            schedule_interval: How often to refresh.

        Returns:
            True if successful.
        """
        try:
            policy_query = text(f"""
                SELECT add_continuous_aggregate_policy('{view_name}',
                    start_offset => INTERVAL '{start_offset}',
                    end_offset => INTERVAL '{end_offset}',
                    schedule_interval => INTERVAL '{schedule_interval}'
                );
            """)
            await self.db.execute(policy_query)
            await self.db.commit()

            logger.info(f"Added refresh policy to {view_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to add refresh policy to {view_name}: {e}")
            await self.db.rollback()
            return False

    # ============== Utility Functions ==============

    async def get_hypertable_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a hypertable."""
        try:
            query = text("""
                SELECT *
                FROM timescaledb_information.hypertables
                WHERE hypertable_name = :table_name
            """)
            result = await self.db.execute(query, {"table_name": table_name})
            row = result.mappings().first()

            if row:
                return dict(row)
            return None

        except Exception as e:
            logger.error(f"Failed to get hypertable info for {table_name}: {e}")
            return None

    async def get_chunk_stats(self, table_name: str) -> List[Dict[str, Any]]:
        """Get chunk statistics for a hypertable."""
        try:
            query = text("""
                SELECT *
                FROM chunks_detailed_size(:table_name)
                ORDER BY chunk_name
            """)
            result = await self.db.execute(query, {"table_name": table_name})
            rows = result.mappings().all()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get chunk stats for {table_name}: {e}")
            return []

    async def compress_chunk(self, chunk_name: str) -> bool:
        """Manually compress a specific chunk."""
        try:
            query = text(f"SELECT compress_chunk('{chunk_name}');")
            await self.db.execute(query)
            await self.db.commit()

            logger.info(f"Compressed chunk {chunk_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to compress chunk {chunk_name}: {e}")
            await self.db.rollback()
            return False

    async def decompress_chunk(self, chunk_name: str) -> bool:
        """Manually decompress a specific chunk."""
        try:
            query = text(f"SELECT decompress_chunk('{chunk_name}');")
            await self.db.execute(query)
            await self.db.commit()

            logger.info(f"Decompressed chunk {chunk_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to decompress chunk {chunk_name}: {e}")
            await self.db.rollback()
            return False


# ============== Convenience Functions ==============

async def setup_timescaledb(db: AsyncSession) -> Dict[str, Any]:
    """
    Complete TimescaleDB setup.

    Args:
        db: SQLAlchemy async session.

    Returns:
        Setup results.
    """
    setup = TimescaleDBSetup(db)

    results = {
        "extension_installed": await setup.install_extension(),
        "hypertables": await setup.setup_all_hypertables(),
        "retention_policies": await setup.setup_retention_policies(),
        "compression_policies": await setup.setup_compression_policies(),
    }

    # Create continuous aggregates
    results["continuous_aggregates"] = {
        "conversion_metrics_hourly": await setup.create_conversion_metrics_hourly(),
        "touchpoint_metrics_daily": await setup.create_touchpoint_metrics_daily(),
        "attribution_metrics_daily": await setup.create_attribution_metrics_daily(),
    }

    return results
