#!/usr/bin/env python3
"""
Facebook Group Auto Poster using Selenium

IMPORTANT: Use responsibly and respect Facebook's Terms of Service and group rules.
This script may break at any time if Facebook changes its UI. It does NOT bypass 2FA
or other security challenges. Automated posting can lead to account restrictions.

Core features:
- Sequentially open group links and attempt to publish a post.
- Heuristic, multi-language detection of composer (text box) & Post/Publish button.
- Optional explicit XPaths (global or per-link) for both composer and post button.
- Per-link overrides: URL[\t or |]composer_xpath[\t or |]post_button_xpath
- Dry run mode (no browser), Inspect mode (detect & print selectors only, no posting).
- Manual post mode (script fills text; you press Post yourself).
- Debug artifact capture (HTML + screenshot + element metadata) on failures.

Flags:
  --inspect            : Only discover/print composer + post button candidates.
  --composer-xpath     : Global override for composer element.
  --post-button-xpath  : Global override for Post button element.
  --manual-post        : Let user click Post manually.
  --login-wait / --prepost-wait : Deterministic waits to mimic human latency.
"""
from __future__ import annotations

import argparse
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

try:  # Optional .env support
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None

# ---------------------------------- Configuration Dataclass ----------------------------------
@dataclass
class Config:
    email: str
    password: str
    links_file: Path
    message: str
    headless: bool
    limit: int
    delay_min: float
    delay_max: float
    timeout: int
    dry_run: bool
    debug: bool
    out_dir: Path
    lang: str
    user_agent: Optional[str]
    login_wait: float
    prepost_wait: float
    composer_xpath: Optional[str]
    post_button_xpath: Optional[str]
    manual_post: bool
    inspect: bool

# ---------------------------------- Keyword Dictionaries ----------------------------------
COMPOSER_KEYWORDS = [
    'write something', 'write something...', 'write a post', 'write your post', "what's on your mind", 'what are you selling',
    'escribe algo', 'escribe una publicación',
    'tulis sesuatu', 'tulis kiriman', 'tulis postingan',
    'escreva algo', 'no que você está pensando', 'escreva uma publicação',
    'écrivez quelque chose', 'écrire une publication',
    'schreibe etwas', 'schreib etwas', 'einen beitrag schreiben',
    'scrivi qualcosa', 'scrivi un post',
    'bir şeyler yaz', 'bir gönderi yaz',
    'напишите что-нибудь', 'напишите что-то', 'создать публикацию',
    'viết gì đó', 'viết một bài',
    'เขียนอะไรบางอย่าง',
    '投稿を作成', '何かを書いてください',
    '무슨 생각을 하고 계신가요', '게시물 작성',
]

POST_BUTTON_KEYWORDS = [
    'post', 'publish', 'share', 'publier', 'publicar', 'postar', 'enviar', 'fertig', 'kirim', 'bagikan', 'unggah', 'posting',
    'แชร์', 'แบ่งปัน', 'แชร์โพสต์', '投稿', '게시', '완료', 'опубликовать'
]

_COMPOSER_KEY_SET = {k.lower() for k in COMPOSER_KEYWORDS}
_POST_KEY_SET = {k.lower() for k in POST_BUTTON_KEYWORDS}

# ---------------------------------- Argument Parsing ----------------------------------

def parse_args(argv: Optional[List[str]] = None) -> Config:
    p = argparse.ArgumentParser(description="Facebook Group Auto Poster")
    p.add_argument('--email')
    p.add_argument('--password')
    p.add_argument('--links-file', default='links.txt')
    p.add_argument('--message')
    p.add_argument('--message-file', default='pesan.txt')
    p.add_argument('--headless', action='store_true')
    p.add_argument('--no-headless', action='store_true')
    p.add_argument('--limit', type=int, default=40)
    p.add_argument('--delay-min', type=float, default=4.0)
    p.add_argument('--delay-max', type=float, default=9.0)
    p.add_argument('--timeout', type=int, default=25)
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--inspect', action='store_true')
    p.add_argument('--debug', action='store_true')
    p.add_argument('--out-dir', default='artifacts')
    p.add_argument('--lang', default='en-US')
    p.add_argument('--user-agent')
    p.add_argument('--login-wait', type=float, default=30.0)
    p.add_argument('--prepost-wait', type=float, default=30.0)
    p.add_argument('--composer-xpath')
    p.add_argument('--post-button-xpath')
    p.add_argument('--manual-post', action='store_true')
    args = p.parse_args(argv)

    if load_dotenv:
        load_dotenv()

    email = args.email or os.getenv('FACEBOOK_EMAIL', '').strip()
    password = args.password or os.getenv('FACEBOOK_PASSWORD', '').strip()

    if args.no_headless:
        headless = False
    elif args.headless:
        headless = True
    else:
        headless = os.getenv('HEADLESS', '1') not in ('0', 'false', 'False')

    if args.message is not None:
        message = args.message
    else:
        mp = Path(args.message_file)
        message = mp.read_text(encoding='utf-8').strip() if mp.exists() else ''

    if not (message or args.dry_run or args.inspect):
        print('Error: no message provided.', file=sys.stderr)
        sys.exit(2)

    if (not email or not password) and not (args.dry_run or args.inspect):
        print('Error: missing credentials.', file=sys.stderr)
        sys.exit(2)

    if not email:
        email = 'dummy@example.com'
    if not password:
        password = 'dummy_password'

    if args.delay_max < args.delay_min:
        args.delay_min, args.delay_max = args.delay_max, args.delay_min

    return Config(
        email=email,
        password=password,
        links_file=Path(args.links_file).expanduser().resolve(),
        message=message,
        headless=headless,
        limit=max(1, int(args.limit)),
        delay_min=float(args.delay_min),
        delay_max=float(args.delay_max),
        timeout=int(args.timeout),
        dry_run=bool(args.dry_run),
        debug=bool(args.debug),
        out_dir=Path(args.out_dir).expanduser().resolve(),
        lang=args.lang,
        user_agent=args.user_agent,
        login_wait=float(args.login_wait),
        prepost_wait=float(args.prepost_wait),
        composer_xpath=args.composer_xpath,
        post_button_xpath=args.post_button_xpath,
        manual_post=bool(args.manual_post),
        inspect=bool(args.inspect),
    )

# ---------------------------------- Links File Parser ----------------------------------

def read_links(path: Path, limit: int) -> List[dict]:
    if not path.exists():
        raise FileNotFoundError(f'Links file not found: {path}')
    items: List[dict] = []
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if '\t' in line:
            parts = [p.strip() for p in line.split('\t')]
        elif '|' in line:
            parts = [p.strip() for p in line.split('|')]
        else:
            parts = [line]
        url = parts[0]
        if 'facebook.com' not in url:
            continue
        comp = parts[1] if len(parts) > 1 and parts[1] else None
        post = parts[2] if len(parts) > 2 and parts[2] else None
        items.append({'url': url, 'composer_xpath': comp, 'post_button_xpath': post})
        if len(items) >= limit:
            break
    return items

# ---------------------------------- Poster Class ----------------------------------
class FacebookPoster:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.driver = None  # type: ignore
        if self.cfg.debug and not self.cfg.dry_run:
            self.cfg.out_dir.mkdir(parents=True, exist_ok=True)

    # ---- Driver Setup ----
    def _init_driver(self):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        from selenium.webdriver.chrome.service import Service as ChromeService
        opts = ChromeOptions()
        if self.cfg.headless:
            opts.add_argument('--headless=new')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--disable-gpu')
        opts.add_argument('--window-size=1280,1024')
        opts.add_argument(f'--lang={self.cfg.lang}')
        try:
            opts.add_experimental_option('prefs', {'intl.accept_languages': self.cfg.lang})
        except Exception:
            pass
        if self.cfg.user_agent:
            opts.add_argument(f'--user-agent={self.cfg.user_agent}')
        opts.add_experimental_option('excludeSwitches', ['enable-automation'])
        opts.add_experimental_option('useAutomationExtension', False)
        driver_path = os.getenv('CHROMEDRIVER', '').strip()
        if driver_path and Path(driver_path).exists():
            service = ChromeService(driver_path)  # type: ignore[name-defined]
        else:
            try:
                from webdriver_manager.chrome import ChromeDriverManager  # type: ignore
                service = ChromeService(ChromeDriverManager().install())  # type: ignore[name-defined]
            except Exception:
                service = ChromeService()  # type: ignore[name-defined]
        self.driver = webdriver.Chrome(service=service, options=opts)
        self.driver.set_page_load_timeout(max(30, self.cfg.timeout))

    def _by(self):
        from selenium.webdriver.common.by import By
        return By

    def _ec(self):
        from selenium.webdriver.support import expected_conditions as EC
        return EC

    def _wait(self):
        from selenium.webdriver.support.ui import WebDriverWait
        return WebDriverWait(self.driver, self.cfg.timeout)

    def _sleep(self, a: Optional[float] = None, b: Optional[float] = None):
        lo = self.cfg.delay_min if a is None else a
        hi = self.cfg.delay_max if b is None else b
        time.sleep(random.uniform(lo, hi))

    # ---- Debug helpers ----
    def _safe_slug(self, text: str) -> str:
        return ''.join(c if c.isalnum() else '-' for c in text)[:100].strip('-') or 'item'

    def _save_artifacts(self, link: str, tag: str):
        if not (self.cfg.debug and self.driver):
            return
        try:
            ts = time.strftime('%Y%m%d-%H%M%S')
            slug = self._safe_slug(link)
            base = self.cfg.out_dir / f'{ts}__{slug}__{self._safe_slug(tag)}'
            try: self.driver.save_screenshot(str(base.with_suffix('.png')))
            except Exception: pass
            try: base.with_suffix('.html').write_text(self.driver.page_source, encoding='utf-8')
            except Exception: pass
            try: base.with_suffix('.url.txt').write_text(link, encoding='utf-8')
            except Exception: pass
        except Exception:
            pass

    def _element_xpath(self, el) -> Optional[str]:
        if not self.driver: return None
        try:
            return self.driver.execute_script(
                """
                function getXPath(node){
                  if(node.id) return '//*[@id="'+node.id+'"]';
                  const parts=[]; while(node && node.nodeType===1 && node!==document.body){
                    let i=0,s=node.previousSibling; while(s){ if(s.nodeType===1 && s.nodeName===node.nodeName) i++; s=s.previousSibling; }
                    parts.unshift(node.nodeName.toLowerCase()+(i?'['+(i+1)+']':'')); node=node.parentNode; }
                  return '//' + parts.join('/'); }
                return getXPath(arguments[0]);
                """,
                el,
            )
        except Exception:
            return None

    def _save_element_debug(self, el, tag='element'):
        if not (self.cfg.debug and self.driver):
            return
        try:
            ts = time.strftime('%Y%m%d-%H%M%S')
            slug = self._safe_slug(self.driver.current_url or 'page')
            base = self.cfg.out_dir / f'{ts}__{slug}__{tag}'
            try:
                outer = self.driver.execute_script('return arguments[0].outerHTML;', el)
                base.with_suffix('.html').write_text(outer or '', encoding='utf-8')
            except Exception: pass
            try:
                info = {
                    'tag': self.driver.execute_script('return arguments[0].tagName;', el),
                    'aria-label': el.get_attribute('aria-label'),
                    'placeholder': el.get_attribute('placeholder'),
                    'data-testid': el.get_attribute('data-testid'),
                    'class': el.get_attribute('class'),
                    'text_snippet': (el.text or '')[:120],
                    'xpath_guess': self._element_xpath(el),
                }
                base.with_suffix('.meta.txt').write_text(str(info), encoding='utf-8')
            except Exception: pass
        except Exception:
            pass

    # ---- Login ----
    def login(self):
        assert self.driver
        By = self._by(); EC = self._ec(); wait = self._wait()
        self.driver.get('https://www.facebook.com/login')
        for xp in [
            "//button[contains(., 'Allow all cookies')]",
            "//button[contains(., 'Accept all')]",
            "//button[contains(., 'Only allow essential')]",
            "//button[contains(., 'Essentials only')]",
        ]:
            try:
                el = self.driver.find_elements(By.XPATH, xp)
                if el:
                    el[0].click(); break
            except Exception:
                pass
        email_el = wait.until(EC.presence_of_element_located((By.NAME, 'email')))
        pass_el = wait.until(EC.presence_of_element_located((By.NAME, 'pass')))
        email_el.clear(); email_el.send_keys(self.cfg.email)
        pass_el.clear(); pass_el.send_keys(self.cfg.password)
        time.sleep(self.cfg.login_wait)
        login_btn = wait.until(EC.element_to_be_clickable((By.NAME, 'login')))
        login_btn.click()
        self._sleep(0.5, 1.2)
        try:
            wait.until(EC.url_contains('facebook.com'))
        except Exception:
            raise RuntimeError('Login likely failed or extra verification required.')

    # ---- Selector discovery ----
    def _find_composer(self, override_xpath: Optional[str]) -> Optional[object]:
        assert self.driver
        By = self._by()
        if override_xpath:
            try:
                for e in self.driver.find_elements(By.XPATH, override_xpath):
                    if e.is_displayed() and e.is_enabled():
                        return e
            except Exception:
                pass
        try:
            result = self.driver.execute_script(
                """
                const KEYWORDS = arguments[0];
                function score(el){
                  let s=0; const aria=(el.getAttribute('aria-label')||'').toLowerCase();
                  const ph=(el.getAttribute('placeholder')||'').toLowerCase();
                  const txt=(el.textContent||'').trim().toLowerCase();
                  const cls=(el.className||'').toLowerCase();
                  if (el.getAttribute('role')==='textbox') s+=2;
                  if (el.isContentEditable) s+=2; else if (el.getAttribute('contenteditable')==='true') s+=1;
                  if (/composer|notranslate|editable/.test(cls)) s+=1;
                  for (const k of KEYWORDS){ if (aria.includes(k) || ph.includes(k) || txt.startsWith(k) || txt.includes(k)) s+=3; }
                  return s;
                }
                const all = Array.from(document.querySelectorAll('[contenteditable="true"], div[role="textbox"]'));
                const scored = all.map(el=>({el,s:score(el)})).filter(o=>o.s>2).sort((a,b)=>b.s-a.s);
                return scored.map(o=>o.el);
                """,
                list(_COMPOSER_KEY_SET),
            )
            if result:
                for el in result:
                    try:
                        if el.is_displayed() and el.is_enabled():
                            return el
                    except Exception:
                        continue
        except Exception:
            pass
        for xp in [
            "//div[@role='textbox' and @contenteditable='true']",
            "//*[@data-pagelet='GroupInlineComposer']//div[@role='textbox' and @contenteditable='true']",
        ]:
            try:
                for e in self.driver.find_elements(By.XPATH, xp):
                    if e.is_displayed() and e.is_enabled():
                        return e
            except Exception:
                continue
        return None

    def _set_composer_text(self, composer, text: str) -> bool:
        if not self.driver:
            return False
        try:
            try: composer.click()
            except Exception:
                try:
                    self.driver.execute_script('arguments[0].scrollIntoView({behavior:"instant",block:"center"});', composer)
                    self.driver.execute_script('arguments[0].click();', composer)
                except Exception: pass
            try: composer.clear()
            except Exception: pass
            try:
                composer.send_keys(text)
                return True
            except Exception:
                pass
            try:
                self.driver.execute_script(
                    """
                    const el=arguments[0], val=arguments[1];
                    if (el.isContentEditable) { el.focus(); document.execCommand('selectAll',false,null); document.execCommand('insertText', false, val); } else { el.value=val; }
                    el.dispatchEvent(new Event('input',{bubbles:true}));
                    """,
                    composer, text
                )
                return True
            except Exception:
                return False
        except Exception:
            return False

    def _find_post_button(self, composer, override_xpath: Optional[str]) -> Optional[object]:
        assert self.driver
        By = self._by()
        if override_xpath:
            try:
                for b in self.driver.find_elements(By.XPATH, override_xpath):
                    if b.is_displayed() and b.is_enabled():
                        return b
            except Exception:
                pass
        try:
            btn = self.driver.execute_script(
                """
                const KEYS = arguments[1];
                const composer = arguments[0];
                const container = composer.closest('[role="dialog"],[data-pagelet],[aria-modal="true"]') || document.body;
                const cands = Array.from(container.querySelectorAll('[role="button"],button'));
                function good(el){
                  if (el.hasAttribute('disabled') || el.getAttribute('aria-disabled')==='true') return false;
                  const label=(el.getAttribute('aria-label')||'').toLowerCase();
                  const txt=(el.textContent||'').toLowerCase().trim();
                  const testid=(el.getAttribute('data-testid')||'').toLowerCase();
                  if (/react-composer-post-button|composer-post/.test(testid)) return true;
                  return KEYS.some(k=>label.includes(k) || txt===k || txt.startsWith(k) || txt.includes(k));
                }
                for (const el of cands){ if (good(el)) { el.scrollIntoView({behavior:'instant',block:'center'}); return el; } }
                return null;
                """,
                composer,
                list(_POST_KEY_SET),
            )
            if btn: return btn
        except Exception:
            pass
        for xp in [
            "//div[@role='button' and @aria-label='Post']",
            "//span[normalize-space()='Post']/ancestor::div[@role='button']",
            "//span[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'post')]/ancestor::div[@role='button']",
        ]:
            try:
                for b in self.driver.find_elements(By.XPATH, xp):
                    if b.is_displayed() and b.is_enabled():
                        return b
            except Exception:
                continue
        return None

    def _click_post(self, composer, override_xpath: Optional[str]) -> bool:
        btn = self._find_post_button(composer, override_xpath)
        if not btn:
            return False
        try:
            btn.click(); return True
        except Exception:
            try:
                self.driver.execute_script('arguments[0].click();', btn)
                return True
            except Exception:
                return False

    # ---- Posting ----
    def post_to_group(self, item: dict) -> bool:
        assert self.driver
        link = item.get('url') or item.get('link')
        comp_xp = item.get('composer_xpath') or self.cfg.composer_xpath
        post_xp = item.get('post_button_xpath') or self.cfg.post_button_xpath
        self.driver.switch_to.new_window('tab')
        try:
            try:
                self.driver.get(link)
            except Exception as e:
                try:
                    from selenium.common.exceptions import TimeoutException  # type: ignore
                    if isinstance(e, TimeoutException):
                        self.driver.execute_script('window.stop();')
                    else:
                        raise
                except Exception:
                    pass
            self._sleep(1.0, 2.2)
            composer = self._find_composer(comp_xp)
            if not composer:
                self._save_artifacts(link, 'composer-not-found')
                raise RuntimeError('Composer not found')
            self._save_element_debug(composer, 'composer')
            if self.cfg.inspect:
                print(f'[INSPECT] {link}')
                print(f'  composer_xpath_guess: {self._element_xpath(composer)}')
                btn = self._find_post_button(composer, post_xp)
                if btn:
                    self._save_element_debug(btn, 'post-button')
                    print(f'  post_button_xpath_guess: {self._element_xpath(btn)}')
                else:
                    print('  post_button_xpath_guess: <not-found>')
                return True
            if not self._set_composer_text(composer, self.cfg.message):
                self._save_artifacts(link, 'composer-type-failed')
                raise RuntimeError('Failed to set message text')
            time.sleep(self.cfg.prepost_wait)
            if self.cfg.manual_post:
                print('[MANUAL] Click Post in browser, then press Enter here (Ctrl+C abort).')
                try: input()
                except Exception: pass
            else:
                if not self._click_post(composer, post_xp):
                    self._save_artifacts(link, 'post-button-not-found')
                    raise RuntimeError('Post button not clicked')
            self._sleep(2.5, 4.5)
            return True
        except Exception as e:
            print(f'[WARN] {link} -> {e}')
            return False
        finally:
            try:
                self.driver.close()
                root = self.driver.window_handles[0]
                self.driver.switch_to.window(root)
            except Exception:
                pass

    # ---- Run Loop ----
    def run(self, links: List[dict]):
        if self.cfg.dry_run:
            print(f'[DRY-RUN] Would login as {self.cfg.email} and process {len(links)} links:')
            for i, it in enumerate(links, 1):
                print(f'  {i:02d}. {it.get("url")}')
            return
        self._init_driver()
        try:
            self.login()
            ok = 0
            for idx, item in enumerate(links, 1):
                print(f'[{idx}/{len(links)}] {item.get("url")}')
                if self.post_to_group(item):
                    ok += 1
                self._sleep()
            if self.cfg.inspect:
                print(f'Inspect complete. {ok}/{len(links)} processed (no posts attempted).')
            else:
                print(f'Done. Success {ok}/{len(links)}')
        finally:
            try:
                if self.driver:
                    self.driver.quit()
            except Exception:
                pass

# ---------------------------------- Main Entry ----------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    cfg = parse_args(argv)
    if cfg.debug:
        print('[DEBUG] Config:')
        for k, v in cfg.__dict__.items():
            if k == 'password':
                continue
            print(f'  {k}={v!r}')
    try:
        links = read_links(cfg.links_file, cfg.limit)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    if not links:
        print('No valid facebook.com links found.', file=sys.stderr)
        return 1
    if cfg.dry_run:
        print(f'Found {len(links)} links.')
    FacebookPoster(cfg).run(links)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
