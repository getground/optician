from optician.db_client import db_client as db
import os
import json
from optician.logger import Logger

CONSOLE_LOGGER = Logger().get_logger()

FIELD_TYPE_MAPPING = {
    "bigquery": {
        "INTEGER": "number",
        "INT64": "number",
        "FLOAT": "number",
        "FLOAT64": "number",
        "BIGNUMERIC": "number",
        "NUMERIC": "number",
        "BOOLEAN": "yesno",
        "BOOL": "yesno",
        "TIMESTAMP": "time",
        "TIME": "time",
        "DATE": "time",
        "DATETIME": "time",
        "STRING": "string",
        "ARRAY": "string",
        "GEOGRAPHY": "string",
        "BYTES": "string",
    }
}

DEFAULT_TIMEFRAMES = [
    "raw",
    "time",
    "date",
    "week",
    "month",
    "month_name",
    "month_num",
    "quarter",
    "quarter_of_year",
    "year",
]

CONFIG_OPTIONS = {
    "hide_all_fields": {"type": bool},
    "capitalize_ids": {"type": bool},
    "primary_key_columns": {"type": list, "subtype": str},
    "ignore_column_types": {"type": list, "subtype": str},
    "ignore_modes": {"type": list, "subtype": str},
    "timeframes": {"type": list, "subtype": str},
    "time_suffixes": {"type": list, "subtype": str},
    "order_by": {"type": str, "options": ["alpha", "table"]},
}


class Config:
    def __init__(self, config_file_path=None):
        self._config_file_path = config_file_path
        self._custom_config = self._read_custom_config()
        self._test_config()

    def _read_custom_config(self):
        if self._config_file_path is None:
            return {}
        else:
            try:
                return json.load(open(self._config_file_path))
            except:
                raise Exception("Invalid config file path")

    def get_property(self, property_name, default_value=None):
        if property_name in self._custom_config.keys():
            return self._custom_config.get(property_name)
        else:
            return default_value

    def _test_config(self):
        for property_name in self._custom_config.keys():
            property_value = self.get_property(property_name)
            if property_name not in CONFIG_OPTIONS.keys():
                raise Exception(f"Invalid config option: {property_name}")
            # check type
            if not isinstance(property_value, CONFIG_OPTIONS[property_name]["type"]):
                raise Exception(
                    f"Invalid type for config option {property_name}. Expected {CONFIG_OPTIONS[property_name]['type']}"
                )
            # check subtype
            if "subtype" in CONFIG_OPTIONS[property_name].keys():
                if len(property_value) > 0:
                    if not isinstance(
                        self.get_property(property_name)[0],
                        CONFIG_OPTIONS[property_name]["subtype"],
                    ):
                        raise Exception(
                            f"Invalid subtype for config option {property_name}. Expected {CONFIG_OPTIONS[property_name]['subtype']}"
                        )
            if "options" in CONFIG_OPTIONS[property_name].keys():
                if property_value not in CONFIG_OPTIONS[property_name]["options"]:
                    raise Exception(
                        f"Invalid value for config option {property_name}. Expected one of {CONFIG_OPTIONS[property_name]['options']}"
                    )


class LookMLGenerator:
    def __init__(self, client: db.DbClient, dataset_id: str):
        self.client = client
        self.dataset_id = dataset_id
        self._config_file_env_name = "OPTICIAN_CONFIG_FILE"
        self.config = Config(os.getenv(self._config_file_env_name, None))
        self.hide_all_fields = self.config.get_property("hide_all_fields", False)
        self.primary_key_column_names = self.config.get_property(
            "primary_key_columns", []
        )
        self.ignore_column_types = self.config.get_property("ignore_column_types", [])
        self.ignore_modes = self.config.get_property("ignore_modes", [])
        self.timeframes = self.config.get_property("timeframes", DEFAULT_TIMEFRAMES)
        self.time_suffixes = self.config.get_property("time_suffixes", [])
        self.order_by = self.config.get_property("order_by", "alpha")
        self.capitalize_ids = self.config.get_property("capitalize_ids", True)

    def _build_field_name(self, field_name: str):
        # remove underscores
        field_name = field_name.replace("_", " ")
        # title case
        field_name = field_name.title()
        if self.capitalize_ids:
            # capitalize any "id" in the field name
            field_name = field_name.replace("Id", "ID")
        return field_name

    def _get_looker_type(self, field: db.Field):
        # Default unknown types to string
        return FIELD_TYPE_MAPPING[self.client.db_type].get(
            field.internal_type, "string"
        )

    def _build_timeframes(self):
        tf = "timeframes: [\n"
        tf += "".join(f"      {tf},\n" for tf in self.timeframes[:-1])
        tf += f"      {self.timeframes[-1]}\n"
        tf += "    ]"
        return tf

    def process_field(self, field: db.Field, parent_field_name: str = None):
        field_name = field.name
        field_sql_name = field_name
        field_type = field.internal_type
        lookml_type = self._get_looker_type(field)
        is_nested_field = self.client.is_nested_field(field)
        field_mode = field.mode
        field_description = field.description
        pk = ""
        convert_ts = ""
        datatype = ""
        group_label = ""
        group_item_label = ""
        hidden = ""
        view_field = ""

        if field_type == "DATE":
            convert_ts = "convert_tz: no"
            datatype = "datatype: date"

        elif field_type == "DATETIME":
            datatype = "datatype: datetime"

        field_description = (
            '"' + field_description.rstrip().replace('"', "'") + '"'
            if field_description
            else '""'
        )

        if parent_field_name:
            field_sql_name = parent_field_name + "." + field_name
            group_item_label = (
                f'group_item_label: "{self._build_field_name(field_name)}"'
            )
            field_name = parent_field_name + "__" + field_name
            group_label = f'group_label: "{self._build_field_name(parent_field_name)}"'

        elif field_name in self.primary_key_column_names:
            pk = "primary_key: yes"

        if self.hide_all_fields:
            hidden = "hidden: yes"

        # Don't write these fields
        if field_mode is not None:
            if field_mode in self.ignore_modes:
                return ""

        if self.ignore_column_types:
            if field_type in self.ignore_column_types:
                return ""

        # Handle nested fields
        if is_nested_field:
            # Handle nested fields within a record field
            nested_fields = field.fields
            # Sort the nested fields by name or leave them in the order they are in
            if self.order_by == "alpha":
                nested_fields = sorted(nested_fields, key=lambda x: x.name)
            nested_output = ""
            for nested_field in nested_fields:
                # Recursively process the nested field
                nested_output += self.process_field(
                    nested_field, parent_field_name=f"{field_name}"
                )
            return nested_output

        # Handle time fields
        elif lookml_type == "time":
            timeframes = self._build_timeframes()
            # if field name ends with _at, _time, or _date
            if len(self.time_suffixes) > 0:
                for s in self.time_suffixes:
                    if field_name.endswith(s):
                        # split field name on underscore and remove last part
                        field_name = "_".join(field_name.split("_")[:-1])
                        break

            view_field = f"  dimension_group: {field_name} {{\n"
            view_field += f"    {hidden}\n"
            view_field += f"    description: {field_description}\n"
            view_field += f"    type: time\n"
            view_field += f"    {timeframes}\n"
            view_field += f"    {convert_ts}\n"
            view_field += f"    {datatype}\n"
            view_field += f"    sql: ${{TABLE}}.{field_sql_name} ;;\n"
            view_field += f"  }}\n"

        # Handle all other fields
        else:
            view_field = f"  dimension: {field_name} {{\n"
            view_field += f"    {hidden}\n"
            view_field += f"    {pk}\n"
            view_field += f"    {group_label}\n"
            view_field += f"    {group_item_label}\n"
            view_field += f"    description: {field_description}\n"
            view_field += f"    type: {lookml_type}\n"
            view_field += f"    sql: ${{TABLE}}.{field_sql_name} ;;\n"
            view_field += f"  }}\n"

        if view_field != "":
            # Remove any empty lines from the view field
            view_field = "\n".join(
                [ll.rstrip() for ll in view_field.splitlines() if ll.strip()]
            )
            view_field = "\n" + view_field + "\n"

        return view_field

    def generate_lookml_view(
        self,
        table_id: str,
        output_dir: str = None,
        view_name: str = None,
        override_dataset_id: str = None,
    ):
        # Generate LookML view
        if not view_name:
            view_name = table_id

        if override_dataset_id:
            sql_table_name = f"{override_dataset_id}.{table_id}"
        else:
            sql_table_name = f"{self.dataset_id}.{table_id}"

        view_output = f"view: {view_name} {{\n"
        view_output += f"  sql_table_name: `{sql_table_name}`;;\n"  # Include the SQL table name parameter

        table = self.client.get_table(self.dataset_id, table_id)

        # Sort the fields by name or leave them in the order they are in
        if self.order_by == "alpha":
            table.schema = sorted(table.schema, key=lambda x: x.name)

        for field in table.schema:
            view_field = self.process_field(field)
            view_output += view_field
        view_output += "\n}"

        # Write the LookML view to a file
        lookml_file_path = f"{view_name}.view.lkml"
        if output_dir:
            # create directory if it doesn't exist
            # with all permissions
            if not os.path.exists(output_dir):
                os.mkdir(output_dir)

            lookml_file_path = os.path.join(output_dir, lookml_file_path)

        with open(lookml_file_path, "w") as file:
            file.write(view_output)

        CONSOLE_LOGGER.info(f"LookML view written to {lookml_file_path}")

    def generate_batch_lookml_views(
        self, tables: list, output_dir: str = None, override_dataset_id: str = None
    ):
        for table in tables:
            self.generate_lookml_view(
                table_id=table,
                output_dir=output_dir,
                override_dataset_id=override_dataset_id,
            )
