# DC Concert Monitor — Cloud Edition

This version runs **on GitHub's servers**, not your Mac. It checks four DC-area
venues every Monday / Wednesday / Friday and sends a **push notification to your
phone** (via the free [ntfy](https://ntfy.sh) app) whenever a new show is added.
It works whether your laptop is on, asleep, or in your bag — and you can also
trigger a check on demand from your phone.

Venues watched: **Black Cat**, **IMP** (9:30 Club / The Anthem / Lincoln Theatre /
Merriweather), **Union Stage Presents** (Union Stage, Jammin' Java, Pearl Street,
The Howard, Miracle Theatre, Capital Turnaround), and **Songbyrd**.

---

## What's in this folder

```
monitor.py                      the checker (Python standard library only)
known_shows.json                the "memory" — 340 shows already seen (your current baseline)
new_shows_log.md                history of new finds (created on first new show)
.github/workflows/monitor.yml   the schedule + automation
```

---

## One-time setup (~10 minutes, no coding)

### 1. Pick your ntfy topic and install the app
1. Install **ntfy** on your phone (App Store / Google Play).
2. Choose a **topic name** — think of it as a private channel. Make it long and
   random so nobody else stumbles onto it, e.g. `bruno-dc-concerts-9f3k2x7q`.
3. In the ntfy app, tap **+** and **subscribe** to that exact topic name.
   (Leave the server as the default `ntfy.sh`.)

> Note: ntfy.sh topics are technically public to anyone who knows the name, which
> is why we use a random one. Concert listings aren't sensitive, but if you'd
> prefer it locked down, ntfy supports access tokens / self-hosting — ask and I'll
> adjust.

### 2. Put this folder on GitHub
1. Create a free account at https://github.com if you don't have one.
2. Click **New repository** → name it e.g. `concert-monitor` → set it **Private** →
   **Create repository**.
3. On the new repo page, click **uploading an existing file** and drag in the
   contents of this `cloud-version` folder — **including the `.github` folder**.
   (If drag-and-drop hides the `.github` folder, see the tip at the bottom.)
4. Commit the files.

### 3. Add your topic as a secret
1. In the repo, go to **Settings → Secrets and variables → Actions**.
2. Click **New repository secret**.
3. Name: `NTFY_TOPIC`  ·  Value: your topic from step 1 (e.g. `bruno-dc-concerts-9f3k2x7q`).
4. Save. (You can skip `NTFY_SERVER` unless you self-host ntfy.)

### 4. Turn on and test
1. Go to the **Actions** tab. If prompted, click **"I understand my workflows,
   enable them."**
2. Click **concert-monitor** in the left list → **Run workflow** → **Run workflow**.
3. In ~30 seconds the run finishes. Since the baseline is current, you'll likely
   see "No new shows" in the run log — that's success. The push fires only when
   something is genuinely new.

That's it. From now on it runs automatically M/W/F at ~11am ET.

---

## Triggering a check from your phone
Open the **GitHub mobile app** (or github.com in your phone browser) → your repo →
**Actions → concert-monitor → Run workflow**. Handy when an artist you want is
rumored to be announcing.

## Reading the history anywhere
`new_shows_log.md` in the repo accumulates every new find — readable from the
GitHub app/site on any device.

## Changing things
- **Schedule:** edit the `cron` line in `.github/workflows/monitor.yml`. The time
  is in UTC; `0 15 * * 1,3,5` is 11am ET in summer / 10am ET in winter, Mon/Wed/Fri.
- **Add/remove venues:** edit the `VENUES` block in `monitor.py`.
- **Quiet down recurring noise** (e.g. dance-fitness classes): add a prefix to
  `IGNORE_PREFIXES` in `monitor.py`.

## Good to know
- GitHub may delay scheduled runs by a few minutes at busy times, and can pause
  schedules on repos with no activity for 60 days — but this one commits its
  baseline on each run, which keeps it active automatically.
- The job never wipes its memory if a site is temporarily unreachable; it just
  skips that venue for the run and tries again next time.

---

### Tip: uploading the hidden `.github` folder
Folders starting with a dot can be hard to drag in. Easiest fix: in GitHub, click
**Add file → Create new file**, then type `.github/workflows/monitor.yml` as the
filename (GitHub creates the folders as you type the slashes) and paste in the
contents of that file. Do the same for `monitor.py`, `known_shows.json`, and
`new_shows_log.md` if drag-and-drop gives you trouble.
