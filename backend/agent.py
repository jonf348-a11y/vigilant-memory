import anthropic
import json
import re
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

HETHERSETT_CONTEXT = """
You are helping two environmental groups in Hethersett, Norfolk, England:

**HEAT** (Hethersett Environmental Action Team): A self-funded committee of Hethersett Parish Council.
**HEAG** (Hethersett Environmental Action Group): A working group running the "Happy Healthy Hethersett" project in partnership with OPERGY, helping Hethersett reach net zero.

Location: Hethersett, Norfolk (South Norfolk District), England
Population: ~5,000 residents
Council type: Parish Council

Focus areas:
- Tree planting and rewilding
- Solar panels, renewable energy, insulation, and heat pumps
- Biodiversity surveys and monitoring
- Community education and events
- Electric vehicles and sustainable transport
- Net zero and climate action generally

These groups are run by community volunteers. They need straightforward, practical grants they can realistically apply for.
"""

GRANT_SEARCH_SYSTEM = f"""{HETHERSETT_CONTEXT}

Your task is to find real, active environmental grants that HEAT or HEAG could apply for.

Search for grants from:
- UK government (DEFRA, DESNZ, Forestry Commission, Environment Agency, etc.)
- Norfolk County Council, South Norfolk Council / Breckland District Council
- Lottery Heritage Fund, National Lottery Community Fund
- Environmental charities (WWF, RSPB, The Wildlife Trusts, Trees for Cities, etc.)
- Energy company obligations (ECO4, GBIS, etc.)
- EU LIFE programme (UK still eligible for some)
- Corporate CSR grant programmes
- Community energy funds

For each grant found, extract:
- title
- funder (organisation offering the grant)
- description (2-3 sentences on what it funds)
- url (direct link to the grant page)
- deadline (if known, otherwise "rolling" or "unknown")
- max_amount (maximum award in GBP as integer, or null)
- min_amount (minimum award in GBP as integer, or null)
- focus_areas (list of relevant tags from: tree planting, rewilding, solar, energy, insulation, heat pumps, biodiversity, education, electric vehicles, net zero, community)
- eligibility_notes (brief notes on eligibility relevant to parish councils / community groups)

Return results as a JSON array. Only return grants that are currently open or regularly recurring. Do not include expired grants.
"""

APPLY_HELPER_SYSTEM = f"""{HETHERSETT_CONTEXT}

You are a friendly grant application assistant helping volunteers at HEAT and HEAG complete grant applications.

Your role:
1. Ask questions to gather the information needed for the application
2. Help draft compelling answers based on the group's work
3. Explain what funders are typically looking for
4. Keep language clear and jargon-free — these are community volunteers, not professional grant writers
5. Be encouraging and practical

When helping with an application:
- Ask one or two questions at a time (don't overwhelm)
- Summarise what you know so far periodically
- Offer to draft text they can copy and edit
- Flag any tricky sections or common pitfalls

Stay focused on the specific grant being discussed. Be warm, supportive, and concise.
"""


def search_grants_sync(focus_areas: list[str]) -> list[dict]:
    """Run grant search agent and return list of grant dicts."""
    areas_str = ", ".join(focus_areas)
    prompt = f"""Please search for environmental grants that HEAT and HEAG in Hethersett, Norfolk can apply for.

Focus areas requested: {areas_str}

Search thoroughly across multiple sources. Use multiple web searches — search for:
1. UK community environmental grants {areas_str}
2. Norfolk parish council environmental grants
3. National Lottery community grants environment Norfolk
4. DEFRA / Forestry Commission grants community groups
5. Any other relevant sources

Return a JSON array of grants. Each grant object must have these fields:
- title (string)
- funder (string)
- description (string)
- url (string or null)
- deadline (string or null)
- max_amount (integer GBP or null)
- min_amount (integer GBP or null)
- focus_areas (array of strings)
- eligibility_notes (string)

Wrap the JSON array in ```json ... ``` markers.
"""

    messages = [{"role": "user", "content": prompt}]

    for _ in range(15):
        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=8000,
            system=GRANT_SEARCH_SYSTEM,
            tools=[{"type": "web_search_20260209", "name": "web_search"}],
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            text = "".join(
                block.text for block in response.content if hasattr(block, "text")
            )
            return _parse_grants_json(text)

        # tool_use stop — append assistant turn and loop
        messages.append({"role": "assistant", "content": response.content})

        # Collect tool results
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "",  # web_search results are injected server-side
                })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    return []


def _parse_grants_json(text: str) -> list[dict]:
    """Extract JSON array from model response text."""
    # Try fenced JSON block first
    match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if match:
        raw = match.group(1)
    else:
        # Fall back to finding first [ ... ] array
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            return []
        raw = match.group(0)

    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        return []
    except json.JSONDecodeError:
        return []


def chat_with_assistant(
    grant: dict,
    conversation_history: list[dict],
    user_message: str,
) -> str:
    """Continue a grant application help conversation."""
    grant_context = f"""
Grant being applied for:
- Title: {grant.get('title', 'Unknown')}
- Funder: {grant.get('funder', 'Unknown')}
- Description: {grant.get('description', '')}
- Max amount: £{grant.get('max_amount', 'unknown')}
- Deadline: {grant.get('deadline', 'unknown')}
- Eligibility notes: {grant.get('eligibility_notes', '')}
"""

    messages = list(conversation_history)
    if not messages:
        # First message — prepend grant context
        messages.append({
            "role": "user",
            "content": f"{grant_context}\n\nUser question: {user_message}",
        })
    else:
        messages.append({"role": "user", "content": user_message})

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2000,
        system=APPLY_HELPER_SYSTEM,
        messages=messages,
    )

    return response.content[0].text
