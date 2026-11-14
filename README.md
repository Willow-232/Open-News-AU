# Open News AU

A free, open-source news app. Australian news comes first, then world news. It pulls headlines from reputable outlets across the political spectrum every day, groups stories that several outlets covered, and shows how each story's coverage leans.

- **Australia first:** AAP, ABC, SBS, The Conversation, Guardian Australia, The New Daily, news.com.au, AFR, The Australian
- **World:** Reuters, AP, BBC, DW, NPR, France 24, Al Jazeera English, Wall Street Journal
- **Fact checks:** AAP FactCheck, RMIT FactLab
- **Compare coverage:** stories covered by several outlets are grouped together, with a left/centre/right bar. A **One-sided coverage** filter shows stories covered mostly by one side.
- **No ads, no tracking, no accounts.** It's a static site plus a Python script with no dependencies.
- **Works like an app:** add it to your phone's home screen. It also shows the last update when you're offline.

## Set it up (about 10 minutes, free)

You need a free GitHub account. This is easiest on a computer.

1. **Create a repo.** On github.com, click **+ → New repository**. Name it something like `open-news-au`, make it **Public**, and click **Create**.
2. **Upload the files.** On the new repo page, click **uploading an existing file**. Unzip this project and drag *everything* inside the `open-news-au` folder into the page, including the hidden `.github` folder. (On a Mac, press `Cmd + Shift + .` in Finder to show hidden folders.) Click **Commit changes**.
3. **Let the bot save updates.** Go to **Settings → Actions → General → Workflow permissions**, choose **Read and write permissions**, and click **Save**.
4. **Turn on the website.** Go to **Settings → Pages**. Under *Source*, choose **Deploy from a branch**, pick **main** and the **/docs** folder, then click **Save**.
5. **Run the first update.** Go to the **Actions** tab, click **Daily news update → Run workflow**, and wait about a minute.
6. **Open your app** at `https://YOUR-USERNAME.github.io/open-news-au/`. On iPhone, tap **Share → Add to Home Screen**. On Android, use **⋮ → Add to Home screen**.

After that it updates itself every morning around 7am Sydney time (6am during winter).

## Change the sources

Everything is in `sources.json`. Each outlet looks like this:

```json
{"name": "ABC News", "region": "australia", "lean": "left-centre", "reliability": "high",
 "url": "https://www.abc.net.au/news/feed/51120/rss.xml"}
```

- `region`: `australia`, `world` or `factcheck`
- `lean`: `left`, `left-centre`, `centre`, `right-centre` or `right`
- `reliability`: `very-high`, `high`, `mostly-factual` or `mixed`

The lean and reliability labels are starting estimates based on [Media Bias/Fact Check](https://mediabiasfactcheck.com) and [Ad Fontes Media](https://adfontesmedia.com). Check them and adjust them to your own view.

Any RSS or Atom feed works. For outlets without a public feed (Reuters, AP, AFR, The Australian), the app uses a Google News search feed limited to that site. Editing `sources.json` on GitHub automatically starts a new update.

If a feed stops working, it shows as **failed** in the app's **Sources** tab, and the other feeds keep running.

## Update more often

In `.github/workflows/daily-news.yml`, change `cron: "0 20 * * *"` to `cron: "0 20,8 * * *"` to update at 7am and 7pm.

## Run it on your own computer

```bash
python3 scripts/fetch_news.py      # builds docs/news.json
cd docs && python3 -m http.server  # open http://localhost:8000
```

## A note on "unbiased"

No outlet is perfectly neutral. This app aims for balance instead: wire services (AAP, Reuters, AP) for straight reporting, plus reputable outlets from both sides, with their leans shown openly so you can compare how a story is covered.

Headlines and links belong to their publishers. Each story links back to the original article.

## Licence

MIT. See `LICENSE`.
