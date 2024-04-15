# Optician
Optician automatically generates your LookML views from your database models.

Optician was created at [GetGround](https://www.getground.co.uk/), where we use dbt, BigQuery and Looker, so you may realise that its usage may be aligned with this data stack paradigm.

Optician has 3 features:
- LookML generator: this is the main feature, that reads the table schemas from database and creates the LookML base views
- [Optional] Track differences of models between tables in two distinct schemas in the same database, which are meant to correspond to your development and production schemas, in order to identify which models need to be synced.
- [Optional] Commit the LookML view files to your Looker repository (only supports GitHub at the moment)

Assumptions:
- The fields in your tables have descriptions (supported by some databases only). If you use dbt, you can use `persist-docs` to store the fields descriptions in the database (see [dbt docs](https://docs.getdbt.com/reference/resource-configs/persist_docs)).
- Your Looker project is structured with base, standard and logical layers, following [this approach](https://www.spectacles.dev/post/fix-your-lookml-project-structure). Optician helps you create and update your base layer, without any measures.

## Installation

You can install optician from a PyPi repository. We suggest you install it into a virtual environment.
Please specify which database (or databases) you will be using, as in the example below.

```shell
pip install "optician[bigquery]"
```

## Setup
1. Create the Optician configuration file `.optician/config.json` (you can name it another way) somewhere in your computer (we suggest inside the dbt or Looker repo)
2. Create the environment variable `OPTICIAN_CONFIG_FILE` which will be the absolute path to the file created in 1
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


## Commands

### Diff Tracker

```bash
optician diff_tracker [options]
```

Use this command if you need to compare models between 2 different schemas in a database, supposed to correspond to your dev and prod targets. This command will return a list of the models which are different, ie, the ones you will need to update. This can be particulary useful when developping on your models, to know which models you will need to refresh in Looker.

#### Arguments

- `--db_type` (type: str, required: True): Database type (bigquery, redshift, snowflake).

- `--dataset1_name` (type: str, required: True): Name of Dataset 1.

- `--dataset2_name` (type: str, required: True): Name of Dataset 2.

- `--project` (type: str, required: True): Project ID.

- `--service_account` (type: str, required: False): Google Service Account.

- `--models` (type: str): List of model names to compare (comma-separated) or file path with a model per line. You can pass your dbt marts only, for example.

- `--output` (type: str): Output file path to write the results to.

- `--full-refresh` (action: Boolean, default: False): If you want to perform a full refresh of all models. This will return all models inputed (so this step does not run). This is only useful if you want to skip this command when refreshing all models, for example in a CI pipeline.

#### Example
```bash
optician diff_tracker \
    --db_type bigquery \
    --project my-database-name \
    --dataset1_name dbt_dev \
    --dataset2_name dbt_prod \
    --models tmp/marts.txt \
    --output tmp/diff.txt
```

### Generate LookML

```bash
optician generate_lookml [options]
```

This command created the LookML base views.

#### Arguments

- `--db_type` (type: str, required: True): Database type (bigquery, redshift, snowflake).

- `--project` (type: str, required: True): Project ID.

- `--dataset` (type: str, required: True): Dataset ID/database schema to read the models from.

- `--tables` (type: str, required: True): List of Table IDs separated by a comma or provide a file path with a table name per line. You can use the same file outputted by the `diff_tracker`, for example.

- `--output-dir` (type: str, required: False): Output Directory. If not specified, it will write the files to the current directory.

- `--override-dataset-id` (type: str, required: False): Override Dataset ID. For example, you may be developping and reading from a dev dataset, but you may want to create the LookML views pointing to your production dataset. Or you may have defined a constant in Looker for you dataset name
    ```lookml
    constant: dataset {
        value: "dbt_prod"
    }
    ```
    and set this option value to @{dataset} as in Example 2.

- `--service-account` (type: str, required: False): Service Account.

#### Examples

Example 1:
```bash
optician generate_lookml \
    --db_type bigquery \
    --project my-database-name \
    --dataset dbt_dev \
    --tables tmp/diff.txt \
    --override-dataset-id dbt_prod \
    --output tmp/lookml/
```

Example 2:
```bash
optician generate_lookml \
    --db_type snowflake \
    --project my-database-name \
    --dataset dbt_dev \
    --tables deals,contacts \
    --override-dataset-id @{dataset}
```

### Push to Looker

```bash
optician push_to_looker [options]
```

You can use this command to commit and push your LookML views generated to your Looker GitHub repository.

#### Arguments

- `--token` (type: str, required: True): GitHub Token.

- `--repo` (type: str, required: True): GitHub Repo.

- `--user-email` (type: str, required: False): GitHub User Email.

- `--input-dir` (type: str, required: True): Path that contains new files to be committed.

- `--output-dir` (type: str, required: True): Directory in the repo to write the LookML files to.

- `--branch-name` (type: str, required: True): Name of the branch to commit the changes to.

- `--base-branch` (type: str, default: "main"): Name of the base branch (e.g. main, master).

#### Examples

Example 1:
In this example we have the GitHub Token saved in an environment variable `$GH_TOKEN`. We are reading the views from the directory tmp/lookml that we have used as output in the `generate_lookml` command and we are writing the files to a folder _base in our repo.

```bash
optician push_to_looker \
    --token $GH_TOKEN \
    --repo mycompany/looker \
    --branch-name update-deals \
    --base-branch main \
    --input-dir tmp/lookml/ \
    --output-dir _base
```

## How to contribute

We are only supporting BigQuery at the moment, but you are able to contribute by updating the `db_client.py` file.

In order to contribute, fork this repository, develop on a new branch and then open a pull request.

Make sure you install all dependencies into a virtual environment and also install pre-commit `pre-commit install` so that the code is linted when committing.
