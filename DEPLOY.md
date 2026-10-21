# Put ashwire.ai live on your server, step by step

You'll do four parts. The first two happen in your web browser, the rest in Terminal. It takes about 20 minutes, plus waiting for DNS.

Throughout this guide:
- A grey box is something to copy and paste exactly, then press **Enter**.
- "Mac Terminal" means Terminal on your own computer. "Server" means after you've logged in with `ssh`. The prompt tells you which: on the server it ends in `root@...:~#`.

---

## Part 1. Merge the Caddy change on GitHub (browser, 2 minutes)

Your MUD's setup script rewrites the Caddy config every time it runs. Pull request #431 makes it also load extra sites from `/etc/caddy/sites/`, so ashwire.ai won't get wiped on your next MUD update.

1. Open https://github.com/Datahead80/cyberpunk-mud/pull/431
2. Scroll to the bottom and click the green **Merge pull request** button, then **Confirm merge**.

---

## Part 2. Point ashwire.ai at your server in GoDaddy (browser, 5 minutes)

1. Go to https://dcc.godaddy.com/control/portfolio and sign in.
2. Click **ashwire.ai**, then the **DNS** tab (it may say **Manage DNS**).
3. In the list of records, look for any row with **Type = A** and **Name = @**.
   - If its value is already `5.161.220.19`, leave it.
   - If its value is anything else (GoDaddy's default is a "Parked" address), click the pencil icon, change **Value** to `5.161.220.19`, and **Save**.
   - If there's no such row, click **Add New Record**, choose **Type: A**, **Name: @**, **Value: 5.161.220.19**, **TTL: 1 Hour**, and **Save**.
4. Now look for a row with **Name = www**.
   - If it's a **CNAME** pointing at `@` or `ashwire.ai`, that's fine. Leave it.
   - If it's an **A** record, make its value `5.161.220.19`.
   - If there's no `www` row, add one: **Type: A**, **Name: www**, **Value: 5.161.220.19**, **TTL: 1 Hour**, **Save**.
5. Delete any **AAAA** rows for `@` or `www` if GoDaddy added them. They'd send some visitors to the wrong place.

DNS can take a few minutes to an hour to update. You'll check it in Part 4.

---

## Part 3. Install the site on the server (Mac Terminal, then server, 5 minutes)

The site lives in its own GitHub repo, https://github.com/Datahead80/ashwire-site, separate from the MUD. The server downloads it straight from GitHub, so you don't copy any files yourself.

1. Open **Terminal** on your Mac (press **Cmd + Space**, type `Terminal`, press **Enter**).

2. Log in to the server:

   ```
   ssh root@5.161.220.19
   ```

3. Update the MUD to the merged code. This adds the `/etc/caddy/sites` line to Caddy. The game is down for about a minute while it restarts.

   ```
   bash setup.sh
   ```

   Wait until it finishes and you get your prompt back.

4. Check that Caddy now loads the sites folder. You should see `import /etc/caddy/sites/*.caddy`:

   ```
   grep sites /etc/caddy/Caddyfile
   ```

   If nothing prints, stop here and tell me, because Part 1's merge didn't reach the server.

5. Download the site into `/var/www/ashwire.ai`:

   ```
   mkdir -p /var/www
   git clone https://github.com/Datahead80/ashwire-site.git /var/www/ashwire.ai
   ls /var/www/ashwire.ai
   ```

   The last line should list `index.html`, `favicon.svg`, `assets`, `brand`, `deploy` and `README.md`.

6. Install the Caddy site file. It comes in the repo, so you just copy it:

   ```
   cp /var/www/ashwire.ai/deploy/ashwire.caddy /etc/caddy/sites/ashwire.caddy
   ```

7. Check the config, then load it:

   ```
   caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
   ```

   It should end with `Valid configuration`. If it shows an error instead, copy it to me and don't run the next line.

   ```
   systemctl reload caddy
   ```

   No output means it worked.

8. Log out:

   ```
   exit
   ```

---

## Part 4. Check it's live (Mac Terminal, then browser)

1. In Mac Terminal, check DNS:

   ```
   dig +short ashwire.ai
   dig +short www.ashwire.ai
   ```

   Both should print `5.161.220.19` (www may print `ashwire.ai.` first, then the IP). If not, wait 15 minutes and try again.

2. Once DNS shows the right IP, open https://ashwire.ai in your browser. The first visit can take up to a minute while Caddy gets the HTTPS certificate. Then try https://www.ashwire.ai too.

3. Also check the game still works at https://mud.scpulley.com.

**If ashwire.ai shows a certificate error or won't load** after DNS is right, log in to the server and run this, then send me the output:

```
journalctl -u caddy --since "15 min ago" --no-pager | tail -30
```

---

## Updating the site later

When I tell you I've pushed a change to ashwire-site, run these two commands from your Mac:

```
ssh root@5.161.220.19
git -C /var/www/ashwire.ai pull
```

The new version is live right away, with no Caddy reload. (If I tell you the change touched `deploy/ashwire.caddy`, also repeat steps 6 and 7 of Part 3.)
