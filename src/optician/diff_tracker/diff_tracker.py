from optician.db_client import DbClient


class DiffTracker:
    def __init__(
        self,
        dataset1_name: str,
        dataset2_name: str,
        db_client: DbClient = None,
        models: list = None,
        full_refresh: bool = False,
    ):
        self.dataset1_name = dataset1_name
        self.dataset2_name = dataset2_name
        self.models = models
        self.db = db_client
        self.full_refresh = full_refresh

    def get_table_schemas(self, dataset_id: str):
        # Get list of tables in dataset that are also in models
        table_schemas = {}
        for table in self.db.list_tables(dataset_id):
            table_id = table.name
            if table_id in self.models:
                table_schemas[table_id] = table

        return table_schemas

    def get_diff_tables(self):
        results = {"new_models": [], "diff_models": [], "missing_models": []}

        # Get table schemas for dataset1
        dataset1_schemas = self.get_table_schemas(self.dataset1_name)

        # If full refresh, return all tables in dataset1
        if self.full_refresh == True:
            results["diff_models"] = list(dataset1_schemas.keys())
            return results

        # Get table schemas for dataset2
        dataset2_schemas = self.get_table_schemas(self.dataset2_name)

        # Compare schemas
        for table_name, schema1 in dataset1_schemas.items():
            if table_name in dataset2_schemas:
                schema2 = dataset2_schemas[table_name]
                if schema1 != schema2:
                    results["diff_models"].append(table_name)
            else:
                results["new_models"].append(table_name)

        for table_name in dataset2_schemas:
            if table_name not in dataset1_schemas:
                results["missing_models"].append(table_name)

        return results
