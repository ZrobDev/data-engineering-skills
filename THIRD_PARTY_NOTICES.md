# Third-party notices

This repo bundles no third-party content. `skills/de-vendors/vendors.toml` only **points at**
vendor repositories, pinned by commit. `de-vendors` fetches them into the user's own project
under each vendor's licence. Pins as of 2026-11-09:

| Vendor | Repository | Commit | Licence |
|---|---|---|---|
| dbt Labs | dbt-labs/dbt-agent-skills | b8facde20b7a92c40ce3e6b86b71c4b92aa44040 | Apache-2.0 |
| Astronomer | astronomer/agents | 35b9610bb2710c37ca11326c4cbf7818b6725fec | Apache-2.0 |
| Databricks | databricks/databricks-agent-skills | b079942c0fcad01ec7afc2c37d816c8f1345323a | see repo (NOASSERTION) |
| Snowflake | snowflake-labs/coco-skills | 32c70bebac600edc8a712304c88a05b0b7b43382 | none declared |
| AWS | aws/agent-toolkit-for-aws | 6d6948da26c9505fd59ebd5ccaaa68d7cdced5b7 | Apache-2.0 |
| DuckDB | duckdb/duckdb-skills | 7feda8e01e22bc0886c86123f3884947e36d8c69 | MIT |
| dltHub | dlt-hub/dlthub-ai-workbench | 413c3b48ea2f30aa9ccadbf2f79d1be27d1f4ee7 | see repo (NOASSERTION) |
| Microsoft | microsoft/skills | 84666abf77c6b09ed431ab09c516891d0514710e | MIT |
| Anthropic | anthropics/knowledge-work-plugins | e050c2ec856373787143d7057663a6ebd1277df3 | Apache-2.0 |

`de-vendors` refuses licences that are not open (NONE, NOASSERTION) unless the user passes
`--accept-license` after reading the repo's terms.
