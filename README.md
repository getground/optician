# Optician
Optician automatically generates your LookML views from your database models.

Optician was developped at GetGround, where we use dbt, BigQuery and Looker, so some of its usage is aligned with these tools' paradigm.

Optician has 3 features:
- LookML generator: this is the main feature, that reads the table schema from database and creates the LookML base view
- [Optional] Track differences of models between tables in two distinct schemas in the same database, which are meant to correspond to your development and production schemas, in order to identify which models need to be synced.
- [Optional] Commit the LookML view files to your Looker repository (GitHub supported only at the moment)

Assumptions:
- The fields in your tables have descriptions (supported by some databases only). If you use dbt, you can use `persist-docs` to save the fields descriptions in the database (see [dbt docs](https://docs.getdbt.com/reference/resource-configs/persist_docs)).
- Your Looker project is structured with base, standard and logical layers, following [this approach](https://www.spectacles.dev/post/fix-your-lookml-project-structure). Optician helps you create and update your base layer, without any measures.

## Setup

1. Create the Optician configuration file `.optician/config.json` (you can name it another way) somewhere in your computer (we suggest in the dbt or Looker repo)
2. Create the environment variable `OPTICIAN_CONFIG_FILE` which will be the absolute path to that file
3. You need to be able to connect to your database. For BigQuery, you can connect either by Oauth or Service Account.
4. [Optional] Create an environment variable `GH_TOKEN` for your GitHub personal token. You need to create this token in [GitHub](https://github.com/settings/tokens) with read:project, repo, user:email permissions. This will allow you to commit your Looker views directly to the Looker repository.

### Config file

The config file allows you to customise your LookML views. It supports the following options:

- `hide_all_fields`: Defaults to false. If set to true, all fields in the LookML view will be hidden in Looker.

- `timeframes`: The list of timeframes to use for your time dimension group fields. It uses the following timeframes as default:
    ```json
    "timeframes": [
            "raw",
            "time",
            "date",
            "week",
            "month",
            "month_name",
            "month_num",
            "quarter",
            "quarter_of_year",
            "year"
        ]
    ```

- `capitalize_ids`: Defaults to True. If your field name contains "Id", it will be replaced by "ID". You can set it to false if it's messing up with any other field names.

- `primary_key_columns`: List of field names to be assumed to be a primary key in Looker. E.g: ` "primary_key_columns": ["pk", "id", "primary_key"]`.

- `ignore_column_types`: List of database field types to be ignored on the LookML creation. E.g: `"ignore_column_types": ["GEOGRAPHY", "ARRAY"]`

- `ignore_modes`: List of database field modes that will be ignored on the LookML creation. E.g: `"ignore_modes": ["REPEATED"]`

- `time_suffixes`: List of suffixes on your database field names to be ommitted in the Looker field names. E.g. `"time_suffixes": ["_at", "_date", "_time", "_ts", "_timestamp", "_datetime"]` will mean that the field `created_at` will be named `created` in Looker.

- `order_by`: Defaults to `alpha`. How to order the fields in the LookML view. Use `alpha` for alphabetical order or `table` to use the same order as in your database table.

Example of a config file:

```json
{
    "primary_key_columns": ["id", "pk", "primary_key"],
    "ignore_column_types": ["GEOGRAPHY", "ARRAY"],
    "ignore_modes": ["REPEATED"],
    "timeframes":[
        "raw",
        "time",
        "date",
        "week",
        "month",
        "month_name",
        "month_num",
        "quarter",
        "quarter_of_year",
        "year"
    ],
    "hide_all_fields": false,
    "capitalize_ids": true,
    "time_suffixes": ["_at", "_date", "_time", "_ts", "_timestamp", "_datetime"],
    "order_by": "alpha"
}
```



### Install

You can install optician from a PyPi repository. We suggest you install it into a virtual environment.

```shell
pip install optician[bigquery]
``````


## How to contribute

We are only supporting BigQuery at the moment, but you are able to contribute by extending our DbClient class for your database.

In order to contribute, fork this repository, develop on a new branch and then open a pull request.

pre commit
