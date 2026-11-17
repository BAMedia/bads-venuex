Urban Concierge email signup Worker.

Collects addresses only; it does not send mail. Live endpoint:
https://uc-signup.scootrlink.workers.dev/subscribe

Export the list (from this directory, with an account API token set):

npx wrangler d1 execute uc-signup --remote --command "SELECT email, created_at, source, consent FROM subscribers ORDER BY created_at"
