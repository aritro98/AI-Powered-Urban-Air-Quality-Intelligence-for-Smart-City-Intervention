"""
BaseAgent — shared plumbing for every reasoning agent:
  - trace logging (so the orchestrator can expose a real execution trace)
  - a reason_with_llm() hook that is a no-op until ANTHROPIC_API_KEY is set,
    at which point it makes a real Claude API call. Every agent that
    currently uses a heuristic/template fallback calls this hook FIRST and
    only falls back if it returns None — so adding a key upgrades the
    whole system without touching agent logic.
"""
import time
import config

_client = None
if config.USE_LLM:
    import anthropic
    _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


class BaseAgent:
    name = "BaseAgent"

    def __init__(self, trace):
        self.trace = trace

    def log(self, action, source="internal", detail=""):
        self.trace.append({
            "agent": self.name,
            "action": action,
            "source": source,
            "detail": detail,
            "t": round(time.time(), 3),
        })

    def reason_with_llm(self, system_prompt, user_prompt, max_tokens=400):
        """Returns Claude's text response, or None if no API key is
        configured / the call fails. Callers must handle None by using
        their rule-based fallback. Logs WHY it returned None distinctly
        (no key configured vs. an actual API error) so the trace console
        and UI don't make "no key yet" look like a broken system."""
        if not config.USE_LLM:
            self.log("reason_with_llm", "not_configured", "no ANTHROPIC_API_KEY set -- using rule-based fallback by design")
            return None
        try:
            resp = _client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = "".join(block.text for block in resp.content if block.type == "text")
            self.log("reason_with_llm", "live", "Claude API call")
            return text.strip()
        except Exception as exc:
            self.log("reason_with_llm", "fallback", f"Anthropic API error: {exc}")
            return None