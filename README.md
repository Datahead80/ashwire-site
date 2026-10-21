# ashwire.ai

The Ashwire Labs landing page. Plain static files, no build step.

Served on the game server from `/var/www/ashwire.ai` by Caddy (full setup steps in `DEPLOY.md`; the Caddy site file is `deploy/ashwire.caddy`).

To update the live site after changes are pushed:

```
ssh root@5.161.220.19
git -C /var/www/ashwire.ai pull
```
