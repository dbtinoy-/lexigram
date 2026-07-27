MOCK_IDEAS = """**IDEA #1: The Consistency Paradox
* Core Message: Small daily actions beat big weekly efforts.
* Hook Line: What if everything you knew about success was wrong?
* Identity Signal: This person values discipline over motivation.
* Permission Given: It's okay to start small.
* Emotional Arc: frustration -> clarity
* Target Audience: people who struggle with daily habits
* Quotability Score: 9
* Share Trigger: Tag someone who needs to hear this

**IDEA #2: Embrace the Struggle
* Core Message: Growth requires discomfort — lean into it.
* Hook Line: What if pain is the signal for growth?
* Identity Signal: You are someone who faces challenges head-on.
* Permission Given: It's okay to struggle — that's how you grow.
* Emotional Arc: discomfort -> empowerment
* Target Audience: Ambitious professionals
* Quotability Score: 8.5
* Share Trigger: Tag someone who needs to hear this

**IDEA #3: The Permission Slip
* Core Message: You don't need permission to start — except your own.
* Hook Line: Stop waiting for the perfect moment.
* Identity Signal: You're proactive, not passive.
* Permission Given: You are allowed to take up space.
* Emotional Arc: self-doubt -> confidence
* Target Audience: aspiring creators
* Quotability Score: 9.2
* Share Trigger: Save this for when you need courage"""

MOCK_SCRIPT = """TITLE: The Consistency Paradox
DURATION: 45
WORD COUNT: 85
PACING: 1.9
[HOOK - 5s]
"What if everything you knew about success was wrong?"
[MESSAGE - 25s]
"Success isn't about massive action — it's about tiny, consistent steps."
"The person who shows up every day beats the one who only shows up when motivated."
"Your habits shape your identity more than your goals ever will."
[METAPHOR - 5s]
"Think of it like compound interest for your character."
[CONCLUSION - 5s]
"Start small. Stay consistent. Watch what happens."
EMOTIONAL ARC MAP: frustration -> clarity -> empowerment
PARALLEL STRUCTURE USED: true
HOOK SCORE: 9"""

MOCK_SEO = """YOUTUBE_TITLE: The Consistency Paradox: Why Small Daily Habits Beat Big Weekly Efforts
YOUTUBE_DESCRIPTION: Discover why consistency beats intensity in building lasting habits. Learn how small daily actions compound into extraordinary results.
If you have ever struggled to maintain motivation, this video is for you.

YOUTUBE_TAGS: consistency, habits, personal growth, motivation, daily routine, discipline
FACEBOOK_CAPTION: The secret to success isn't motivation — it's consistency. Watch this short reel to learn why small steps lead to big results."""


def mock_for_prompt(prompt: str) -> str:
    low = prompt.lower()
    if "seo " in low or low.startswith("seo"):
        return MOCK_SEO
    if "generate " in low and "idea" in low:
        return MOCK_IDEAS
    if "script" in low:
        return MOCK_SCRIPT
    if "youtube" in low:
        return MOCK_SEO
    return "Mock response (no LLM available)."
