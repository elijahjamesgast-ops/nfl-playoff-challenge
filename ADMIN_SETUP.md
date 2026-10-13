# Admin upgrade setup — NFL Playoff Challenge

## 1. Back up your current repository

From your local clone, run `git pull --rebase origin main` before copying these upgrade files. Back up `assets/config.js`, `data/teams.xml`, `data/scores.xml`, and `data/players.xml`. **Do not replace these four files with the sample versions in the ZIP.** The upgrade ZIP contains a complete sample project, but you should copy ONLY the files listed below to your existing repository.

Copy these from the upgrade ZIP into the corresponding locations in your repository:

- `index.html`
- `assets/app.js`
- `scripts/sync_submissions.py`
- `.github/workflows/sync.yml`
- `data/admin_setup.sql` (setup reference, not served to visitors)
- `data/admin_applied.json` (initially `[]`; if it already exists, preserve it)

**Keep your existing `assets/config.js` unchanged**, because it contains your real public Supabase URL and publishable key. Keep all of your existing XML player/team/score data.

## 2. Create your admin login in Supabase

1. Open Supabase > Authentication > Users.
2. Add an email/password user for yourself (use a strong unique password; do not share it). If the dashboard creates a user without email confirmation, ensure it is confirmed.
3. Copy that user's **UUID** from the Auth users page.
4. Open SQL Editor, paste the contents of `data/admin_setup.sql`, and run it.
5. Run this second statement, replacing the placeholder with the actual UUID:

```sql
insert into public.admin_users(user_id)
values ('YOUR-ADMIN-AUTH-USER-UUID')
on conflict (user_id) do nothing;
```

Only UUIDs in `admin_users` can call `admin_command`. Never grant admin status based on an unverified email address. Do not add any database secret keys to public files.

## 3. Verify GitHub Actions secrets

Under GitHub repository Settings > Secrets and variables > Actions, ensure both are present:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

The service-role key goes **only** in GitHub Actions secrets. The website's `assets/config.js` uses your existing **publishable** key, not the service-role key.

Under Settings > Actions > General > Workflow permissions, allow **Read and write permissions** for the workflow to commit XML changes.

## 4. Push the upgrade

```cmd
git add index.html assets/app.js scripts/sync_submissions.py .github/workflows/sync.yml data/admin_setup.sql data/admin_applied.json
git commit -m "Add playoff administrator controls"
git push origin main
```

If push is rejected, stop and resolve the upstream changes using `git pull --rebase origin main`. Don't force-push.

## 5. Test

1. Open the GitHub Pages website and click **Admin**.
2. Sign in using the email/password user you created in Supabase Authentication.
3. Close submissions. Check that the Create Team page is blocked, and that a direct Supabase submission is rejected by the database trigger.
4. Reopen submissions.
5. Queue a small score correction. Open GitHub > Actions > **Publish submissions to XML** > **Run workflow**.
6. Check `data/scores.xml` on GitHub and refresh the leaderboard. Confirm the corrected points appear.
7. Edit a test team and run the workflow; verify `data/teams.xml` changed. Delete a test team, run again, and confirm it stays deleted.

## Important behavior

- Public visitors do not get administrator privileges. Login is checked server-side by `admin_command` against Supabase Auth UUIDs.
- The admin interface queues XML changes in Supabase. GitHub Actions applies them during the next sync (scheduled every ~30 minutes, or run manually).
- Existing XML team edits are not overwritten by the regular import of submissions. **Queued admin edits intentionally override an XML edit for the same team when processed.**
- Manual score corrections use `adjustment` in `scores.xml` and replace the prior adjustment value. If you later build an automated stats importer, make it preserve this field.
- The submission lock is enforced in Supabase, even if a visitor bypasses the browser interface. For a truly secure public launch, add server-side validation of positions, team uniqueness and eligible players to the submission endpoint as well; the current SQL only enforces eight picks, and the sync script rejects invalid rosters before publication.
- GitHub Pages is static; the published leaderboard still refreshes when GitHub XML is deployed, not instantly after submitting.
- Do not share your Supabase Auth password, JWT access token, service-role key, or database password.
