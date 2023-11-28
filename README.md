## Mina Payout Process

### What the service can do

Calculate MINA rewards for delegators of specified validator and send payouts. Payout processing frequency - once in epoch.

### Install

Create copy of *.template files with no .template extensions and specify your data if necessary.

To run POSTGRESQL be sure that `postgres/docker-entrypoint-initd.d/create_user.sql`exists and contains correct data.

Provide permissions to executable files:

    chmod +x postgres/run.sh
    chmod +x build.sh
    chmod +x run.sh
    chmod +x run_tests.sh

Start POSTGRESQL:
    
    ./postgres/run.sh

Build docker image:

    ./build.sh

Run service:

    ./run.sh

### Settings

Please provide your config data in config.conf file.

### Disclaimer

Calculation is based on https://github.com/garethtdavies/mina-payout-script