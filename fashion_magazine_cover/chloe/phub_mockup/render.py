"""Render overlay.html at configured aspect ratios via Playwright.
Text content comes from config.json; only IDs in the HTML are touched —
the HTML still opens directly in a browser for default preview.
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
HTML = HERE / "overlay.html"
CONFIG = HERE / "config.json"


# JS function that takes the parsed config and applies it to the DOM.
APPLY_CONFIG_JS = r"""
(cfg) => {
  // simple "set textContent if id exists and value is provided" helper
  const setText = (id, val) => {
    if (val === undefined || val === null) return;
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  if (cfg.stream) {
    setText("cfg-title",          cfg.stream.title);
    setText("cfg-subtitle",       cfg.stream.subtitle);
    setText("cfg-viewers",        cfg.stream.viewers);
    setText("cfg-viewers-label",  cfg.stream.viewers_label);
    setText("cfg-elapsed",        cfg.stream.elapsed);
    setText("cfg-quality",        cfg.stream.quality);
    setText("cfg-live-mini",      cfg.stream.live_mini);
  }
  if (cfg.channel) {
    setText("cfg-channel-name", cfg.channel.name);
    setText("cfg-followers",    cfg.channel.followers);
  }
  if (cfg.interact) {
    setText("cfg-likes",  cfg.interact.likes);
    setText("cfg-follow", cfg.interact.follow);
    setText("cfg-tip",    cfg.interact.tip);
  }

  // tags — clear and rebuild
  if (Array.isArray(cfg.tags)) {
    const tagsEl = document.getElementById("cfg-tags");
    if (tagsEl) {
      tagsEl.innerHTML = "";
      cfg.tags.forEach(t => {
        const span = document.createElement("span");
        span.className = "tag";
        span.textContent = t;
        tagsEl.appendChild(span);
        // CSS :nth-child rules handle rotation per position
      });
    }
  }

  // chat — clear and rebuild
  if (Array.isArray(cfg.chat)) {
    const chatEl = document.getElementById("cfg-chat");
    if (chatEl) {
      chatEl.innerHTML = "";
      cfg.chat.forEach(m => {
        const div = document.createElement("div");
        div.className = m.superchat ? "msg superchat" : "msg";

        // badge
        if (m.badge) {
          const b = document.createElement("span");
          b.className = "msg-badge " + m.badge;
          b.textContent = m.badge.toUpperCase();
          div.appendChild(b);
        }

        // username
        const u = document.createElement("span");
        u.className = "username";
        if (m.color) u.style.color = m.color;
        u.textContent = m.user;
        div.appendChild(u);

        // body text — append as a text node so it sits inline after username
        div.appendChild(document.createTextNode(m.text || ""));

        // superchat amount chip
        if (m.amount) {
          const a = document.createElement("span");
          a.className = "sc-amount";
          a.textContent = m.amount;
          div.appendChild(a);
        }

        chatEl.appendChild(div);
      });
    }
  }
}
"""


def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    outputs = cfg.get("render", {}).get("outputs") or [
        {"name": "kuro_live_16x9_4k.png", "viewport": [1920, 1080], "scale": 2},
        {"name": "kuro_live_4x5_4k.png",  "viewport": [1536, 1920], "scale": 2},
        {"name": "kuro_live_9x16_4k.png", "viewport": [1080, 1920], "scale": 2},
    ]

    url = HTML.resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for spec in outputs:
            w, h = spec["viewport"]
            dsf = spec.get("scale", 2)
            name = spec["name"]
            ctx = browser.new_context(
                viewport={"width": w, "height": h},
                device_scale_factor=dsf,
            )
            page = ctx.new_page()
            page.goto(url)
            page.wait_for_load_state("networkidle")
            # apply config to DOM
            page.evaluate(APPLY_CONFIG_JS, cfg)
            # small wait so layout settles after dynamic content
            page.wait_for_timeout(400)
            out = HERE / name
            page.screenshot(path=str(out), full_page=False, type="png")
            print(f"  -> {out}  ({out.stat().st_size // 1024} KB) [{w*dsf}x{h*dsf}]")
            ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
