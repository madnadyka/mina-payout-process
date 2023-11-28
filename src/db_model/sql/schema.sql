CREATE TABLE IF NOT EXISTS epochs(
                           epoch INT4                   NOT NULL,
                           ledger_hash                  VARCHAR(64),
                           staking_balance              BIGINT,
                           staking_balance_foundation   BIGINT,
                           rewards_amount               BIGINT,
                           fee_amount                   BIGINT,
                           blocks_count                 INT4
                            );
CREATE UNIQUE INDEX IF NOT EXISTS epoch_i ON epochs USING BTREE (epoch);



CREATE TABLE IF NOT EXISTS blocks(
                           epoch INT4 NOT NULL,
                           block_height     INT4 NOT NULL,
                           supercharged_weighting   NUMERIC(20,16),
                           coinbase BIGINT,
                           fee_transfers_creator BIGINT,
                           fee_transfers_snarkers BIGINT,
                           fee_transfer_coinbase BIGINT,
                           timestamp BIGINT);
CREATE UNIQUE INDEX IF NOT EXISTS height_i ON blocks USING BTREE (block_height);



CREATE TABLE IF NOT EXISTS rewards(
                           public_key VARCHAR(128),
                           epoch INT4 NOT NULL,
                           block_height     INT4 NOT NULL,
                           reward_amount  BIGINT,
                           foundation SMALLINT,
                           timestamp BIGINT);
CREATE UNIQUE INDEX IF NOT EXISTS public_key_block_i ON rewards USING BTREE (public_key,block_height);


CREATE TABLE IF NOT EXISTS payouts(
                           id BIGSERIAL PRIMARY KEY,
                           public_key VARCHAR(128),
                           epoch INT4 NOT NULL,
                           payout_amount  BIGINT,
                           staking_balance BIGINT,
                           timed_weighting  INT4,
                           foundation SMALLINT,
                           payment_id TEXT,
                           status SMALLINT DEFAULT 0,
                           timestamp BIGINT);

CREATE UNIQUE INDEX IF NOT EXISTS payment_id_i ON payouts USING BTREE (payment_id);
CREATE UNIQUE INDEX IF NOT EXISTS public_key_epoch_i ON payouts USING BTREE (public_key,epoch);