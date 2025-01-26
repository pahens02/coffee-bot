-- Tables
CREATE TABLE brewing_logs (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    user_name TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    channel TEXT NOT NULL
);

CREATE TABLE selected_brewers (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    user_name TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES brewing_logs(user_id)
);

CREATE TABLE last_cup_logs (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    user_name TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES brewing_logs(user_id)
);

CREATE TABLE brewing_jobs (
    id UUID PRIMARY KEY,
    execute_at TIMESTAMP NOT NULL,
    payload JSONB NOT NULL,
    channel TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() ,
    brew_id TEXT NOT NULL,
    status TEXT NOT NULL,
    CONSTRAINT fk_brew_id FOREIGN KEY (brew_id) REFERENCES brewing_logs(id)
);

CREATE TABLE refutations (
    id SERIAL PRIMARY KEY,
    accusation_id UUID NOT NULL,
    accused_id TEXT NOT NULL,
    accused_name TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    CONSTRAINT fk_accusation_id FOREIGN KEY (accusation_id) REFERENCES accusations(id)
);

CREATE TABLE votes (
    id SERIAL PRIMARY KEY,
    accusation_id UUID NOT NULL,
    voter_id TEXT NOT NULL,
    voter_name TEXT NOT NULL,
    vote TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    CONSTRAINT fk_accusation_id FOREIGN KEY (accusation_id) REFERENCES accusations(id)
);

CREATE TABLE accusations (
    id UUID PRIMARY KEY,
    accuser_id TEXT NOT NULL,
    accuser_name TEXT NOT NULL,
    accused_id TEXT NOT NULL,
    accused_name TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    refuted BOOLEAN DEFAULT FALSE,
    judged BOOLEAN DEFAULT FALSE
);

CREATE TABLE refutations (
    id SERIAL PRIMARY KEY,
    accusation_id UUID NOT NULL REFERENCES accusations(id) ON DELETE CASCADE,
    accused_id TEXT NOT NULL,
    accused_name TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE TABLE votes (
    id SERIAL PRIMARY KEY,
    accusation_id UUID NOT NULL REFERENCES accusations(id) ON DELETE CASCADE,
    voter_id TEXT NOT NULL,
    voter_name TEXT NOT NULL,
    vote TEXT CHECK (vote IN ('accept', 'reject')),
    timestamp TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_vote UNIQUE (accusation_id, voter_id)
);


-- Views
CREATE VIEW brew_leaderboard AS
  SELECT user_name, COUNT(*) AS brew_count
  FROM brewing_logs
  GROUP BY user_name
  ORDER BY brew_count DESC;

CREATE VIEW last_cup_leaderboard AS
  SELECT user_name, COUNT(*) AS times_last_cup
  FROM last_cup_logs
  GROUP BY user_name
  ORDER BY times_last_cup DESC;

CREATE VIEW acussed_leaderboard as
SELECT accused_name, COUNT(*) AS accusations
FROM accusations
GROUP BY accused_name
ORDER BY accusations DESC;

CREATE VIEW acusser_leaderboard as
SELECT accuser_name, COUNT(*) AS accusations_made
FROM accusations
GROUP BY accuser_name
ORDER BY accusations_made DESC;


-- Functions
CREATE OR REPLACE FUNCTION public.execute_raw_sql(sql TEXT)
RETURNS TABLE(user_name TEXT, count INTEGER)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY EXECUTE sql;
END;
$$;

CREATE OR REPLACE FUNCTION notify_coffee_ready()
RETURNS TRIGGER AS $$
BEGIN
  -- Schedule the notification for 10 minutes later
  INSERT INTO brewing_jobs (brew_id, execute_at, payload)
  VALUES (
    NEW.id,
    now() + interval '10 minutes',
    jsonb_build_object(
      'text', '☕ Coffee is ready!',
      'channel', NEW.channel
    )
  );

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER brew_insert
AFTER INSERT ON brewing_logs
FOR EACH ROW EXECUTE FUNCTION notify_coffee_ready();

-- If you have multiple coffee channels you will need to make this procedure with a unique name for each channel/webhook
CREATE OR REPLACE PROCEDURE process_brewing_jobs()
LANGUAGE plpgsql AS $$
DECLARE
  job brewing_jobs%ROWTYPE;
BEGIN
  FOR job IN
    SELECT * FROM brewing_jobs WHERE execute_at <= now() AND status = 'pending'
  LOOP
    BEGIN
      -- Mark the job as processing
      UPDATE brewing_jobs
      SET status = 'processing'
      WHERE id = job.id;

      -- Send the HTTP POST request
      PERFORM net.http_post(
        url := 'YOUR WEBHOOK',
        headers := '{"Content-Type": "application/json"}'::jsonb,
        body := job.payload
      );

      -- Mark the job as processed
      UPDATE brewing_jobs
      SET status = 'processed'
      WHERE id = job.id;

      RAISE NOTICE 'Successfully processed job: %, Channel: %', job.id, job.payload->>'channel';
    EXCEPTION
      WHEN OTHERS THEN
        -- Log failure and retry later
        RAISE NOTICE 'Failed to process job: %, Error: %', job.id, SQLERRM;
        UPDATE brewing_jobs
        SET status = 'failed'
        WHERE id = job.id;
    END;
  END LOOP;
END;
$$;


-- Cron Jobs
SELECT cron.schedule(
    'process_brewing_jobs',
    '*/1 * * * *', -- Every minute
    'CALL process_brewing_jobs();'
);

SELECT cron.schedule(
    'cleanup_brewing_jobs',
    '0 0 * * *',  -- Every day at midnight
    'DELETE FROM brewing_jobs WHERE status = ''processed'' AND execute_at < now() - interval ''1 day'';'
);
