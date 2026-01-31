"""
Snowflake data warehouse connector.

Provides efficient data export to Snowflake with:
- Connection pooling and management
- Bulk insert operations
- Schema management
- Customer, event, and attribution data export
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

logger = logging.getLogger(__name__)

# Snowflake connector is optional - only import if available
try:
    import snowflake.connector
    from snowflake.connector.pandas_tools import write_pandas
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False
    logger.warning("Snowflake connector not installed. Install with: pip install snowflake-connector-python")


class SnowflakeError(Exception):
    """Base exception for Snowflake errors."""
    pass


class SnowflakeClient:
    """
    Snowflake data warehouse connector.
    
    Manages connections and data operations with Snowflake including
    bulk exports of CDP data for analytics.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Snowflake client.
        
        Args:
            config: Connection configuration containing:
                - account: Snowflake account identifier
                - user: Username
                - password: Password
                - private_key: Private key for key-pair auth (alternative to password)
                - database: Database name
                - schema: Schema name (default: PUBLIC)
                - warehouse: Warehouse name
                - role: Role name (optional)
        """
        if not SNOWFLAKE_AVAILABLE:
            raise ImportError(
                "Snowflake connector not installed. "
                "Install with: pip install snowflake-connector-python"
            )
        
        self.account = config["account"]
        self.user = config["user"]
        self.password = config.get("password")
        self.private_key = config.get("private_key")
        self.database = config["database"]
        self.schema = config.get("schema", "PUBLIC")
        self.warehouse = config.get("warehouse")
        self.role = config.get("role")
        
        self._connection = None
    
    async def connect(self):
        """Establish Snowflake connection."""
        connect_params = {
            "account": self.account,
            "user": self.user,
            "database": self.database,
            "schema": self.schema,
        }
        
        if self.password:
            connect_params["password"] = self.password
        elif self.private_key:
            connect_params["private_key"] = self.private_key
        else:
            raise SnowflakeError("Either password or private_key must be provided")
        
        if self.warehouse:
            connect_params["warehouse"] = self.warehouse
        if self.role:
            connect_params["role"] = self.role
        
        try:
            self._connection = snowflake.connector.connect(**connect_params)
            logger.info(f"Connected to Snowflake: {self.account}/{self.database}/{self.schema}")
        except Exception as e:
            raise SnowflakeError(f"Failed to connect to Snowflake: {e}")
    
    async def close(self):
        """Close Snowflake connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Snowflake connection closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    def _get_connection(self):
        """Get active connection."""
        if not self._connection:
            raise SnowflakeError("Not connected to Snowflake. Call connect() first.")
        return self._connection
    
    async def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute SQL query.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of result rows as dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]
        finally:
            cursor.close()
    
    async def execute(self, query: str, params: Optional[tuple] = None) -> int:
        """
        Execute SQL statement (non-query).
        
        Args:
            query: SQL statement
            params: Statement parameters
            
        Returns:
            Number of affected rows
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            return cursor.rowcount
        finally:
            cursor.close()
    
    async def create_table(self, table_name: str, schema: Dict[str, str]) -> None:
        """
        Create table if not exists.
        
        Args:
            table_name: Name of the table
            schema: Dictionary of column names to types
        """
        columns = ", ".join([f"{col} {dtype}" for col, dtype in schema.items()])
        query = f"""
            CREATE TABLE IF NOT EXISTS {self.schema}.{table_name} (
                {columns}
            )
        """
        await self.execute(query)
        logger.info(f"Created table {table_name}")
    
    async def bulk_insert(
        self,
        table_name: str,
        data: List[Dict[str, Any]],
        batch_size: int = 1000
    ) -> int:
        """
        Bulk insert data using efficient loading.
        
        Args:
            table_name: Target table name
            data: List of dictionaries to insert
            batch_size: Number of rows per batch
            
        Returns:
            Number of rows inserted
        """
        if not data:
            return 0
        
        try:
            import pandas as pd
            
            df = pd.DataFrame(data)
            
            success, num_chunks, num_rows, _ = write_pandas(
                conn=self._get_connection(),
                df=df,
                table_name=table_name,
                schema=self.schema,
                database=self.database,
                chunk_size=batch_size
            )
            
            if success:
                logger.info(f"Inserted {num_rows} rows into {table_name}")
                return num_rows
            else:
                raise SnowflakeError("Bulk insert failed")
                
        except ImportError:
            # Fallback to manual insert if pandas not available
            return await self._manual_bulk_insert(table_name, data, batch_size)
    
    async def _manual_bulk_insert(
        self,
        table_name: str,
        data: List[Dict[str, Any]],
        batch_size: int = 1000
    ) -> int:
        """Manual bulk insert without pandas."""
        if not data:
            return 0
        
        columns = list(data[0].keys())
        total_inserted = 0
        
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            
            # Build INSERT statement
            placeholders = ", ".join(["%s"] * len(columns))
            column_names = ", ".join(columns)
            
            query = f"""
                INSERT INTO {self.schema}.{table_name} ({column_names})
                VALUES ({placeholders})
            """
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                # Prepare batch values
                values = [
                    tuple(row.get(col) for col in columns)
                    for row in batch
                ]
                
                cursor.executemany(query, values)
                total_inserted += cursor.rowcount
            finally:
                cursor.close()
        
        logger.info(f"Inserted {total_inserted} rows into {table_name}")
        return total_inserted
    
    async def export_customers(
        self,
        organization_id: UUID,
        customers: List[Dict[str, Any]],
        destination_table: str = "cdp_customers",
        full_refresh: bool = False
    ) -> int:
        """
        Export CDP customers to Snowflake.
        
        Args:
            organization_id: Organization ID
            customers: List of customer dictionaries
            destination_table: Target table name
            full_refresh: If True, truncate table before insert
            
        Returns:
            Number of rows exported
        """
        # Create table if not exists
        await self.create_table(destination_table, {
            "id": "VARCHAR(12)",
            "organization_id": "VARCHAR(12)",
            "external_ids": "VARIANT",
            "anonymous_id": "VARCHAR(64)",
            "traits": "VARIANT",
            "computed_traits": "VARIANT",
            "engagement_score": "FLOAT",
            "lifetime_value": "FLOAT",
            "churn_risk": "FLOAT",
            "recency_days": "FLOAT",
            "frequency_score": "FLOAT",
            "monetary_value": "FLOAT",
            "first_seen_at": "TIMESTAMP_NTZ",
            "last_seen_at": "TIMESTAMP_NTZ",
            "created_at": "TIMESTAMP_NTZ",
            "updated_at": "TIMESTAMP_NTZ",
            "exported_at": "TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()"
        })
        
        # Truncate if full refresh
        if full_refresh:
            await self.execute(f"DELETE FROM {self.schema}.{destination_table} WHERE organization_id = %s", (str(organization_id),))
        
        # Prepare data
        export_data = []
        for customer in customers:
            export_data.append({
                "id": customer.get("id"),
                "organization_id": str(organization_id),
                "external_ids": customer.get("external_ids", {}),
                "anonymous_id": customer.get("anonymous_id"),
                "traits": customer.get("traits", {}),
                "computed_traits": customer.get("computed_traits", {}),
                "engagement_score": customer.get("engagement_score", 0),
                "lifetime_value": customer.get("lifetime_value", 0),
                "churn_risk": customer.get("churn_risk", 0),
                "recency_days": customer.get("recency_days"),
                "frequency_score": customer.get("frequency_score"),
                "monetary_value": customer.get("monetary_value"),
                "first_seen_at": customer.get("first_seen_at"),
                "last_seen_at": customer.get("last_seen_at"),
                "created_at": customer.get("created_at"),
                "updated_at": customer.get("updated_at")
            })
        
        return await self.bulk_insert(destination_table, export_data)
    
    async def export_events(
        self,
        organization_id: UUID,
        events: List[Dict[str, Any]],
        destination_table: str = "cdp_events",
        full_refresh: bool = False
    ) -> int:
        """
        Export customer events to Snowflake.
        
        Args:
            organization_id: Organization ID
            events: List of event dictionaries
            destination_table: Target table name
            full_refresh: If True, truncate table before insert
            
        Returns:
            Number of rows exported
        """
        await self.create_table(destination_table, {
            "id": "VARCHAR(12)",
            "organization_id": "VARCHAR(12)",
            "customer_id": "VARCHAR(12)",
            "anonymous_id": "VARCHAR(64)",
            "event_type": "VARCHAR(100)",
            "event_name": "VARCHAR(255)",
            "properties": "VARIANT",
            "context": "VARIANT",
            "timestamp": "TIMESTAMP_NTZ",
            "session_id": "VARCHAR(64)",
            "campaign_id": "VARCHAR(12)",
            "source": "VARCHAR(50)",
            "created_at": "TIMESTAMP_NTZ",
            "exported_at": "TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()"
        })
        
        if full_refresh:
            await self.execute(f"DELETE FROM {self.schema}.{destination_table} WHERE organization_id = %s", (str(organization_id),))
        
        export_data = []
        for event in events:
            export_data.append({
                "id": event.get("id"),
                "organization_id": str(organization_id),
                "customer_id": event.get("customer_id"),
                "anonymous_id": event.get("anonymous_id"),
                "event_type": event.get("event_type"),
                "event_name": event.get("event_name"),
                "properties": event.get("properties", {}),
                "context": event.get("context", {}),
                "timestamp": event.get("timestamp"),
                "session_id": event.get("session_id"),
                "campaign_id": event.get("campaign_id"),
                "source": event.get("source"),
                "created_at": event.get("created_at")
            })
        
        return await self.bulk_insert(destination_table, export_data)
    
    async def export_attribution(
        self,
        organization_id: UUID,
        attributions: List[Dict[str, Any]],
        destination_table: str = "cdp_attribution"
    ) -> int:
        """
        Export attribution data to Snowflake.
        
        Args:
            organization_id: Organization ID
            attributions: List of attribution dictionaries
            destination_table: Target table name
            
        Returns:
            Number of rows exported
        """
        await self.create_table(destination_table, {
            "id": "VARCHAR(12)",
            "organization_id": "VARCHAR(12)",
            "customer_id": "VARCHAR(12)",
            "conversion_event_id": "VARCHAR(12)",
            "attribution_model": "VARCHAR(50)",
            "touchpoint_id": "VARCHAR(12)",
            "touchpoint_type": "VARCHAR(50)",
            "channel": "VARCHAR(100)",
            "campaign_id": "VARCHAR(12)",
            "attribution_percentage": "FLOAT",
            "attributed_revenue": "FLOAT",
            "time_to_conversion_hours": "FLOAT",
            "created_at": "TIMESTAMP_NTZ",
            "exported_at": "TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()"
        })
        
        export_data = []
        for attr in attributions:
            export_data.append({
                "id": attr.get("id"),
                "organization_id": str(organization_id),
                "customer_id": attr.get("customer_id"),
                "conversion_event_id": attr.get("conversion_event_id"),
                "attribution_model": attr.get("attribution_model"),
                "touchpoint_id": attr.get("touchpoint_id"),
                "touchpoint_type": attr.get("touchpoint_type"),
                "channel": attr.get("channel"),
                "campaign_id": attr.get("campaign_id"),
                "attribution_percentage": attr.get("attribution_percentage"),
                "attributed_revenue": attr.get("attributed_revenue"),
                "time_to_conversion_hours": attr.get("time_to_conversion_hours"),
                "created_at": attr.get("created_at")
            })
        
        return await self.bulk_insert(destination_table, export_data)
    
    async def validate_connection(self) -> bool:
        """
        Test Snowflake connection.
        
        Returns:
            True if connection is valid
        """
        try:
            await self.connect()
            result = await self.execute_query("SELECT CURRENT_VERSION()")
            await self.close()
            return len(result) > 0
        except Exception as e:
            logger.error(f"Snowflake connection validation failed: {e}")
            return False
    
    async def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get schema for a table.
        
        Args:
            table_name: Table name
            
        Returns:
            List of column definitions
        """
        query = f"""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        
        return await self.execute_query(query, (self.schema.upper(), table_name.upper()))
