# Move ashwire.ai to GitHub Pages, step by step

After this, GitHub hosts the site for free and your old server has nothing to do with it. Every push to this repo goes live on its own in about a minute.

Do the parts in order. Parts 1 to 3 are in GitHub, Part 4 is in GoDaddy, and Part 5 is one last cleanup on your server. Allow about 20 minutes, plus up to an hour of waiting for DNS and the HTTPS certificate.

The site may show a certificate warning for a few minutes after Part 4, while GitHub gets its certificate. That's normal.

---

## Part 1. Turn on GitHub Pages (2 minutes)

1. Open https://github.com/Datahead80/ashwire-site/settings/pages
2. Under **Build and deployment**, set **Source** to **GitHub Actions**. There's no Save button; it saves as soon as you pick it.
3. Open https://github.com/Datahead80/ashwire-site/actions/workflows/pages.yml
4. Click **Run workflow** on the right, then the green **Run workflow** button.
5. Wait for the run to show a green check (about a minute). Refresh the page if it doesn't update.

---

## Part 2. Verify you own ashwire.ai (5 minutes, recommended)

This stops anyone else from ever attaching ashwire.ai to their own GitHub Pages site.

1. Open https://github.com/settings/pages (your account settings, not the repo).
2. Click **Add a domain**, type `ashwire.ai`, and click **Add domain**.
3. GitHub shows a **TXT record** with a name like `_github-pages-challenge-Datahead80` and a long value. Keep this tab open.
4. In a new tab, open GoDaddy's DNS page for ashwire.ai (https://dcc.godaddy.com/control/portfolio, click **ashwire.ai**, then **DNS**).
5. Click **Add New Record** and fill in:
   - **Type:** TXT
   - **Name:** the name GitHub shows, *without* the `.ashwire.ai` on the end (for example `_github-pages-challenge-Datahead80`)
   - **Value:** the long value GitHub shows
   - **TTL:** 1 Hour
6. Click **Save**, go back to the GitHub tab, and click **Verify**. If it says it can't find the record yet, wait 10 minutes and click **Verify** again.

---

## Part 3. Tell GitHub the site's domain (1 minute)

1. Go back to https://github.com/Datahead80/ashwire-site/settings/pages
2. Under **Custom domain**, type `ashwire.ai` and click **Save**.
3. It will show a DNS warning. That's expected until Part 4 is done.

---

## Part 4. Point ashwire.ai at GitHub in GoDaddy (5 minutes)

On the GoDaddy DNS page for ashwire.ai:

1. Find the existing **A** record with **Name @** (it points at your old server). Click its pencil icon, change **Value** to `185.199.108.153`, and **Save**.
2. Add three more A records. For each one, click **Add New Record**, choose **Type: A**, **Name: @**, **TTL: 1 Hour**, and **Save**. Use these values:
   - `185.199.109.153`
   - `185.199.110.153`
   - `185.199.111.153`
3. Find the **www** record (a CNAME pointing at `ashwire.ai` or `@`). Click its pencil icon, change **Value** to `datahead80.github.io`, and **Save**.
4. Check there are no **AAAA** records for `@` or `www`. If there are, delete them.

When you're done, the records for the site should be exactly:

| Type | Name | Value |
|---|---|---|
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| CNAME | www | datahead80.github.io |

Then wait. Within about an hour:

1. Open https://github.com/Datahead80/ashwire-site/settings/pages again. It should say **DNS check successful**.
2. Tick **Enforce HTTPS**. If the box is greyed out, GitHub is still getting the certificate. Check back in 15 minutes.
3. Open https://ashwire.ai and https://www.ashwire.ai. Both should show the site.

---

## Part 5. Remove the site from your server (2 minutes)

Only do this after https://ashwire.ai loads from GitHub (Part 4 finished). Open your server in your SSH app as you normally do, then paste these one at a time:

```
rm /etc/caddy/sites/ashwire.caddy
```
```
systemctl reload caddy
```
```
rm -rf /var/www/ashwire.ai
```
```
exit
```

The empty `/etc/caddy/sites/` folder stays. It's harmless, and you can use it for another site later.

---

## Updating the site later

Nothing to do on your end. Changes pushed to `main` go live on their own within about a minute. You can watch each update at https://github.com/Datahead80/ashwire-site/actions
