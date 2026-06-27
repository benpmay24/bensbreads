"""Gemini agent for Clash Center deck coaching."""
import json
import logging
import re
import time

from django.conf import settings

from main.clash_center.analytics import owner_tag
from main.clash_center.tiers import RANKED_TIERS, tier_label
from main.clash_center.tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 8
DEFAULT_MODEL = 'gemini-2.5-flash-lite'
FALLBACK_MODELS = ('gemini-2.5-flash-lite', 'gemini-2.5-flash', 'gemini-2.0-flash-lite')


def agent_configured() -> bool:
    return bool(getattr(settings, 'GEMINI_API_KEY', ''))


def _max_retries() -> int:
    return int(getattr(settings, 'CLASH_CENTER_AGENT_MAX_RETRIES', 5))


def _retry_delay() -> float:
    return float(getattr(settings, 'CLASH_CENTER_AGENT_RETRY_DELAY_SECONDS', 3.0))


def _system_prompt() -> str:
    tag = owner_tag()
    leagues = ', '.join(f'{n}={tier_label(n)}' for n in sorted(RANKED_TIERS))
    return f"""You are Clash Center Coach, an expert Clash Royale ranked (Path of Legends) analyst.

The player's tag is {tag or '(not configured)'}.
Leagues: {leagues}

You have read-only tools to query battle data scraped from ranked battle logs. ALWAYS use tools to look up data before answering questions about meta, win rates, decks, or matchups. Never invent statistics.

Card knowledge:
- Use list_card_catalog or lookup_cards for elixir costs, rarity, evolution info, and valid card names
- The full card catalog is stored in the database and synced from the Clash Royale API

Your deck data (from scraped battle logs — NOT live API):
- Use get_my_recent_deck when the user asks about their current, latest, or most recently used deck
- Use get_my_decks (no tier arg) for most-used decks across all leagues
- Use get_recent_battles with mine_only=true for raw battle history
- Do NOT call get_my_decks once per league tier — one call with no tier is enough

When optimizing decks:
- Cite win rates, 95% Wilson confidence intervals, and p-values when available
- Top league decks require 20+ battles and p<0.05 vs league baseline
- Prefer statistically significant cards/decks over small-sample outliers
- Be practical: suggest 1-2 card swaps, not full deck rebuilds unless data strongly supports it
- Check average elixir when suggesting deck changes

Keep responses concise and actionable. Use bullet points for deck recommendations."""


def _gemini_tools():
    from google.genai import types

    declarations = [
        types.FunctionDeclaration(
            name=t['name'],
            description=t['description'],
            parameters=t['input_schema'],
        )
        for t in TOOL_DEFINITIONS
    ]
    return [types.Tool(function_declarations=declarations)]


def _to_gemini_contents(messages: list[dict]):
    from google.genai import types

    contents = []
    for message in messages:
        content = message.get('content')
        if not content:
            continue
        role = 'user' if message['role'] == 'user' else 'model'
        contents.append(types.Content(role=role, parts=[types.Part(text=content)]))
    return contents


def _models_to_try() -> list[str]:
    configured = getattr(settings, 'CLASH_CENTER_AGENT_MODEL', DEFAULT_MODEL)
    models = [configured]
    for model in FALLBACK_MODELS:
        if model not in models:
            models.append(model)
    return models


def _retry_delay_seconds(exc) -> float | None:
    message = str(exc)
    match = re.search(r'retry in ([\d.]+)s', message, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _error_code(exc) -> int | None:
    return getattr(exc, 'code', None) or getattr(exc, 'status_code', None)


def _is_quota_exhausted(exc) -> bool:
    text = str(exc)
    if 'limit: 0' in text:
        return True
    if 'PerDay' in text or 'PerDayPerProject' in text:
        return True
    if 'RESOURCE_EXHAUSTED' in text and 'retry in' not in text.lower():
        return True
    return False


def _should_retry_gemini_error(exc) -> bool:
    from google.genai import errors as genai_errors

    if not isinstance(exc, genai_errors.ClientError):
        return False
    if _is_quota_exhausted(exc):
        return False
    code = _error_code(exc)
    if code in (429, 500, 503):
        return True
    text = str(exc).upper()
    return 'UNAVAILABLE' in text or 'RESOURCE_EXHAUSTED' in text


def _friendly_gemini_error(exc, model: str) -> tuple[str, int]:
    from google.genai import errors as genai_errors

    if isinstance(exc, genai_errors.ClientError):
        text = str(exc).upper()
        code = _error_code(exc)
        if code == 503 or 'UNAVAILABLE' in text:
            return (
                f'Gemini model {model} is temporarily overloaded. Please try again shortly.',
                503,
            )
        if code == 429:
            retry_after = _retry_delay_seconds(exc)
            if retry_after:
                wait = max(1, int(retry_after))
                return (
                    f'Gemini rate limit hit for {model}. Wait about {wait}s and try again. '
                    'Free tier has strict limits — check https://aistudio.google.com/',
                    429,
                )
            return (
                f'Gemini quota exhausted for {model}. '
                'Try CLASH_CENTER_AGENT_MODEL=gemini-2.5-flash-lite or check '
                'https://aistudio.google.com/',
                429,
            )

    return (str(exc), 500)


def _generate_with_retry(client, model: str, contents, config):
    from google.genai import errors as genai_errors

    max_attempts = _max_retries()
    delay = _retry_delay()
    last_exc = None

    for attempt in range(max_attempts):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except genai_errors.ClientError as exc:
            last_exc = exc
            if attempt >= max_attempts - 1:
                raise
            if not _should_retry_gemini_error(exc):
                raise

            wait = _retry_delay_seconds(exc)
            if wait is None:
                wait = delay
            wait = min(max(wait, 2), 45)
            logger.warning(
                'Gemini error (attempt %d/%d) for %s: %s — retrying in %.1fs',
                attempt + 1,
                max_attempts,
                model,
                exc,
                wait,
            )
            time.sleep(wait)
            delay = min(delay * 1.5, 25)

    raise last_exc


def _should_try_fallback_model(exc) -> bool:
    from google.genai import errors as genai_errors

    if not isinstance(exc, genai_errors.ClientError):
        return False
    if _is_quota_exhausted(exc):
        return True
    code = _error_code(exc)
    if code in (429, 500, 503):
        return True
    text = str(exc).upper()
    return 'UNAVAILABLE' in text


def run_agent(messages: list[dict]) -> dict:
    """
    Run the agent with conversation history.
    messages: [{role: user|assistant, content: str}, ...]
    Returns {reply: str, messages: updated history for client}
    """
    if not agent_configured():
        return {
            'error': 'GEMINI_API_KEY is not configured',
            'reply': None,
            'status': 503,
        }

    from google import genai
    from google.genai import errors as genai_errors
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    config = types.GenerateContentConfig(
        system_instruction=_system_prompt(),
        tools=_gemini_tools(),
    )

    contents = _to_gemini_contents(messages)
    client_history = list(messages)
    last_error = None
    last_status = 500

    for model in _models_to_try():
        try:
            for _ in range(MAX_TOOL_ROUNDS):
                response = _generate_with_retry(client, model, contents, config)

                if not response.candidates:
                    return {
                        'error': 'No response from model',
                        'reply': None,
                        'messages': client_history,
                        'status': 502,
                    }

                candidate = response.candidates[0]
                if not candidate.content:
                    logger.warning('Gemini returned empty content for %s', model)
                    client_history.append({
                        'role': 'assistant',
                        'content': (
                            'I had trouble reading the battle data. '
                            'Please try asking again.'
                        ),
                    })
                    return {
                        'error': 'Empty model response',
                        'reply': client_history[-1]['content'],
                        'messages': client_history,
                        'status': 502,
                    }

                parts = candidate.content.parts or []
                function_calls = [part for part in parts if part.function_call]

                if not function_calls:
                    text = (response.text or '').strip()
                    if not text:
                        text = 'I was unable to complete that request.'
                    client_history.append({'role': 'assistant', 'content': text})
                    return {'reply': text, 'messages': client_history}

                contents.append(candidate.content)

                response_parts = []
                for part in function_calls:
                    function_call = part.function_call
                    args = dict(function_call.args) if function_call.args else {}
                    result_str = execute_tool(function_call.name, args)
                    response_parts.append(
                        types.Part.from_function_response(
                            name=function_call.name,
                            response=json.loads(result_str),
                        )
                    )
                contents.append(types.Content(role='user', parts=response_parts))

            fallback = (
                'I needed too many data lookups for that question. '
                'Try a more specific question.'
            )
            client_history.append({'role': 'assistant', 'content': fallback})
            return {
                'error': 'Tool loop limit reached',
                'reply': fallback,
                'messages': client_history,
            }

        except genai_errors.ClientError as exc:
            last_error, last_status = _friendly_gemini_error(exc, model)
            if _should_try_fallback_model(exc):
                logger.warning(
                    'Gemini failed for %s after retries, trying fallback model',
                    model,
                )
                contents = _to_gemini_contents(messages)
                continue
            logger.exception('Gemini API error for %s', model)
            return {
                'error': last_error,
                'reply': None,
                'messages': client_history,
                'status': last_status,
            }
        except Exception as exc:
            logger.exception('Gemini API error for %s', model)
            return {
                'error': str(exc),
                'reply': None,
                'messages': client_history,
                'status': 500,
            }

    return {
        'error': last_error or 'Gemini API request failed after retries',
        'reply': None,
        'messages': client_history,
        'status': last_status,
    }
