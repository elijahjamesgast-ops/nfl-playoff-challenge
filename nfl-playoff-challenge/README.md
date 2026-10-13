# NFL Playoff Challenge — GitHub Pages starter

A free static website with a leaderboard, clickable team details, an eight-player roster builder, XML-backed team/player/score data, and optional public submission handling through Supabase + GitHub Actions.

## Rules
- QB ×1, RB ×2, WR ×3, TE ×1, K ×1
- One player per NFL team; no duplicate player
- All touchdowns a player scores or throws: 6 points each
- Field goals: 3 points each
- Cumulative points from the 2026-season NFL playoffs (January–February 2027)
- No owner-side team editing after submission
- No yardage or extra-point scoring unless you explicitly add rules

## Fast deployment
1. Create a new public GitHub repository, e.g. `nfl-playoff-challenge`.
2. Upload **the contents of this folder** to the repository root (including the hidden `.github` folder).
3. GitHub repository → **Settings → Pages** → **Deploy from a branch** → `main` → `/(root)` → Save.
4. Open the Pages URL displayed by GitHub. Your site can read the XML immediately. Team submission requires additional setup below.

## Owner edits (XML files)
- `data/players.xml`: add/remove players and update their NFL team abbreviations. Player `id` must remain stable after submissions. A player with team `FA` cannot be selected.
- `data/teams.xml`: edit, add, or remove teams directly in GitHub. Each `team` needs a unique `id`, `name`, `owner`, and exactly eight `pick` elements **in QB,RB,RB,WR,WR,WR,TE,K order**.
- `data/scores.xml`: set **cumulative** TDs, field goals and `adjustment` (positive or negative). The leaderboard automatically recalculates from this XML.
- `data/rules.xml`: rule values and slot definitions.

Example `teams.xml` team fragment (insert inside `<teams>`; replace all IDs with real players):
```xml
<team id="my-team-001" name="Sunday Champions" owner="Example Owner">
  <pick position="QB" playerId="josh-allen"/>
  <pick position="RB" playerId="saquon-barkley"/>
  <pick position="RB" playerId="bijan-robinson"/>
  <pick position="WR" playerId="ja-marr-chase"/>
  <pick position="WR" playerId="justin-jefferson"/>
  <pick position="WR" playerId="puka-nacua"/>
  <pick position="TE" playerId="george-kittle"/>
  <pick position="K" playerId="brandon-aubrey"/>
</team>
```
Example score fragment (insert inside `<scores>`):
```xml
<score playerId="josh-allen" touchdowns="4" fieldGoals="0" adjustment="-6"/>
```
The example above awards 18 points (4 × 6 − 6). Use adjustment for scoring corrections. **Do not count a QB's rushing TD twice**: touchdowns is the number of TDs the player threw *plus* personally scored.

## Enable anyone to submit (optional free-tier backend)
1. Create a Supabase project and run `data/schema.sql` in its SQL editor.
2. In `assets/config.js`, set `supabaseUrl` and `supabaseAnonKey` to your project's URL and **public anon/publishable key**. Never put a service-role key here.
3. In GitHub repository **Settings → Secrets and variables → Actions**, create `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` (the latter must remain private).
4. Enable Actions for the repository and run **Actions → Publish submissions to XML → Run workflow** to test. Scheduled sync runs every 30 minutes (GitHub schedules can be delayed).
5. New submissions are validated again by the sync script before publication; they will then appear on GitHub Pages after the commit is deployed.

**Limitations:** Without Supabase setup, the form validates but will explicitly refuse to save. With Supabase, anyone can submit without signing in, but submissions are publicly accessible only once synced into GitHub XML. The current database policy does not provide anti-spam or rate limiting; consider CAPTCHA / an Edge Function for a public launch. There is no authentication for owner names, and no limit on multiple entries per person. The public form cannot edit submissions, but you can modify published XML in GitHub. A later sync does not overwrite an existing team's XML record. If you delete a synced team in XML while leaving its submission in Supabase, the next sync will re-add it; delete the Supabase submission too to remove it permanently.

## Scoring updates
The **base build uses manual `data/scores.xml` updates**. Automatic score fetching is not implemented yet because it requires a selected, reliable NFL statistics provider and mapping of provider player IDs to these XML IDs. The XML score format is designed to accept a future GitHub Action that fetches playoff stats and applies manual adjustments. Do not assume scores are live until that is configured.

## Other launch checks
- `data/players.xml` is a **starter list**, not a confirmed 2027 playoff player pool. Check every player's team and playoff eligibility before accepting real entries.
- Scores are all zero until populated.
- The list of selectable teams currently includes non-playoff teams; filter/curate `players.xml` after playoff teams are known.
- Host the files with GitHub Pages or a local HTTP server (e.g. `python -m http.server 8000`), not by opening `index.html` directly.
- GitHub Pages and Supabase free tiers have usage limits and service terms that may change.
