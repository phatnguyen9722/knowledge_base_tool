"""Email Composer — template-based email drafting.

Layout under ``emails/``:
    emails/
      welcome-new-user.md       # custom templates
      follow-up-meeting.md

Each file uses frontmatter for metadata:
    ---
    title: Welcome New User
    subject: Welcome to {{company}}, {{name}}!
    category: onboarding
    builtin: false
    variables: ["name", "company", "role"]
    description: Warm welcome email for new team members
    created: 2026-07-03
    updated: 2026-07-03
    ---
    Body text with {{variable}} placeholders...

Built-in templates are seeded on first startup and stored with ``builtin: true``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import frontmatter
from slugify import slugify

__all__ = ["EmailTemplate", "EmailManager"]

BUILTIN_TEMPLATES = [
    {
        "slug": "welcome-new-user",
        "title": "Welcome New User",
        "subject": "Welcome to {{company}}, {{name}}! 🎉",
        "category": "onboarding",
        "description": "Warm welcome email for new team members or customers.",
        "variables": ["name", "company", "role", "sender_name"],
        "builtin": True,
        "content": """Hi {{name}},

Welcome aboard! We're thrilled to have you join {{company}} as our new {{role}}.

Here's what you can expect in your first few days:

- **Day 1:** Onboarding session and account setup
- **Day 2-3:** Meet the team and explore your workspace
- **Week 1:** Get hands-on with your first project

If you have any questions, don't hesitate to reach out — my door is always open.

Looking forward to working together!

Best regards,
{{sender_name}}
""",
    },
    {
        "slug": "follow-up-meeting",
        "title": "Follow-Up After Meeting",
        "subject": "Follow-up: {{meeting_topic}} — Next Steps",
        "category": "business",
        "description": "Professional follow-up after a meeting with action items.",
        "variables": ["name", "meeting_topic", "meeting_date", "action_items", "sender_name"],
        "builtin": True,
        "content": """Hi {{name}},

Thank you for taking the time to meet with me on {{meeting_date}} to discuss {{meeting_topic}}.

It was a productive conversation, and I wanted to summarise our key takeaways and next steps:

**Action Items:**
{{action_items}}

Please let me know if I've missed anything or if you'd like to adjust the plan.

I'll follow up again by end of next week. Feel free to reach out if you need anything in the meantime.

Best,
{{sender_name}}
""",
    },
    {
        "slug": "cold-outreach",
        "title": "Cold Outreach",
        "subject": "Quick idea for {{company}} — worth a chat?",
        "category": "sales",
        "description": "Short, personalised cold email for reaching new prospects.",
        "variables": ["first_name", "company", "pain_point", "value_prop", "sender_name", "sender_company"],
        "builtin": True,
        "content": """Hi {{first_name}},

I noticed {{company}} is focused on {{pain_point}} — a challenge we see often.

At {{sender_company}}, we help teams like yours with {{value_prop}}. Our customers typically see results within the first 30 days.

Would you be open to a 15-minute call this week? I'm happy to fit around your schedule.

No pressure either way — just thought it might be worth exploring.

Best,
{{sender_name}}
""",
    },
    {
        "slug": "newsletter",
        "title": "Monthly Newsletter",
        "subject": "{{month}} Update: What's New at {{company}} 📰",
        "category": "marketing",
        "description": "Clean monthly newsletter template with sections.",
        "variables": ["month", "company", "highlight_1", "highlight_2", "highlight_3", "cta_link", "sender_name"],
        "builtin": True,
        "content": """Hello,

Here's your {{month}} update from {{company}}. Here's a quick look at what's been happening:

---

## ✨ Highlights this month

**{{highlight_1}}**

**{{highlight_2}}**

**{{highlight_3}}**

---

## 🚀 Coming up next month

We have some exciting things in the pipeline — stay tuned!

[Read More →]({{cta_link}})

---

Thank you for being part of our community. As always, we'd love to hear your thoughts.

Warm regards,
{{sender_name}} & the {{company}} team
""",
    },
    {
        "slug": "thank-you",
        "title": "Thank You",
        "subject": "Thank you, {{name}} — truly appreciated",
        "category": "personal",
        "description": "Heartfelt thank-you email for any occasion.",
        "variables": ["name", "reason", "specific_detail", "sender_name"],
        "builtin": True,
        "content": """Hi {{name}},

I just wanted to take a moment to say thank you for {{reason}}.

{{specific_detail}}

It really made a difference, and I'm genuinely grateful for your support. I hope I can return the favour someday.

With appreciation,
{{sender_name}}
""",
    },
    {
        "slug": "meeting-invite",
        "title": "Meeting Invitation",
        "subject": "Invitation: {{meeting_title}} — {{date}} at {{time}}",
        "category": "business",
        "description": "Clear and professional meeting invitation.",
        "variables": ["name", "meeting_title", "date", "time", "location", "agenda", "sender_name"],
        "builtin": True,
        "content": """Hi {{name}},

I'd like to invite you to a meeting:

**📅 Date:** {{date}}
**⏰ Time:** {{time}}
**📍 Location / Link:** {{location}}

**Agenda:**
{{agenda}}

Please let me know if this time works for you, or suggest an alternative that fits your schedule.

See you there!

Best,
{{sender_name}}
""",
    },
    {
        "slug": "apology",
        "title": "Professional Apology",
        "subject": "Apology regarding {{issue}} — {{company}}",
        "category": "business",
        "description": "Sincere apology for a service failure or mistake.",
        "variables": ["name", "issue", "company", "resolution", "compensation", "sender_name"],
        "builtin": True,
        "content": """Dear {{name}},

I'm writing to sincerely apologise for {{issue}}. This falls short of the standard we hold ourselves to at {{company}}, and I'm truly sorry for any inconvenience caused.

Here's what we're doing to resolve this:
{{resolution}}

As a gesture of goodwill, we'd like to offer: {{compensation}}

We take your experience seriously, and I want to assure you that steps have been taken to prevent this from happening again.

Thank you for your understanding and patience.

Sincerely,
{{sender_name}}
""",
    },
    {
        "slug": "job-application",
        "title": "Job Application",
        "subject": "Application for {{position}} — {{your_name}}",
        "category": "career",
        "description": "Professional job application cover email.",
        "variables": ["hiring_manager", "position", "company", "your_name", "key_skill_1", "key_skill_2", "years_experience"],
        "builtin": True,
        "content": """Dear {{hiring_manager}},

I am writing to express my interest in the {{position}} role at {{company}}. With {{years_experience}} years of experience, I believe I can make a meaningful contribution to your team.

My background includes:

- **{{key_skill_1}}** — with hands-on project experience delivering real results
- **{{key_skill_2}}** — applied across multiple industries and team sizes

I am particularly drawn to {{company}} because of your commitment to innovation and your strong team culture. I would love the opportunity to bring my skills and enthusiasm to your organisation.

I have attached my CV and portfolio for your review. I would welcome the chance to discuss this role further at your convenience.

Thank you for your time and consideration.

Kind regards,
{{your_name}}
""",
    },
]


def _extract_variables(text: str) -> list[str]:
    """Extract {{variable}} placeholders from text, preserving order, deduplicating."""
    found = re.findall(r"\{\{(\w+)\}\}", text)
    seen, out = set(), []
    for v in found:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


@dataclass
class EmailTemplate:
    slug: str
    title: str
    subject: str
    content: str
    category: str = "general"
    description: str = ""
    variables: list[str] = field(default_factory=list)
    builtin: bool = False
    created: str = ""
    updated: str = ""

    @property
    def all_variables(self) -> list[str]:
        """Variables detected across both subject and body."""
        return _extract_variables(self.subject + "\n" + self.content)

    @property
    def category_label(self) -> str:
        labels = {
            "onboarding": "🎉 Onboarding",
            "business":   "💼 Business",
            "sales":      "📈 Sales",
            "marketing":  "📣 Marketing",
            "personal":   "💌 Personal",
            "career":     "🏆 Career",
            "general":    "📧 General",
        }
        return labels.get(self.category, self.category.title())


class EmailManager:
    def __init__(self, emails_dir: Path):
        self.emails_dir = Path(emails_dir)
        self.emails_dir.mkdir(parents=True, exist_ok=True)
        self._seed_builtins()

    def _path(self, slug: str) -> Path:
        return self.emails_dir / f"{slug}.md"

    def _unique_slug(self, title: str) -> str:
        base = slugify(title, allow_unicode=True) or "template"
        slug, n = base, 2
        while self._path(slug).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug

    def _seed_builtins(self) -> None:
        """Write built-in templates if they don't already exist."""
        today = date.today().isoformat()
        for t in BUILTIN_TEMPLATES:
            path = self._path(t["slug"])
            if not path.exists():
                meta = {
                    "title": t["title"],
                    "subject": t["subject"],
                    "category": t["category"],
                    "description": t["description"],
                    "variables": t["variables"],
                    "builtin": True,
                    "created": today,
                    "updated": today,
                }
                fm = frontmatter.Post(t["content"], **meta)
                path.write_text(frontmatter.dumps(fm), encoding="utf-8")

    def _read_file(self, path: Path) -> EmailTemplate | None:
        if not path.exists():
            return None
        fm = frontmatter.load(str(path))
        m = fm.metadata or {}
        slug = path.stem
        return EmailTemplate(
            slug=slug,
            title=str(m.get("title", slug)),
            subject=str(m.get("subject", "")),
            content=fm.content,
            category=str(m.get("category", "general")),
            description=str(m.get("description", "")),
            variables=list(m.get("variables") or []),
            builtin=bool(m.get("builtin", False)),
            created=str(m.get("created", "")),
            updated=str(m.get("updated", "")),
        )

    def read(self, slug: str) -> EmailTemplate | None:
        return self._read_file(self._path(slug))

    def list(self, q: str = "", category: str = "") -> list[EmailTemplate]:
        templates = []
        for f in sorted(self.emails_dir.glob("*.md")):
            t = self._read_file(f)
            if t:
                templates.append(t)
        if q:
            ql = q.lower()
            templates = [t for t in templates if ql in t.title.lower() or ql in t.description.lower() or ql in t.subject.lower()]
        if category:
            templates = [t for t in templates if t.category == category]
        # Builtins first, then alphabetical
        templates.sort(key=lambda t: (not t.builtin, t.title.lower()))
        return templates

    def categories(self) -> list[str]:
        cats: set[str] = set()
        for f in self.emails_dir.glob("*.md"):
            t = self._read_file(f)
            if t:
                cats.add(t.category)
        return sorted(cats)

    def create(self, data: dict) -> str:
        slug = self._unique_slug(data.get("title", ""))
        today = date.today().isoformat()
        content = data.get("content", "")
        meta = {
            "title": data.get("title", "").strip() or slug,
            "subject": data.get("subject", "").strip(),
            "category": data.get("category", "general").strip(),
            "description": data.get("description", "").strip(),
            "variables": _extract_variables(data.get("subject", "") + "\n" + content),
            "builtin": False,
            "created": today,
            "updated": today,
        }
        fm = frontmatter.Post(content, **meta)
        self._path(slug).write_text(frontmatter.dumps(fm), encoding="utf-8")
        return slug

    def update(self, slug: str, data: dict) -> str | None:
        existing = self.read(slug)
        if not existing:
            return None
        content = data.get("content", existing.content)
        meta = {
            "title": data.get("title", existing.title).strip() or existing.title,
            "subject": data.get("subject", existing.subject).strip(),
            "category": data.get("category", existing.category).strip(),
            "description": data.get("description", existing.description).strip(),
            "variables": _extract_variables(data.get("subject", existing.subject) + "\n" + content),
            "builtin": existing.builtin,
            "created": existing.created or date.today().isoformat(),
            "updated": date.today().isoformat(),
        }
        fm = frontmatter.Post(content, **meta)
        self._path(slug).write_text(frontmatter.dumps(fm), encoding="utf-8")
        return slug

    def delete(self, slug: str) -> bool:
        t = self.read(slug)
        if not t or t.builtin:
            return False  # cannot delete built-ins
        self._path(slug).unlink()
        return True
