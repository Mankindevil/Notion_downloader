from pathlib import Path
import re


src = Path("C:/Users/Jinting/.claude/skills/fashion-magazine-cover/assets/cover_skeletons.html")
out = Path("o:/Coding/Claude/fashion_magazine_cover/chloe_new/cover_role_special/cover_options.html")
html = src.read_text(encoding="utf-8")

html = html.replace("--cw: 1240; --ch: 1650;", "--cw: 759; --ch: 1024;")
html = html.replace("--cw: 1860; --ch: 1240;", "--cw: 759; --ch: 1024;")
html = html.replace("url('subject.jpg')", "url('../chloe_safe.png')")

for fx in ["fx-vignette", "fx-rim-light", "fx-shade-top", "fx-shade-bottom"]:
    html = re.sub(rf"\n\s*<div class=\"{fx}\"></div>", "", html)
html = re.sub(r"\n\s*<div class=\"fx-sparkle\"[^>]*>.*?</div>", "", html)

repl = {
    "{{S1_CJK_1}}": "角色",
    "{{S1_CJK_2}}": "特辑",
    "{{S1_ENGLISH_TITLE}}": "Chloe",
    "{{S1_ENGLISH_SUBTITLE}}": "CHARACTER ISSUE",
    "{{S1_DATELINE_1}}": "MAY 2026",
    "{{S1_DATELINE_2}}": "SPECIAL VIDEO EDITION",
    "{{S1_BADGE_NUM}}": "12",
    "{{S1_BADGE_TEXT}}": "EXCLUSIVE SCENES",
    "{{S1_VERTICAL_TAGLINE}}": "幕后设定与镜头语言",
    "{{S1_CL1_H}}": "角色档案",
    "{{S1_CL1_SUB}}": "设定关键词、视觉母题与剧情弧线一页读懂",
    "{{S1_CL2_H}}": "镜头拆解",
    "{{S1_CL2_SUB}}": "高光段落分镜解析与情绪节奏",
    "{{S1_CL3_H}}": "造型进化",
    "{{S1_CL3_SUB}}": "从初登场到最终形象的风格演进",
    "{{S1_SIG_NAME}}": "Chloe",
    "{{S1_SIG_TAGLINE}}": "THE CHARACTER SPOTLIGHT",
    "{{S2_MASTHEAD}}": "SCREEN",
    "{{S2_DATELINE}}": "CHARACTER EDITION - MAY 2026",
    "{{S2_HERO_HEADLINE}}": "Chloe's Signature Era",
    "{{S2_HERO_SUB}}": "THE VIDEO SPECIAL",
    "{{S2_CL1_H}}": "Story Beats",
    "{{S2_CL1_SUB}}": "How each scene builds character presence.",
    "{{S2_CL2_H}}": "Visual Language",
    "{{S2_CL2_SUB}}": "Color, rhythm and frame choices behind the persona.",
    "{{S2_ISSUE_TEXT}}": "VOL.18 NO.05",
    "{{S3_MASTHEAD}}": "Spotlight",
    "{{S3_SUB_CJK}}": "角色特辑",
    "{{S3_SUB_ROMAJI}}": "CHARACTER ISSUE",
    "{{S3_ISSUE_1}}": "MAY 2026",
    "{{S3_ISSUE_2}}": "VIDEO SPECIAL",
    "{{S3_ISSUE_3}}": "VOL.18",
    "{{S3_PRICE}}": "+28",
    "{{S3_BADGE_LABEL}}": "PAGES",
    "{{S3_CL1_H}}": "幕后访谈",
    "{{S3_CL1_SUB}}": "主创谈角色立体感与情绪调度",
    "{{S3_CL2_H}}": "必看场景",
    "{{S3_CL2_SUB}}": "本期精选 10 个高能镜头",
    "{{S3_CL3_H}}": "造型手册",
    "{{S3_CL3_SUB}}": "色彩与配饰如何支撑角色记忆点",
    "{{S3_CL4_H}}": "台词金句",
    "{{S3_CL4_SUB}}": "最能定义人物弧光的关键台词",
    "{{S3_NAME}}": "Chloe",
    "{{S3_TAGLINE}}": "ONLY CHARACTER, ONLY IMPACT",
    "{{S4_BLOCK_TEXT}}": "spot\nlight",
    "{{S4_ISSUE_1}}": "MAY 2026",
    "{{S4_ISSUE_2}}": "CHARACTER",
    "{{S4_ISSUE_3}}": "SPECIAL",
    "{{S4_RULE_LABEL}}": "VIDEO FOCUS",
    "{{S4_CL1}}": "scene by scene, she rewrites the tone",
    "{{S4_CL1_TAG}}": "ANALYSIS",
    "{{S4_CL2}}": "the details that make a character iconic",
    "{{S4_CL2_TAG}}": "STYLE FILE",
    "{{S4_CL3}}": "one issue dedicated to a single presence",
    "{{S4_CL3_TAG}}": "EDITOR'S PICK",
    "{{S4_NAME}}": "CHLOE",
    "{{S4_NAME_TAG}}": " character focus",
    "{{S5_MASTHEAD}}": "FOCUS",
    "{{S5_MASTHEAD_SUB}}": "CHARACTER ISSUE",
    "{{S5_ISSUE_TEXT}}": "MAY 2026  VOL.18",
    "{{S5_CL1_H}}": "Hero Scene",
    "{{S5_CL1_SUB}}": "Why this frame defines the whole arc.",
    "{{S5_CL2_H}}": "Style DNA",
    "{{S5_CL2_SUB}}": "The motifs that shape Chloe's identity.",
    "{{S5_NAME}}": "Chloe",
}

for key, value in repl.items():
    html = html.replace(key, value)

out.write_text(html, encoding="utf-8")
print(out)
