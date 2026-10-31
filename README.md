# R7023E
## Oliver WItzel, Isaac Edwards, Petter Bäckman, Anton Damnberg

This projects aims to simulate a ground to S/C communication protocoll using docker container networks.
## Requirements
- Docker Desktop with Docker Compose
- No local Python installation is needed; dependencies are installed inside the containers.

## Run

Open two terminals in the project directory.

In the first terminal, start the OBC and leave it running:

docker compose up obc

In the second terminal, start the ground station:

docker compose run --rm --no-deps ground

The containers communicate over the Docker Compose network. The ground station writes its log to data/ground, and the payload log is stored in data/payload.

Write QUIT or Ctrl+C to stop ground and Ctrl+c for obc