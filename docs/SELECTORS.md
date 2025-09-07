Selector Guide (Facebook Group Auto Poster)
===========================================

Purpose
-------
This guide explains how the script finds the composer (post text box) and the Post/Publish button, how to use --inspect mode, and how to supply your own robust XPaths.

1. Inspect Mode
---------------
Run:
  python3 main.py --links-file links.txt --inspect --no-headless --debug --limit 5

What it does:
- Logs in (or uses dummy credentials if you omit real ones and also use --dry-run, though real login is recommended for accuracy).
- Opens each group link in a new tab.
- Detects the composer element heuristically (no message is typed, no post is submitted).
- Locates a likely Post button.
- Prints guessed XPaths like:
    [INSPECT] https://www.facebook.com/groups/1234
      composer_xpath_guess: //div[3]/div/div[2]/div
      post_button_xpath_guess: //*[@id="jsc_xyz"]
- Saves artifacts under artifacts/ if --debug is on.

Use the printed guesses to create stable custom XPaths.

2. Per-Link Overrides (links.txt)
---------------------------------
Format (tab or pipe separators):
  URL
  URL | COMPOSER_XPATH
  URL | COMPOSER_XPATH | POST_BUTTON_XPATH

Examples:
  https://www.facebook.com/groups/example1
  https://www.facebook.com/groups/example2 | //div[@role='textbox' and @contenteditable='true']
  https://www.facebook.com/groups/example3 | //div[@aria-label='Write something...' and @contenteditable='true'] | //span[normalize-space()='Post']/ancestor::div[@role='button']

3. Global Overrides
-------------------
If MOST groups share a stable structure:
  --composer-xpath "//div[@role='textbox' and @contenteditable='true']"
  --post-button-xpath "//span[normalize-space()='Post']/ancestor::div[@role='button']"

Per-link overrides take precedence over global ones.

4. Heuristic Detection Logic (Summary)
--------------------------------------
Composer scan steps:
1. Optional override XPath.
2. JavaScript scoring of all [contenteditable="true"] or role="textbox" elements.
   - Scores points if: role= textbox, isContentEditable, class hints (composer/notranslate), or contains localized keywords (see COMPOSER_KEYWORDS in code).
3. Fallback XPaths: //div[@role='textbox' and @contenteditable='true'] and within data-pagelet GroupInlineComposer.

Post button scan steps:
1. Optional override XPath.
2. Search within nearest dialog / data-pagelet ancestor for elements matching role=button or <button> whose aria-label, textContent, data-testid match localized POST_BUTTON_KEYWORDS or common test IDs (react-composer-post-button).
3. Fallback XPaths for English “Post”.

5. Crafting Resilient XPaths
---------------------------
Prefer attributes that are:
- Stable: role, aria-label (language-specific; may change if UI language changes), data-testid.
- Avoid brittle auto-generated class names (e.g., .x1lliihq.x1n2onr6... ).
- Keep them short:
    //div[@role='textbox' and @contenteditable='true']
  or scope inside a known container:
    //*[@data-pagelet='GroupInlineComposer']//div[@role='textbox' and @contenteditable='true']

For Post button, try multi-locale approach:
  //div[@role='button' and (@aria-label='Post' or @aria-label='Publier' or @aria-label='Publicar')]
Or rely on text:
  //span[normalize-space()='Post']/ancestor::div[@role='button']

6. Debug Artifacts
------------------
When --debug is active, failures produce files like:
  artifacts/20250907-101500__https---www-facebook-com-groups-...__composer-not-found.png
  artifacts/...__post-button-not-found.html
  artifacts/...__composer.meta.txt

.element/meta contents help you refine selectors by showing:
- aria-label
- placeholder
- data-testid
- a guessed XPath (xpath_guess)

7. Troubleshooting
------------------
Issue: composer-not-found
- Open the corresponding HTML artifact and search for role="textbox" or contenteditable.
- Use browser DevTools to inspect and derive a simpler XPath.

Issue: post-button-not-found
- Ensure the composer accepted text (no validation popups blocking).
- Inspect artifacts for a disabled Post button (look for aria-disabled or class indicating disabled state). Sometimes text still needs a newline.

Issue: Only admins can post
- Artifacts may contain a message like “Only admins can post” – this is not a selector issue.

8. Manual Mode Workflow
-----------------------
If auto-post is flaky or you want supervision:
  python3 main.py --links-file links.txt --message-file pesan.txt --manual-post --no-headless --limit 3
The script types the message, pauses, and waits for you to press Enter after manually clicking Post.

9. Safety & Rate Limits
-----------------------
- Increase --delay-min / --delay-max to appear more human.
- Use small batches (--limit) and pause between runs.
- Avoid posting identical content to many groups quickly; vary wording.

10. Updating Keyword Lists
--------------------------
If your UI language isn’t matched, add localized phrases to COMPOSER_KEYWORDS or POST_BUTTON_KEYWORDS in main.py and re-run.

11. Common Useful Selector Patterns
-----------------------------------
Composer patterns:
  //div[@role='textbox' and @contenteditable='true']
  //*[@data-pagelet='GroupInlineComposer']//div[@role='textbox']
  //div[@aria-label='Write something...']

Post button patterns:
  //span[normalize-space()='Post']/ancestor::div[@role='button']
  //div[@role='button' and contains(@aria-label,'Post')]
  //div[@role='button' and (@aria-label='Post' or @aria-label='Publier' or @aria-label='Publicar')]

12. When All Else Fails
-----------------------
1. Run with --inspect --debug.
2. Open artifact HTML in a text editor.
3. Copy a unique attribute path.
4. Test the XPath quickly using browser DevTools ($x("<xpath>")).
5. Add to links.txt line.

License & Responsibility
------------------------
Provided for educational / personal automation scenarios. You assume all risk. The maintainers are not responsible for account actions taken by the platform.

