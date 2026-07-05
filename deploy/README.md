# Running the bot 24/7 on an AWS free-tier server

This gets the Telegram bot running around the clock on a small AWS EC2 machine
that fits inside the free tier. The bot talks to Telegram by polling (it makes
outbound calls and waits for messages), so you do not need to open any web
ports or set up a domain. All it needs is a machine that stays on.

Once it is set up, `systemd` keeps it alive: it starts on every reboot and
restarts itself if it ever crashes.

## What you need

- An AWS account (the free tier covers this for 12 months).
- A Telegram bot token from [@BotFather](https://t.me/BotFather).
- About 15 minutes.

## 1. Launch the server

In the AWS console, open **EC2** and click **Launch instance**:

- **Name:** `flight-bot`
- **AMI:** Ubuntu Server 24.04 LTS (free tier eligible). Amazon Linux 2023
  also works if you prefer it.
- **Instance type:** `t2.micro` or `t3.micro` (whichever shows "Free tier
  eligible" in your region).
- **Key pair:** create one and download the `.pem` file so you can SSH in.
- **Network / security group:** allow **SSH (port 22)** only. That is all the
  bot needs, because it never accepts incoming connections.
- **Storage:** the default 8 GB is plenty.

Launch it, then copy the instance's **Public IPv4 address**.

## 2. Connect to it

From your own machine:

```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@YOUR_PUBLIC_IP
```

(Use `ec2-user@...` instead of `ubuntu@...` on Amazon Linux.)

## 3. (Recommended) add a bit of swap

The free-tier machine only has 1 GB of RAM, which is fine to run the bot but
can run out while installing dependencies. A small swap file avoids that:

```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 4. Get the code and run the setup script

```bash
git clone https://github.com/osamaPY/flight-meetup-agent.git
cd flight-meetup-agent
bash deploy/setup.sh
```

The script installs Python, creates a virtual environment, installs the
dependencies, and registers the `flight-bot` service so it runs on boot.

## 5. Add your token

The script creates a `.env` file from the template. Open it and paste in your
bot token:

```bash
nano .env
```

Set at least:

```
TELEGRAM_BOT_TOKEN=123456:your-token-from-botfather
```

The rest is optional. `DEEPSEEK_API_KEY` turns on the AI suggestion button, and
`TRAVELPAYOUTS_TOKEN` adds a server-friendly free API source, `AMADEUS_CLIENT_ID` / `AMADEUS_CLIENT_SECRET` add an optional GDS source, and `DUFFEL_TOKEN` adds a paid GDS source. The bot runs fine on the free Ryanair and Google data without any of them.

## 6. Start it

```bash
sudo systemctl start flight-bot
```

Check it is running and watch the live logs:

```bash
systemctl status flight-bot
journalctl -u flight-bot -f
```

You should see it reach `Polling...`. Message your bot on Telegram to confirm
it answers. Press `Ctrl+C` to stop tailing the logs (that does not stop the
bot).

That is it. The bot is now live 24/7 and will come back on its own after a
crash or a reboot.

## Everyday commands

```bash
sudo systemctl restart flight-bot   # restart it
sudo systemctl stop flight-bot      # stop it
sudo systemctl start flight-bot     # start it again
systemctl status flight-bot         # is it running?
journalctl -u flight-bot -f         # follow the logs
journalctl -u flight-bot --since "1 hour ago"
```

## Updating after you push new code

```bash
cd ~/flight-meetup-agent
bash deploy/update.sh
```

That pulls the latest commit, updates dependencies, and restarts the bot.

## Keeping it free

- Stay on a `t2.micro` / `t3.micro` and one instance, and you stay within the
  free tier for the first 12 months.
- The database is a single SQLite file under `data/`. Back it up with the
  helper if you want: `venv/bin/python scripts/backup_db.py`.
- After the 12 free months, a `t3.micro` is only a few dollars a month, or you
  can move the same setup to any other cheap Linux VPS. The steps are identical
  from "Get the code" onward.

## If something goes wrong

- **Bot does not answer:** check the logs with `journalctl -u flight-bot -e`.
  The most common cause is a missing or wrong `TELEGRAM_BOT_TOKEN` in `.env`.
  Fix it, then `sudo systemctl restart flight-bot`.
- **"Conflict" in the logs:** another copy of the bot is running with the same
  token (for example on your laptop). Stop the other one; the service retries
  on its own.
- **Ran out of memory during setup:** add the swap file from step 3 and run
  `bash deploy/setup.sh` again.
