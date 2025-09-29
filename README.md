Facebook Group Auto Poster (Selenium)

Use at your own risk. Automated posting may violate Facebook’s Terms. This script doesn’t bypass 2FA and may break if Facebook changes its UI. Respect group rules.

Quick start

1) Python 3.9+ recommended. Install deps:
   pip install -r requirements.txt

2) Create a .env file (or pass --email/--password):
   FACEBOOK_EMAIL=your_email@example.com
   FACEBOOK_PASSWORD=your_password

3) Put your group links (one per line) in links.txt. See links.sample.txt for format. You can optionally append per-link composer & post button XPaths, separated by a tab or pipe:
   https://www.facebook.com/groups/123456789012345
   https://www.facebook.com/groups/123456789012345 | //div[@role='textbox']
   https://www.facebook.com/groups/123456789012345 | //div[@role='textbox'] | //span[normalize-space()='Post']/ancestor::div[@role='button']

4) Write your post content in pesan.txt (default) or pass --message "Your text".

Dry run (no browser, no login required)
   python3 main.py --links-file links.txt --limit 10 --dry-run

Real run (headless by default unless --no-headless)
   python3 main.py --links-file links.txt --limit 40 --message-file pesan.txt

   # or inline message
   python3 main.py --links-file links.txt --limit 40 --message "Hello group!" --headless

Selector inspect mode (discover XPaths but DO NOT post)
   python3 main.py --links-file links.txt --inspect --no-headless --debug --limit 5
   # This prints guessed composer/post button XPaths you can copy into links.txt

Manual post mode (script fills text, you click Post yourself)
   python3 main.py --links-file links.txt --message-file pesan.txt --manual-post --no-headless

Mobile mode (m.facebook.com)
- Enable with --mobile to emulate a mobile device and open m.facebook.com.
- Flow: Click Composer Placeholder -> Type after modal appears -> Click Post.
- Keywords limited to English + Indonesian (e.g., "Write something...", "Tulis sesuatu...").

Global overrides
   --composer-xpath "//div[@role='textbox' and @contenteditable='true']"
   --post-button-xpath "//span[normalize-space()='Post']/ancestor::div[@role='button']"
(Use these only if automatic detection fails for most groups.)

Timing tweaks
   --login-wait 25       # seconds to pause after filling login form (anti-bot pacing)
   --prepost-wait 20     # pause after typing message before clicking Post
   --delay-min 3 --delay-max 8  # random delay range between group actions

Debugging failures
- Use --debug to save screenshot & HTML for failures into ./artifacts (change with --out-dir).
- Files include a timestamp, slugified URL, and a tag (e.g., composer-not-found, post-button-not-found).
- Element metadata (.meta.txt) & HTML snapshots help craft better XPaths.

Recommended workflow to obtain stable XPaths
1. Run inspect mode on a small subset (--limit 5 --inspect --debug).
2. Copy printed composer_xpath_guess and post_button_xpath_guess into links.txt lines.
3. Re-run normally. If stable, you can remove global overrides.
4. Keep XPaths short & resilient: target role/aria-label/data-testid more than brittle class names.

links.txt format examples
   # Only URL
   https://www.facebook.com/groups/example1
   # URL + composer XPath
   https://www.facebook.com/groups/example2 | //div[@role='textbox']
   # URL + composer XPath + post button XPath
   https://www.facebook.com/groups/example3 | //div[@role='textbox'] | //span[normalize-space()='Post']/ancestor::div[@role='button']

Environment variables (fallbacks if flags absent)
   FACEBOOK_EMAIL, FACEBOOK_PASSWORD, HEADLESS (0/1)
   CHROMEDRIVER (path to chromedriver binary)

Notes
- Joining required groups or admin-only restrictions are detected heuristically; posting is skipped.
- If UI changes break detection, run with --inspect + --debug and open artifacts to adjust XPaths.
- Use manual mode for sensitive accounts to verify each post before submitting.
- Avoid very aggressive delays; keep human-like pacing to reduce risk.

Selector details
See docs/SELECTORS.md for deeper guidance on crafting resilient XPaths and interpreting debug artifacts.

Assets location
- Example screenshots/images moved to docs/assets/ to keep the project root clean.
