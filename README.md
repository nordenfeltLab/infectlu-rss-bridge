# Infect@LU RSS bridge

An automatic RSS-to-HTML bridge for Infect@LU publications at Lund University. A GitHub Action fetches the official RSS feed and publishes a readable HTML page plus JSON through GitHub Pages.

## What the tracker adds

- Saves publication links and content fingerprints in `.state/seen_publications.json` in the repository.
- Compares every successful run with the previous one, independent of publication date.
- Adds `new_items`, `changed_items`, and counts to `feed.json`; the HTML page lists these separately from the current feed snapshot.
- On the first upgraded run, compares against the previously published `feed.json` to seed the tracker. If that snapshot cannot be fetched, it establishes a baseline and reports that state in the page.
- Keeps old IDs in the state file after they roll out of the monthly feed, preventing them from appearing new if they reappear.
- Allows up to 1,000 parsed items per snapshot (the current version stops at 100), reducing the chance of silently truncating a busy month.

“New” means newly present in the feed compared with the previous successful bridge snapshot. It does not mean newly published or automatically suitable for social media. Continue to check LUP’s record page, date added, DOI, abstract, author order, editorial fit and the existing publication queue.

## One-time update

1. Download the ZIP and replace the repository's `scripts/fetch_rss.py`, `.github/workflows/update-feed.yml` and `README.md` with the copies in this archive. Commit to `main`.
2. In GitHub, open **Settings → Actions → General** and confirm the workflow is allowed to grant **Read and write permissions** to `GITHUB_TOKEN`. The workflow needs this permission to commit the small state file.
3. Run **Actions → Update Infect@LU RSS bridge → Run workflow** once. Confirm the run is green and check the published page and JSON.
4. Subsequent Monday runs will compare with the stored state automatically. No weekly download or upload is needed.

The action deploys the Pages snapshot before committing state. If deployment fails, tracking state is not advanced. If the state commit fails, the published snapshot still appears, and the next run may repeat its new/changed labels until state saves.

## Existing settings

- Runs every Monday at 05:00 UTC and on manual demand.
- Pages uses the GitHub Actions deployment source.
- No API key or paid service is required.
- If the feed fails or contains no valid records, the action fails without deploying an empty snapshot.
