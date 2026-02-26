# Mealie-backup
This project is intended to be a simple solution for people who want to schedule their [mealie](https://mealie.io/) backups, and use docker compose.

## Why
Mealie has an [extensive API](https://docs.mealie.io/documentation/getting-started/api-usage/) that the ability to manage backups, but there is no way to schedule backups. This project is meant to fill that gap.

## How
Supply environment variables for api-token, mealie address, and optionally supply the daily, weekly, montly, and yearly retention. add the container to your mealie compose file, and redploy it. The intention is to keep everything as simple as possible.