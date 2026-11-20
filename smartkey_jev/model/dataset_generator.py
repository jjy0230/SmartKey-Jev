"""
AnyJev Intent Fine-Tuning Dataset Generator.
Synthesizes high-quality, balanced desktop selection contexts and intent labels
for training small language models (Qwen2.5-1.5B / SmolLM2-1.7B) to act as instant classification heads.
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Any


SAMPLE_TEMPLATES = [
    # IDE / Code Scenarios
    {
        "process": "code.exe",
        "title": "{file}.py - Visual Studio Code",
        "snippets": [
            ("Traceback (most recent call last):\n  File 'app.py', line {line}\n    {expr}\nKeyError: '{key}'", "fix_code"),
            ("NullPointerException: Cannot invoke method on null object at com.api.Service.process(Service.java:{line})", "fix_code"),
            ("def compute_embeddings(tokens: List[int], dim: int = 512) -> np.ndarray:\n    return np.zeros((len(tokens), dim))", "explain_code"),
            ("class ConnectionPool:\n    def __init__(self, size: int = 10):\n        self._pool = asyncio.Queue(maxsize=size)", "explain_code"),
            ("r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$'", "regex_test"),
            ('{"status": 200, "data": {"token": "xyz987", "expired_at": 1700000000}}', "format_json"),
        ]
    },
    # Browser Scenarios
    {
        "process": "chrome.exe",
        "title": "{site_title} - Google Chrome",
        "snippets": [
            ("epistemology", "dictionary"),
            ("serendipity", "dictionary"),
            ("deterministic", "dictionary"),
            ("We propose a novel framework that decouples low-level system hooks from neural intent inference.", "translate"),
            ("The memory overhead of quantized 4-bit weights is drastically reduced compared to FP16 baselines.", "translate"),
            ("https://github.com/jjy0230/SmartKey-Jev", "open_url"),
            ("https://docs.python.org/3/library/ctypes.html", "open_url"),
            ("What is the difference between preemptive multitasking and cooperative scheduling in operating systems?", "search_web"),
        ]
    },
    # Chat / Collaboration Scenarios
    {
        "process": "wechat.exe",
        "title": "项目核心攻坚组",
        "snippets": [
            ("明天下午 15:30 组织在线架构同步会，务必准时参加！", "create_todo"),
            ("下周一上午 10:00 截止第一轮功能提测，请各位知悉。", "create_todo"),
            ("这个方案我感觉还行吧，反正就那样搞搞看。", "polish_text"),
            ("今天把那个东西弄好了，明天再搞这个东西。", "polish_text"),
        ]
    },
    # Terminal Scenarios
    {
        "process": "windowsterminal.exe",
        "title": "PowerShell - Administrator",
        "snippets": [
            ("docker run -d -p 8080:80 --name web-nginx nginx:alpine", "terminal_cmd"),
            ("git rebase -i HEAD~3", "terminal_cmd"),
            ('{"id":"usr_01","role":"developer","active":true}', "format_json"),
        ]
    }
]


def generate_synthetic_dataset(output_path: str, count: int = 1000):
    """Generates synthetic fine-tuning pairs formatted for instruction tuning."""
    records: List[Dict[str, Any]] = []

    files = ["main", "server", "engine", "handler", "router", "models", "utils"]
    keys = ["id", "token", "session", "user_id", "status", "data"]
    site_titles = ["GitHub - Pull Request", "Stack Overflow - Question", "arXiv Computer Science", "MDN Web Docs"]

    for _ in range(count):
        cat = random.choice(SAMPLE_TEMPLATES)
        proc = cat["process"]
        title_fmt = cat["title"]
        file_choice = random.choice(files)
        site_choice = random.choice(site_titles)
        win_title = title_fmt.format(file=file_choice, site_title=site_choice)

        snippet_tmpl, target_macro = random.choice(cat["snippets"])
        try:
            snippet = snippet_tmpl.format(
                line=random.randint(10, 200),
                expr="result = mapping[item]",
                key=random.choice(keys),
            )
        except Exception:
            snippet = snippet_tmpl

        prompt = (
            f"[Desktop Context]\n"
            f"Process: {proc}\n"
            f"Window: {win_title}\n"
            f"Selected Snippet:\n\"\"\"\n{snippet}\n\"\"\"\n\n"
            f"Predict the single optimal macro action ID from the system registry:"
        )

        response = json.dumps({"recommended_macro": target_macro, "confidence": round(random.uniform(0.92, 0.99), 2)})

        records.append({
            "instruction": "You are SmartKey-Jev, a desktop user intent prediction model.",
            "input": prompt,
            "output": response,
        })

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[Dataset Generator] Generated {len(records)} synthetic training samples at: {out_file}")


if __name__ == "__main__":
    generate_synthetic_dataset("data/train_intent.jsonl", count=500)
