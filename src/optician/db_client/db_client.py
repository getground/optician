from importlib import import_module


class DbClient:
    SUPPORTED_DATABASES = ["bigquery"]

    def __init__(self, db_type: str, credentials: dict):
        self.db_type = db_type
        self.credentials = credentials
        self.db_client = None

        if self.db_type == "bigquery":
            self.db_client = BQClient(
                project_id=self.credentials.get("project_id", None),
                service_account=self.credentials.get("service_account", None),
            )
        else:
            raise Exception(f"Database type {self.db_type} not supported")

    def get_table(self, *args, **kwargs):
        return self.db_client.get_table(*args, **kwargs)

    def list_tables(self, *args, **kwargs):
        return self.db_client.list_tables(*args, **kwargs)

    # Defining the method in the client class since the definition
    # may differ between databases
    def is_nested_field(self, field):
        return self.db_client.is_nested_field(field)


class BQClient:
    def __init__(self, project_id: str, service_account: str = None):
        bigquery = import_module("google.cloud.bigquery")

        self.project_id = project_id
        if not self.project_id:
            raise ValueError("Project ID is required for BigQuery client")
        self.service_account = service_account

        if self.service_account:
            # Create BigQuery client with service account
            self.bq = bigquery.Client.from_service_account_json(
                self.service_account, project=self.project_id
            )
        else:
            # Create BigQuery client with oauth
            self.bq = bigquery.Client(project=self.project_id)

    @staticmethod
    def is_nested_field(field):
        return field.internal_type == "RECORD" and field.mode == "NULLABLE"

    def get_client(self):
        return self.bq

    def get_table(self, dataset_id: str, table_id: str):
        # Get BigQuery table from API
        bq_table_ref = self.bq.dataset(dataset_id).table(table_id)
        bq_table = self.bq.get_table(bq_table_ref)

        # Create Table instance
        table = Table(name=bq_table.table_id, internal_schema=bq_table.schema)

        # Create Field instances for each field in the table
        for schema_field in table.internal_schema:
            field = Field(
                name=schema_field.name,
                internal_type=schema_field.field_type,
                mode=schema_field.mode,
                description=schema_field.description,
            )

            # If the field is a nested field, add the nested fields to the schema
            if self.is_nested_field(field):
                for nested_field in schema_field.fields:
                    nested_field = Field(
                        name=nested_field.name,
                        internal_type=nested_field.field_type,
                        mode=nested_field.mode,
                        description=nested_field.description,
                    )
                    field.add_nested_field(nested_field)

            table.add_field_to_schema(field=field)
        return table

    def list_tables(self, dataset_id: str):
        dataset_ref = self.bq.dataset(dataset_id)
        tables = self.bq.list_tables(dataset_ref)
        return [self.get_table(dataset_id, table.table_id) for table in tables]


class Field:
    def __init__(
        self,
        name: str,
        internal_type: str,
        mode: str,
        description: str,
    ) -> None:
        """Initialisation of the field

        Args:
            name (str): Name of the field
            internal_type (str): Type of the field. Depends on the data warehouse engine.
            mode (str): Mode of the field. In BigQuery, can be NULLABLE, REQUIRED or REPEATED.
            description (str): Description of the field.
        """
        self.name = name
        self.internal_type = internal_type
        self.description = description
        self.mode = mode
        self.fields = []

    def __eq__(self, other):
        if not isinstance(other, Field):
            return False
        return (
            self.name == other.name
            and self.internal_type == other.internal_type
            and self.mode == other.mode
            and self.description == other.description
            and self.fields == other.fields
        )

    def get_name(self):
        return self.name

    def get_internal_type(self):
        return self.internal_type

    def get_mode(self):
        return self.mode

    def get_description(self):
        return self.description

    def add_nested_field(self, field):
        self.fields.append(field)


class Table:
    def __init__(self, name: str, internal_schema) -> None:
        """Initialisation of the table.

        Args:
            name (str): Name of the table in the dbt dataset.
            internal_schema (_type_): Object from the client that contains the table schema.
        """
        self.name = name
        self.description = None
        self.internal_schema = internal_schema
        self.schema = []

    def __eq__(self, other):
        if not isinstance(other, Table):
            return False

        return (
            self.name == other.name
            and self.description == other.description
            and self.schema == other.schema
        )

    def add_field_to_schema(self, field: Field):
        self.schema.append(field)

    def get_table_name(self):
        return self.name

    def get_internal_schema(self):
        return self.internal_schema

    def get_schema(self):
        return self.schema

    def get_schema_as_dict(self):
        return self.schema.__dict__
