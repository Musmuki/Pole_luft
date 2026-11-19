# Cloudflare Pages deployment

The existing [GitHub Pages site](https://musmuki.github.io/Pole_luft/) stays online. Cloudflare Pages is an optional second deployment. Connecting Cloudflare requires the account owner to authorize GitHub access in Cloudflare's dashboard.

## One-time connection

1. Open [Cloudflare Workers & Pages](https://dash.cloudflare.com/).
2. Choose **Create → Pages → Connect to Git**, connect **Musmuki/Pole_luft**, branch **main**.
3. Build command: `python build.py`; output directory: `site`; root directory: `/`.
4. If the build fails due to missing Python/timezone support, check build log and select a Python 3.x runtime. No pip dependencies are used.
5. Deploy. The build script automatically reads the `CF_PAGES_URL` environment variable and uses the Cloudflare domain for canonical URLs and the sitemap. For a custom domain, set `SITE_URL` to its full `https://` origin and trigger a rebuild.
6. Verify the Cloudflare homepage, city pages, `/sitemap.xml`, `/robots.txt`, and Google verification file. Only then submit the Cloudflare sitemap to Search Console.

## Scheduled refreshes (optional)

The existing GitHub workflow refreshes GitHub Pages hourly. Cloudflare Pages Git integration builds on pushes, but not automatically when the source DWD/UBA data changes. To refresh the Cloudflare site at most every **two hours** without paid Cloudflare features:

1. Cloudflare Pages project → **Settings → Builds & deployments → Deploy hooks** → create a production deployment hook.
2. GitHub repository → **Settings → Secrets and variables → Actions → New repository secret**. Name: `CLOUDFLARE_PAGES_DEPLOY_HOOK`, value: the full deployment hook URL.
3. The existing hourly GitHub Action calls the hook on even UTC hours. On Git pushes it also calls the hook, in addition to the Pages Git integration's native build. Consider disabling duplicate triggers or removing this optional push call if build usage is near its limit.

**Usage warning:** Cloudflare Pages Free has a monthly build limit. Two-hourly builds are ~360–372/month, before pushes, manual builds and retries. Monitor builds. No hosting costs should be incurred without explicit approval.

## Monetization is not active

Moving to Cloudflare alone does not generate revenue. Before adding ad code or affiliate programs:
- Provide truthful legal contact/imprint details appropriate for Germany (including a compliant Impressum) and an accurate privacy notice for the actual hosting and analytics used.
- Examine DWD and UBA terms of reuse, attribution and any commercial limitations.
- Confirm that the site is providing substantial distinct value to visitors; avoid thin/near-duplicate pages for SEO.
- Submit site and verify ownership/traffic in Google Search Console.
- Set up a verified ad/affiliate account, payment and tax information; consider consent requirements before installing tracking/advertising scripts.
- Do not state that the site sets no cookies or records no data unless true across hosting, ads, analytics, and third-party services.

No ad network credentials or personal addresses should be committed to this public GitHub repository. Keep the code in GitHub and configure third-party service credentials in provider account settings only.
