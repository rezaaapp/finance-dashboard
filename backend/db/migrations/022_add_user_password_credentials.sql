-- One-way password credentials for internally provisioned UAT users.
-- Plaintext passwords are never stored.

create table if not exists user_password_credentials (
  user_id uuid primary key
    references users(id)
    on delete cascade,
  password_hash text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

drop trigger if exists set_user_password_credentials_updated_at
  on user_password_credentials;
create trigger set_user_password_credentials_updated_at
before update on user_password_credentials
for each row
execute function set_updated_at();
