-- Stage 6 identity: demo credentials and server-side sessions.
--
-- The project still has no production identity provider. This migration adds a
-- self-contained demo credential store (argon2id hashes) and revocable session
-- tokens so the storefront can hold a customer or operator session instead of
-- reaching for a fixed server-side bearer value.
BEGIN;

CREATE TABLE account_credentials (
    principal_id uuid PRIMARY KEY REFERENCES account_principals (principal_id) ON DELETE CASCADE,
    password_hash text NOT NULL CHECK (password_hash LIKE '$argon2%'),
    changed_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Back-office principals have no customer row, so they need their own login
-- identifier. Customer principals continue to sign in with their email.
ALTER TABLE account_principals ADD COLUMN login_email text UNIQUE
    CHECK (login_email IS NULL OR (login_email = lower(login_email) AND position('@' IN login_email) > 1));

CREATE TABLE sessions (
    session_id uuid PRIMARY KEY,
    principal_id uuid NOT NULL REFERENCES account_principals (principal_id) ON DELETE CASCADE,
    token_hash text NOT NULL UNIQUE CHECK (length(token_hash) = 64),
    surface text NOT NULL CHECK (surface IN ('customer', 'operator')),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at timestamptz NOT NULL,
    last_seen_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at timestamptz,
    CHECK (expires_at > created_at)
);

CREATE INDEX sessions_principal_expiry_idx ON sessions (principal_id, expires_at DESC);
CREATE INDEX sessions_expiry_idx ON sessions (expires_at) WHERE revoked_at IS NULL;

-- A session surface must match the account type: customer sessions belong to
-- customer principals, operator sessions to back-office principals.
CREATE OR REPLACE FUNCTION session_surface_matches() RETURNS trigger AS $$
DECLARE
    account text;
BEGIN
    SELECT account_type INTO account
    FROM account_principals
    WHERE principal_id = NEW.principal_id;
    IF account IS NULL OR NOT (
        (NEW.surface = 'customer' AND account = 'customer') OR
        (NEW.surface = 'operator' AND account = 'backoffice')
    ) THEN
        RAISE EXCEPTION 'session surface does not match the principal account type';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sessions_surface_check
    BEFORE INSERT OR UPDATE OF principal_id, surface ON sessions
    FOR EACH ROW EXECUTE FUNCTION session_surface_matches();

-- Demo credentials live in the seed file: migrations run before seeds, so a
-- credential row cannot reference a principal that does not exist yet.

COMMIT;
