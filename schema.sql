drop table if exists users;
drop table if exists threads;
drop table if exists messages;


create table users (
  user_id text,     -- string (uuid1)
  user_name text,   -- string
  auth_hash text,   -- string (sha256 hash)
  quip text,        -- string (possibly empty)
  bio text,         -- string (possibly empty)
  color int,        -- int (from 0 to 8)
  is_admin int,     -- bool
  created real      -- floating point unix timestamp (when this user registered)
);


create table threads (
  thread_id text,   -- uuid string
  author text,      -- string (uuid1, user.user_id)
  title text,       -- string
  last_mod real,    -- floating point unix timestamp (of last post or post edit)
  created real,     -- floating point unix timestamp (when thread was made)
  reply_count int   -- integer (incremental, starting with 0)
);


create table messages (
  thread_id text,   -- string (uuid1 of parent thread)
  post_id int,      -- integer (incrementing from 1)
  author text,      -- string (uuid1, user.user_id)
  created real,     -- floating point unix timestamp (when reply was posted)
  edited int,       -- bool
  body text         -- string
);
