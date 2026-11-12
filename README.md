# Infect@LU RSS bridge

An automatic RSS-to-HTML bridge for Infect@LU publications at Lund University. A GitHub Action fetches the official RSS feed and publishes a readable HTML page plus a JSON file via GitHub Pages.

## Setup in GitHub (one time)

1. Create a new public repository named `infectlu-rss-bridge`. Choose **Public**, leave **Add a README file** disabled, **.gitignore** = None, **License** = None.
2. Unzip the package locally. In Finder (macOS), open the inner `infectlu-rss-bridge` folder. Press **Command + Shift + .** if `.github` is hidden.
3. Upload the three items *inside* that folder into the root of the GitHub repository: `README.md`, `scripts` folder, and `.github` folder. The zip file itself and the outer folder should not be uploaded. Commit directly to `main`.
4. Under **Settings > Pages > Build and deployment**, select **Source = GitHub Actions** (NOT `Deploy from a branch`).
5. Under **Actions**, select **Update Infect@LU RSS bridge**, choose **Run workflow**, **Branch = main**, then **Run workflow**.
6. Verify the run has a green check. Under **Settings > Pages**, click **Visit site** and verify that the page includes a current **Last successful fetch** timestamp and actual publications.
7. Your site will normally be `https://YOUR-GITHUB-USERNAME.github.io/infectlu-rss-bridge/`; JSON: `https://YOUR-GITHUB-USERNAME.github.io/infectlu-rss-bridge/feed.json`. Use the actual address from GitHub, not the example.
8. Share your published page URL in ChatGPT so the monitoring workflow can be tested against it. Don't change the source in the monitoring task before that check succeeds.

## Running and failures

- Runs every Monday **05:00 UTC** (06:00 Swedish winter time; 07:00 Swedish summer time) plus on manual demand.
- There is no API key and no recurring manual action.
- The generated `docs/` folder is *not* checked into the repository; it is created during each Action run and published as a GitHub Pages artifact. **This is intentional.** GitHub Pages is configured using **GitHub Actions**, ensuring scheduled runs deploy fresh pages even though they do not push code changes.
- If the RSS server cannot be accessed or produces no valid items, the action fails without replacing the previously published site. Check the **Actions** run logs.
- The page is public and includes only publication records already exposed in the official public RSS feed.

## Limitations

- The RSS monthly feed represents recent feed updates, not necessarily newly published articles; old publications may be edited or newly registered. ChatGPT still needs to check dates, DOI, subjects, author affiliation and whether an article has been featured before.
- ChatGPT's browsing tool may cache public HTML pages, so check the displayed **Last successful fetch** timestamp before treating the data as current.
- This package was validated with a sample RSS document. Its first GitHub Actions run is the actual test against the Lund University server.
