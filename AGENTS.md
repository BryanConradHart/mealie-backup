# Mealie-backup
[[README.md]] contains important information about the intention of the project, and how users configure and interact with it.

## Requirements
1. Produce code that is to be packaged as a docker image, and deployed in docker compose
2. Produce the required docker artifacts to publish the docker container in github.
3. According to a schedule, use the API token provided in the docker env to make a backup.
4. Make daily backups
5. Retention policy (GFS / DWMY): After each backup, inspect all existing backups and delete any that do not meet the retention rules.
    1. Calendar periods (week/month/year) should be deterministic (e.g., ISO week/calendar month).
    2. Always prefer the latest backup in a period as the representative snapshot.
    3. Default to 1 year of backups.
    4. Default to 6 months of backups.
    5. Default to 4 weeks of backups.
    6. default to 7 days of backups.
7. Validate the configuration on startup

## Deliverables
1. Docker image that can be [published to github](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images)
2. Example docker compose service in [[README.md]] that can be pasted into a user's Mealie compose file, including a working healthcheck.
3. Passing unit test suite.
4. GitHub Actions workflow that automatically builds and publishes the Docker image to GitHub Container Registry (ghcr.io) on releases, using free GitHub features.

## Technical Guidance
1. This project will be deployed as a docker container in docker compose.
2. The language used to write the project should be selected for ease of human understandability and suitability for the project.
3. Strive to decrease complexity.
4. Strive to make code that is easy to understand.
5. This will be published to github.
6. Use the Mealie API to create and delete backups.
7. Use consistent naming conventions.
8. Provide unit tests to confirm functionality works, that can be run in VS Code or in a CI/CD pipeline.

# Resources
1. [Mealie API explainer](https://docs.mealie.io/documentation/getting-started/api-usage/)
    - Each instance of mealie has its own API docs, which can be found by going to the `/docs` path of the mealie instance.
    - The API docs of specific note are the ones on backups: `/docs#/Admin%3A%20Backups`
    - If you need to read specific API specs, ask the user for the URL to their mealie instance.
        - alternatively, use the [mealie demo instance](https://demo.mealie.io/docs)