# Optional: auto-invite buyers to the private repo

Stripe Payment Link → `checkout.session.completed` webhook → GitHub "add collaborator" (read access).
No database, and no billing code in the kit. This is a recipe plus one tested file (`invite_webhook.py`).
Nothing here is deployed for you.

## Setup (about 15 minutes, all in dashboards)
1. **Payment Link:** add a required custom text field labeled **GitHub username** ([Stripe: custom fields](https://docs.stripe.com/payment-links/customize)). Note the field key Stripe shows; set `INVITE_FIELD_KEY` if it isn't `githubusername`. Stripe warns against using custom fields for sensitive data, and a username isn't sensitive.
2. **GitHub token:** a fine-grained personal access token scoped to **only the private repo**, with repository permission **Administration: write**. That's what "Add a repository collaborator" requires ([GitHub REST docs](https://docs.github.com/en/rest/collaborators/collaborators#add-a-repository-collaborator)). Set an expiry date and a calendar reminder to rotate it.
3. **Host the app** anywhere that runs Python (the same Cloud Run project works: `uvicorn invite_webhook:app --app-dir tools/invite-webhook`). Env: `STRIPE_WEBHOOK_SECRET`, `GITHUB_TOKEN`, `GITHUB_REPO=owner/repo`.
4. **Stripe webhook endpoint:** `https://<host>/stripe/webhook`, event `checkout.session.completed` (add `checkout.session.async_payment_succeeded` if you enable delayed payment methods). Copy its signing secret.
5. **Test first** with `INVITE_DRY_RUN=1` and Stripe test mode, then switch to live keys.

## Behavior
| Case | Response | Effect |
|---|---|---|
| Bad or old signature (more than 5 min) | 400 | nothing |
| Not `checkout.session.completed`, or not paid | 200 `ignored` | nothing |
| Missing or invalid username, or GitHub user not found | 200 `manual_follow_up` | email the buyer (support inbox) |
| Paid, valid username | 200 `invited` / `already_collaborator` | GitHub emails the invite |
| GitHub 5xx/429 | 502 | Stripe retries later |

## Gotchas
- **GitHub limits repo invitations to 50 per repository per 24 hours** ([docs](https://docs.github.com/en/rest/collaborators/collaborators#add-a-repository-collaborator)). Launch spikes beyond that need a queue or an org/team approach.
- Invites expire if not accepted (GitHub sends reminders). Keep a "resend invite" reply ready.
- Refunds: removing access (`DELETE /repos/{owner}/{repo}/collaborators/{username}` on `charge.refunded`) is left manual in v1. A clone already made can't be revoked anyway.
- Signature check is hand-rolled (HMAC-SHA256 over `"{t}.{body}"`, per Stripe's scheme) to avoid a dependency. Stripe recommends its official library ([docs](https://docs.stripe.com/webhooks#verify-official-libraries)), so swap in `stripe.Webhook.construct_event` if you add the SDK.
- Only Stripe's server-to-server event grants access. Never unlock from the browser redirect.

Tests: `uv run pytest -q tools/invite-webhook` (dry run and mocked GitHub, no network).
