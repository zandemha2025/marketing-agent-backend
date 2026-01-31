"""
Google BigQuery data warehouse connector.

Provides efficient data export to BigQuery with:
- Service account authentication
- Streaming inserts
- Load jobs for bulk data
- Schema management
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

logger = logging.getLogger(__name__)

# BigQuery client is optional - only import if available
try:
    from google.cloud import bigquery
    from google.oauth2 import service_account
    BIGQUERY_AVAILABLE = True
except ImportError:
    BIGQUERY_AVAILABLE = False
    logger.warning("BigQuery client not installed. Install with: pip install google-cloud-bigquery")


class BigQueryError(Exception):
    """Base exception for BigQuery errors."""
    pass


class BigQueryClient:
    """
    Google BigQuery connector.
    
    Manages connections and data operations with BigQuery including
    bulk exports of CDP data for analytics.
    """
    
    def __init__(self, credentials_json: str):
        """
        Initialize BigQuery client.
        
        Args:
            credentials_json: Service account credentials JSON string or file path
        """
        if not BIGQUERY_AVAILABLE:
            raise ImportError(
                "BigQuery client not installed. "
                "Install with: pip install google-cloud-bigquery"
            )
        
        self.credentials_json = credentials_json
        self._client: Optional[bigquery.Client] = None
        
        # Parse credentials
        try:
            if credentials_json.strip().startswith('{'):
                # JSON string
                creds_info = json.loads(credentials_json)
                self.credentials = service_account.Credentials.from_service_account_info(creds_info)
                self.project_id = creds_info.get("project_id")
            else:
                # File path
                self.credentials = service_account.Credentials.from_service_account_file(credentials_json)
                with open(credentials_json) as f:
                    creds_info = json.load(f)
                self.project_id = creds_info.get("project_id")
        except Exception as e:
            raise BigQueryError(f"Failed to parse credentials: {e}")
    
    def _get_client(self) -> bigquery.Client:
        """Get or create BigQuery client."""
        if self._client is None:
            self._client = bigquery.Client(
                project=self.project_id,
                credentials=self.credentials
            )
        return self._client
    
    async def close(self):
        """Close BigQuery client."""
        if self._client:
            self._client.close()
            self._client = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute BigQuery query.
        
        Args:
            query: SQL query string
            
        Returns:
            List of result rows as dictionaries
        """
        client = self._get_client()
        
        try:
            query_job = client.query(query)
            results = query_job.result()
            
            return [dict(row.items()) for row in results]
        except Exception as e:
            raise BigQueryError(f"Query failed: {e}")
    
    async def create_dataset(self, dataset_id: str, location: str = "US") -> None:
        """
        Create dataset if not exists.
        
        Args:
            dataset_id: Dataset ID
            location: Geographic location
        """
        client = self._get_client()
        
        dataset_ref = f"{self.project_id}.{dataset_id}"
        
        try:
            client.get_dataset(dataset_ref)
            logger.info(f"Dataset {dataset_id} already exists")
        except Exception:
            # Dataset doesn't exist, create it
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = location
            dataset = client.create_dataset(dataset, exists_ok=True)
            logger.info(f"Created dataset {dataset_id}")
    
    async def create_table(
        self,
        dataset_id: str,
        table_id: str,
        schema: List[bigquery.SchemaField]
    ) -> None:
        """
        Create table if not exists.
        
        Args:
            dataset_id: Dataset ID
            table_id: Table ID
            schema: List of schema fields
        """
        client = self._get_client()
        
        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        
        try:
            client.get_table(table_ref)
            logger.info(f"Table {table_id} already exists")
        except Exception:
            # Table doesn't exist, create it
            table = bigquery.Table(table_ref, schema=schema)
            table = client.create_table(table, exists_ok=True)
            logger.info(f"Created table {table_id}")
    
    async def stream_insert(
        self,
        dataset_id: str,
        table_id: str,
        rows: List[Dict[str, Any]]
    ) -> int:
        """
        Stream insert rows into BigQuery.
        
        Args:
            dataset_id: Dataset ID
            table_id: Table ID
            rows: List of row dictionaries
            
        Returns:
            Number of rows inserted
        """
        client = self._get_client()
        
        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        table = client.get_table(table_ref)
        
        errors = client.insert_rows_json(table, rows)
        
        if errors:
            logger.error(f"Errors inserting rows: {errors}")
            raise BigQueryError(f"Insert errors: {errors}")
        
        logger.info(f"Streamed {len(rows)} rows into {table_id}")
        return len(rows)
    
    async def load_from_json(
        self,
        dataset_id: str,
        table_id: str,
        rows: List[Dict[str, Any]],
        write_disposition: str = "WRITE_APPEND"
    ) -> int:
        """
        Load data from JSON using a load job.
        
        Args:
            dataset_id: Dataset ID
            table_id: Table ID
            rows: List of row dictionaries
            write_disposition: Write disposition (WRITE_TRUNCATE, WRITE_APPEND, WRITE_EMPTY)
            
        Returns:
            Number of rows loaded
        """
        client = self._get_client()
        
        # Convert rows to newline-delimited JSON
        import io
        json_lines = "\n".join([json.dumps(row) for row in rows])
        
        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=write_disposition,
            autodetect=True
        )
        
        try:
            load_job = client.load_table_from_file(
                io.BytesIO(json_lines.encode()),
                table_ref,
                job_config=job_config
            )
            load_job.result()  # Wait for job to complete
            
            logger.info(f"Loaded {len(rows)} rows into {table_id}")
            return len(rows)
        except Exception as e:
            raise BigQueryError(f"Load job failed: {e}")
    
    async def export_customers(
        self,
        organization_id: UUID,
        customers: List[Dict[str, Any]],
        dataset: str,
        table: str = "customers",
        full_refresh: bool = False
    ) -> int:
        """
        Export customers to BigQuery.
        
        Args:
            organization_id: Organization ID
            customers: List of customer dictionaries
            dataset: Dataset ID
            table: Table name
            full_refresh: If True, truncate table before insert
            
        Returns:
            Number of rows exported
        """
        # Create dataset and table
        await self.create_dataset(dataset)
        
        schema = [
            bigquery.SchemaField("id", "STRING"),
            bigquery.SchemaField("organization_id", "STRING"),
            bigquery.SchemaField("external_ids", "JSON"),
            bigquery.SchemaField("anonymous_id", "STRING"),
            bigquery.SchemaField("traits", "JSON"),
            bigquery.SchemaField("computed_traits", "JSON"),
            bigquery.SchemaField("engagement_score", "FLOAT"),
            bigquery.SchemaField("lifetime_value", "FLOAT"),
            bigquery.SchemaField("churn_risk", "FLOAT"),
            bigquery.SchemaField("recency_days", "FLOAT"),
            bigquery.SchemaField("frequency_score", "FLOAT"),
            bigquery.SchemaField("monetary_value", "FLOAT"),
            bigquery.SchemaField("first_seen_at", "TIMESTAMP"),
            bigquery.SchemaField("last_seen_at", "TIMESTAMP"),
            bigquery.SchemaField("created_at", "TIMESTAMP"),
            bigquery.SchemaField("updated_at", "TIMESTAMP"),
            bigquery.SchemaField("exported_at", "TIMESTAMP"),
        ]
        
        await self.create_table(dataset, table, schema)
        
        # Prepare data
        export_data = []
        for customer in customers:
            export_data.append({
                "id": customer.get("id"),
                "organization_id": str(organization_id),
                "external_ids": json.dumps(customer.get("external_ids", {})),
                "anonymous_id": customer.get("anonymous_id"),
                "traits": json.dumps(customer.get("traits", {})),
                "computed_traits": json.dumps(customer.get("computed_traits", {})),
                "engagement_score": customer.get("engagement_score", 0),
                "lifetime_value": customer.get("lifetime_value", 0),
                "churn_risk": customer.get("churn_risk", 0),
                "recency_days": customer.get("recency_days"),
                "frequency_score": customer.get("frequency_score"),
                "monetary_value": customer.get("monetary_value"),
                "first_seen_at": customer.get("first_seen_at"),
                "last_seen_at": customer.get("last_seen_at"),
                "created_at": customer.get("created_at"),
                "updated_at": customer.get("updated_at"),
                "exported_at": datetime.utcnow().isoformat()
            })
        
        write_disposition = "WRITE_TRUNCATE" if full_refresh else "WRITE_APPEND"
        return await self.load_from_json(dataset, table, export_data, write_disposition)
    
    async def export_events(
        self,
        organization_id: UUID,
        events: List[Dict[str, Any]],
        dataset: str,
        table: str = "events",
        full_refresh: bool = False
    ) -> int:
        """
        Export events to BigQuery.
        
        Args:
            organization_id: Organization ID
            events: List of event dictionaries
            dataset: Dataset ID
            table: Table name
            full_refresh: If True, truncate table before insert
            
        Returns:
            Number of rows exported
        """
        await self.create_dataset(dataset)
        
        schema = [
            bigquery.SchemaField("id", "STRING"),
            bigquery.SchemaField("organization_id", "STRING"),
            bigquery.SchemaField("customer_id", "STRING"),
            bigquery.SchemaField("anonymous_id", "STRING"),
            bigquery.SchemaField("event_type", "STRING"),
            bigquery.SchemaField("event_name", "STRING"),
            bigquery.SchemaField("properties", "JSON"),
            bigquery.SchemaField("context", "JSON"),
            bigquery.SchemaField("timestamp", "TIMESTAMP"),
            bigquery.SchemaField("session_id", "STRING"),
            bigquery.SchemaField("campaign_id", "STRING"),
            bigquery.SchemaField("source", "STRING"),
            bigquery.SchemaField("created_at", "TIMESTAMP"),
            bigquery.SchemaField("exported_at", "TIMESTAMP"),
        ]
        
        await self.create_table(dataset, table, schema)
        
        export_data = []
        for event in events:
            export_data.append({
                "id": event.get("id"),
                "organization_id": str(organization_id),
                "customer_id": event.get("customer_id"),
                "anonymous_id": event.get("anonymous_id"),
                "event_type": event.get("event_type"),
                "event_name": event.get("event_name"),
                "properties": json.dumps(event.get("properties", {})),
                "context": json.dumps(event.get("context", {})),
                "timestamp": event.get("timestamp"),
                "session_id": event.get("session_id"),
                "campaign_id": event.get("campaign_id"),
                "source": event.get("source"),
                "created_at": event.get("created_at"),
                "exported_at": datetime.utcnow().isoformat()
            })
        
        write_disposition = "WRITE_TRUNCATE" if full_refresh else "WRITE_APPEND"
        return await self.load_from_json(dataset, table, export_data, write_disposition)
    
    async def export_attribution(
        self,
        organization_id: UUID,
        attributions: List[Dict[str, Any]],
        dataset: str,
        table: str = "attribution"
    ) -> int:
        """
        Export attribution data to BigQuery.
        
        Args:
            organization_id: Organization ID
            attributions: List of attribution dictionaries
            dataset: Dataset ID
            table: Table name
            
        Returns:
            Number of rows exported
        """
        await self.create_dataset(dataset)
        
        schema = [
            bigquery.SchemaField("id", "STRING"),
            bigquery.SchemaField("organization_id", "STRING"),
            bigquery.SchemaField("customer_id", "STRING"),
            bigquery.SchemaField("conversion_event_id", "STRING"),
            bigquery.SchemaField("attribution_model", "STRING"),
            bigquery.SchemaField("touchpoint_id", "STRING"),
            bigquery.SchemaField("touchpoint_type", "STRING"),
            bigquery.SchemaField("channel", "STRING"),
            bigquery.SchemaField("campaign_id", "STRING"),
            bigquery.SchemaField("attribution_percentage", "FLOAT"),
            bigquery.SchemaField("attributed_revenue", "FLOAT"),
            bigquery.SchemaField("time_to_conversion_hours", "FLOAT"),
            bigquery.SchemaField("created_at", "TIMESTAMP"),
            bigquery.SchemaField("exported_at", "TIMESTAMP"),
        ]
        
        await self.create_table(dataset, table, schema)
        
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
                "created_at": attr.get("created_at"),
                "exported_at": datetime.utcnow().isoformat()
            })
        
        return await self.load_from_json(dataset, table, export_data)
    
    async def validate_connection(self) -> bool:
        """
        Test BigQuery connection.
        
        Returns:
            True if connection is valid
        """
        try:
            client = self._get_client()
            # Try to list datasets
            datasets = list(client.list_datasets(max_results=1))
            return True
        except Exception as e:
            logger.error(f"BigQuery connection validation failed: {e}")
            return False
    
    async def get_table_schema(self, dataset_id: str, table_id: str) -> List[Dict[str, Any]]:
        """
        Get schema for a table.
        
        Args:
            dataset_id: Dataset ID
            table_id: Table ID
            
        Returns:
            List of column definitions
        """
        client = self._get_client()
        
        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        table = client.get_table(table_ref)
        
        return [
            {
                "name": field.name,
                "type": field.field_type,
                "mode": field.mode,
                "description": field.description
            }
            for field in table.schema
        ]
