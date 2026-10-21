# ashwire.ai

The Ashwire Labs landing page. Plain static files, no build step.

Served on the game server from `/var/www/ashwire.ai` by Caddy (see `docs/deploy.md` in cyberpunk-mud, "Hosting another website on the same server").

To update the live site after changes are pushed:

```
ssh root@5.161.220.19
git -C /var/www/ashwire.ai pull
```
