"""
Deep grant research agent for HEAT and HEAG, Hethersett, Norfolk.

Runs up to 6 specialist research phases covering the full UK environmental
grant landscape. Volunteers select which phases to run before starting.

Phase order:
  1  public_lottery     – National Lottery, NLCF, government nature schemes
  2  energy_climate     – Community energy, EV, insulation, climate action
  3  nature_wildlife    – Wildlife Trusts, RSPB, Woodland Trust, Biffa, etc.
  4  community_norfolk  – Groundwork, Norfolk funders, offshore wind, S106/CIL
  5  trusts_corporate   – Major trusts, supermarkets, energy companies, tech
  6  verify_enrich      – Verify and deepen the best leads found (always runs)
"""

import anthropic
import json
import re
import os
from datetime import datetime
from typing import Callable
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

ProgressCallback = Callable[[str, str], None]  # (message, level="info"|"found"|"phase")

MAX_SEARCHES_PER_PHASE = 12  # hard cap on web searches per phase to control cost

# ---------------------------------------------------------------------------
# Shared context injected into every phase
# ---------------------------------------------------------------------------

APPLICANT_PROFILE = """
== APPLICANT PROFILE ==

Organisation 1: HEAT — Hethersett Environmental Action Team
  Type: Self-funded committee of Hethersett Parish Council
  Legal status: Parish council committee (counts as public body for many grants)
  Established: January 2023
  Contact: office@hethersettparishcouncil.gov.uk

Organisation 2: HEAG — Hethersett Environmental Action Group
  Type: Volunteer working group
  Project: "Happy Healthy Hethersett" — formal net zero action plan developed in
           partnership with Opergy Net Zero Ltd (energy services company,
           Manor Farm Barns, Fox Road, Norwich, NR14 7PZ;
           contact: andy.holyland@opergy.co.uk / chris.blincoe@opergy.co.uk)
  Academic partner: University of East Anglia — Public Engagement Observatory
           (UK Energy Research Centre; Dr Jason Chilvers, Prof Tom Hargreaves,
           Dr Phedeas Stephanides)
  Legal status: Community/voluntary group backed by parish council

Location: Hethersett, Norfolk, England
  Postcode area: NR9
  District: South Norfolk (South Norfolk and Breckland Council since 2019)
  County: Norfolk
  Region: East of England / East Anglia
  Rural/Urban: Large village — 8,608 residents (2021 census); semi-rural

== NET ZERO PLAN — KEY FACTS (Opergy, April 2025) ==

Current emissions: ~29,400 tonnes CO2e/year (3.4 t CO2e per person)
Net zero target: 2040 (achievable; 2045 contingency)
Carbon budget remaining: 203 kt CO2e from 2023 to 2100
Buildings: 3,249 properties heated by fossil fuels (mainly gas); 151 already all-electric
Vehicles: 3,700+ registered; >90% petrol/diesel

Key interventions modelled (grants MUST match these real, planned activities):
  • 100,000 trees planted 2026–2030 (25,000/year); Miyawaki forests in built areas
  • Rewilding 100 hectares of parish/agricultural land 2030–2040
  • 10,000 m² of hedgerow planting 2026–2027
  • 1,000 m² extensive green roofs 2028–2032
  • Electrified heating in 3,075 homes 2025–2040 (205 heat pumps/year)
  • Roof insulation for 1,000 properties 2026–2030 (250/year)
  • Wall insulation for 200 properties 2028–2030
  • Domestic solar panels on 1,700 homes 2025–2030 (340/year)
  • Battery storage for 1,700 homes 2025–2030
  • 3,674 battery electric vehicles by 2040 (245/year)
  • 30 fast + 10 rapid EV chargers 2025–2028
  • E-bike rental scheme: 200 shared bikes 2025–2026
  • 2,000 m of new bike lanes 2026–2027
  • Community solar farm / community wind turbine (feasibility 2026–2028)
  • 3 community composting sites 2025–2027
  • Local beekeeping: 10 hives 2026–2028
  • Increased allotments: 1,000 m² 2025–2027
  • Biochar application on 100 km² agricultural land 2030–2035
  • Reduced tillage on 100 ha 2029–2033

== TRACK RECORD — COMPLETED PROJECTS ==

  • Community Garden: Disused skatepark transformed using National Lottery + Tesco funding;
    opened May 2023 at King Charles' Coronation event; weekly school visits; twice-weekly
    work sessions. DEMONSTRATES: ability to deliver NLCF-funded projects.
  • Wildflower rewilding: Wildflower areas created on Parish Council land; formal beds
    and planters maintained for pollinators; tree planting at Village Hall field and
    Memorial Playing Field in last 18 months.
  • LED street light replacement: Old sodium lamps replaced with LEDs across village
    (Phase 1 complete Feb 2024, Phase 2 imminent).
  • Village Hall solar panels: Installation imminent (Nov 2023 → Apr 2025 project).
  • E-mobility: Beryl bikes introduced to village with 3 docking areas.
  • Electric bus: First Bus EV route from Wymondham to Norwich via Hethersett (2024).
  • Formal net zero plan: Opergy Net Zero Pathway (Sept 2024, funded by Norfolk
    Investment Framework) + Happy Healthy Hethersett Action Plan (April 2025).
  • UEA partnership: Active research collaboration with UKERC Public Engagement
    Observatory on community climate engagement mapping.
  • Governance: Parish Council adopted Green Charter & Biodiversity Action Plan (Oct 2022).

== PROJECT AREAS (GRANT-FUNDABLE ACTIVITIES) ==

  • Tree planting on village greens, verges, Memorial Playing Field, Village Hall field
  • Miyawaki micro-forests on brownfield/urban land
  • Hedgerow planting and habitat connectivity across parish
  • Rewilding patches of parish-owned land with wildflowers, native species
  • Community orchard and edible hedges on publicly-owned land
  • Home insulation advice / community referral schemes (ECO4, GBIS targeting)
  • Heat pump community demonstrations: "Visit a Heat Pump" open days
  • Heat Geek training for local heating engineers / workforce upskilling
  • Solar panel and battery storage community showcases
  • Biodiversity surveys: Big Garden Bird Watch, species transects, school projects
  • Community education events: People Planet Pint, open days, school STEM visits
  • EV charging point installation on parish car parks and public land
  • Cross-pavement EV charging channels for residents without driveways
  • E-bike and e-scooter rental scheme (partner: Beryl or similar)
  • Community composting and community food growing (allotments)
  • Carbon footprint monitoring and community survey (with UEA)
  • Net zero policy development (building standards, biodiversity policy)
  • Engagement with local farmers on Countryside Stewardship, SFI, biochar
  • Community solar farm / community wind turbine feasibility and development
  • STEM/Climate Ambassador school visits and youth engagement
  • Active travel: new bike lanes, pedestrianisation, safe routes to school

== LOCAL CONTEXT — KEY FUNDING TRIGGERS ==

  HOUSING DEVELOPMENTS:
  • Taylor Wimpey active development in Hethersett — S106 + CIL obligations
  • Persimmon active development in Hethersett — S106 + CIL obligations
  • South Norfolk CIL: parish council receives 15–25% neighbourhood portion

  ROAD SCHEMES:
  • A47 dualling / Norwich Western Link / NDR corridor near Hethersett
  • National Highways and NCC hold environmental mitigation and community funds

  OFFSHORE WIND (35-mile benefit zone — all relevant):
  • Ørsted Hornsea 3 & 4 (off Norfolk/Lincolnshire)
  • Vattenfall Norfolk Vanguard & Norfolk Boreas
  • ScottishPower East Anglia ONE / TWO / Hub
  • Equinor Dudgeon & Sheringham Shoal
  • Ørsted Race Bank
  • RWE Triton Knoll

  ACADEMIC PARTNER:
  • UEA / UKERC partnership opens access to UKRI, Research England, Horizon grants
    for community-academic research on public engagement with net zero

== END APPLICANT PROFILE ==
"""

# ---------------------------------------------------------------------------
# Phase definitions — each has a name, label, focus, and detailed prompt
# ---------------------------------------------------------------------------

PHASES = [
    {
        "name": "public_lottery",
        "label": "Public Sector & Lottery Funding",
        "focus": """
You are an expert UK grant fundraiser researching public sector and lottery grants
for HEAT/HEAG, a community environmental group in Hethersett, Norfolk.

NATIONAL LOTTERY PROGRAMMES:
- Awards for All England (NLCF) -- 300-10,000, rolling, very accessible for community groups
- NLCF standard grants -- 10,001-500,000
- Climate Action Fund / successor programmes
- People and Nature Fund
- Community Led Place programme
- Reaching Communities England
- National Lottery Heritage Fund -- Landscape Connections, Grants for Heritage
- People's Postcode Lottery -- Dream Fund, Green Communities
- Big Lottery Fund legacy programmes still disbursing

UK GOVERNMENT -- NATURE, FORESTRY & ENVIRONMENT:
- England Woodland Creation Offer (EWCO) -- Forestry Commission, can community groups apply?
- Urban Tree Challenge Fund -- trees in towns
- Woodland Creation Planning Grant and Accelerator Fund
- Nature for Climate Fund -- community strand
- Biodiversity Net Gain (BNG) community fund streams (post-2024 legislation)
- Local Nature Recovery Strategies -- Norfolk LNRS associated funding pots?
- Natural England facilitation funds and Access to Nature Fund
- Environment Agency community flood action grants
- DEFRA community grants via local authorities
- Higher Tier Countryside Stewardship -- parish council eligibility?
- Landscape Recovery Scheme -- community-led strand
- Countryside Stewardship hedgerow/agroforestry/biochar -- community group farm partnerships
- SFI (Sustainable Farming Incentive) community partnerships with local Hethersett farmers
- Green social prescribing pilot -- nature-based health interventions
- Miyawaki forest grants -- dense urban micro-forests

UK SHARED PROSPERITY & RURAL:
- UK Shared Prosperity Fund (UKSPF) environmental/community strands via New Anglia LEP
- Rural England Prosperity Fund (REPF) -- South Norfolk allocation
- LEADER Local Action Group for South Norfolk -- current programme, eligible projects

For each programme: is it currently open? Can a parish council committee or community
group apply? Min/max amounts? Deadlines? Direct application URL?
""",
    },
    {
        "name": "energy_climate",
        "label": "Energy, Climate & Net Zero",
        "focus": """
You are an expert in UK energy and climate funding researching grants for HEAT/HEAG
in Hethersett, Norfolk -- a group planning a community solar farm, community wind turbine,
30+ EV charge points, 200 e-bikes, heat pump promotion, and insulation schemes.

COMMUNITY ENERGY & RENEWABLES:
- Rural Community Energy Fund (RCEF) -- up to 40,000 feasibility for community solar/wind
- Community Energy Fund (DESNZ) -- current rounds, feasibility and development grants
- Community Renewable Energy (CRE) programme -- any active iteration
- Innovate UK Net Zero Living and Smart Local Energy Systems -- local demonstration projects
- UKRI / Research England engaged research fund -- Hethersett has a live UEA partnership
- UK Energy Research Centre (UKERC) community partner funding
- Horizon Europe / Innovate UK community net zero project funding

ENERGY EFFICIENCY & HEAT:
- Great British Insulation Scheme (GBIS) -- community coordinator/facilitator grants
- ECO4 Flex -- community group targeting mechanism grants for identifying households
- Warm Homes Plan / Local Grant -- community group role, current status
- Boiler Upgrade Scheme -- community facilitation grants for promoting uptake
- Heat Network Transformation Programme -- community heat networks
- Heat Pump Ready programme -- community facilitation grants
- Salix Finance -- parish council energy efficiency loans/grants
- Low Carbon Workspaces (East of England) -- if parish office qualifies
- Heat Geek / heat pump installer training grants -- workforce upskilling fund
- Retrofit Works / PAS2035 community facilitation grants

ELECTRIC VEHICLES & ACTIVE TRAVEL:
- LEVI Fund (Local Electric Vehicle Infrastructure) -- parish council car park eligibility
- On-street Residential Charge Point Scheme (ORCS) -- parish council car parks eligible?
- Active Travel England Capability & Ambition Fund -- e-bike, cycling, rural communities
- Cycling and Walking Investment Strategy (CWIS) community grants
- E-bike community scheme grants -- any programme for community e-bike fleets

CLIMATE ACTION SPECIALISTS:
- Ashden Awards and grants -- community climate action
- Climate Emergency Fund (CEF) -- community climate mobilisation
- Transition Network / Transition Towns grants
- Carbon Literacy Project -- community engagement funding
- WRAP -- community waste/circular economy grants
- Hubbub Foundation -- community environmental behaviour change
- Climate Outreach -- community communication grants
- Friends of the Earth Local Groups grants
- 10:10 / Possible community action grants
- Great Big Green Week / Climate Coalition community action grants

For each: current status, who can apply, amounts, deadlines, application URL.
""",
    },
    {
        "name": "nature_wildlife",
        "label": "Nature, Biodiversity & Green Spaces",
        "focus": """
You are an expert in UK wildlife and nature charity funding researching grants for
HEAT/HEAG in Hethersett, Norfolk -- a group planning 100,000 trees by 2030, rewilding,
community orchards, Miyawaki micro-forests, hedgerows, biochar projects, and bee hives.

WILDLIFE & NATURE CHARITIES:
- Norfolk Wildlife Trust -- local grants, Living Landscapes, volunteer support
- RSPB -- community conservation grants, Giving Nature a Home, Local Group funding
- Wildlife Trusts national grants (separate from Norfolk WT)
- Woodland Trust -- MOREwoods (free trees for communities), MOREhedges
- Trees for Cities -- urban tree planting grants for community groups
- The Tree Council -- community tree growing and care grants
- Buglife -- B-Lines community grants, pollinator corridor funding
- Butterfly Conservation -- community habitat grants
- Plantlife -- wild plants/meadows community grants
- Froglife -- amphibian/reptile habitat grants
- People's Trust for Endangered Species (PTES)
- British Trust for Ornithology (BTO) -- survey funding
- Broads Authority -- any grants extending to South Norfolk?
- Wild Anglia (Norfolk and Suffolk nature partnership) -- community grants?
- Rivers Trust -- community catchment/river grants, Norfolk rivers
- Wildfowl & Wetlands Trust (WWT) -- community wetland grants
- Rewilding Britain -- community rewilding support grants
- Heal Rewilding -- land/community grants
- Saving Nature -- species recovery community grants
- Biffa Award -- biodiversity, community, ecology (via ENTRUST / landfill tax)
- Landfill Communities Fund / ENTRUST -- projects near landfill sites
- Environment Agency Fisheries Improvement Programme

SPECIFIC PROJECT GRANTS (match the Hethersett action plan):
- Community composting infrastructure grants -- 3 composting sites planned
- Community beekeeping grants -- 10 hives planned 2026-2028
- Community orchard and edible hedge grants -- edible hedges on public land
- Biochar in agriculture grants -- search "biochar agricultural grant UK community 2025"
- Community allotment and food growing grants -- 1,000m2 allotments planned
- School / youth nature engagement grants -- outdoor learning, STEM visits
- Citizen science / community monitoring grants -- UEA engagement observatory

For each: currently open? Can a village community group apply? Maximum award?
Any Norfolk/East Anglia geographic priority? Direct application URL?
""",
    },
    {
        "name": "community_norfolk",
        "label": "Community, Local & Norfolk Funders",
        "focus": """
You are an expert in Norfolk and community grant funding researching local and
hyperlocal grants for HEAT/HEAG in Hethersett, South Norfolk.

COMMUNITY DEVELOPMENT ORGANISATIONS:
- Groundwork UK / Groundwork East -- local community green space, environment programmes
- The Conservation Volunteers (TCV) -- community green space grants
- Keep Britain Tidy -- Eco-Schools, green flag communities
- Community First Norfolk -- local Norfolk grants for community groups
- Voluntary Norfolk -- capacity-building and environmental grants
- Community Action Norfolk -- rural community group grants
- Norfolk Community Foundation -- current open funds (environment, place, wellbeing)
- Fields in Trust -- green space protection and improvement grants
- Locality -- community asset transfer, community power fund
- Power to Change -- community business grants (if HEAG incorporates as community business)

NORFOLK & REGIONAL FUNDERS:
- Norfolk County Council -- environmental grants, climate change fund, parish support
- South Norfolk and Breckland Council -- environmental improvements, community grants
- New Anglia LEP -- UKSPF environmental/community strands
- Rural England Prosperity Fund (REPF) -- South Norfolk allocation
- LEADER Local Action Group for South Norfolk -- current programme
- Norfolk Rural Community Council (NRCC) -- grants, loan funds, support
- Anglian Water -- Caring for our Catchments community grants
- Active Norfolk -- physical activity/active travel grants
- Greater Norwich Growth Board -- does Hethersett qualify?

OFFSHORE WIND COMMUNITY BENEFIT FUNDS -- HIGH PRIORITY:
Hethersett is within the benefit zone of multiple offshore wind projects off Norfolk.
Research ALL of these -- geographic eligibility is critical:
- Orsted Hornsea Three (H3) Community Benefit Fund -- annual pot, geographic eligibility, how to apply
- Orsted Hornsea Four (H4) -- any community fund announced?
- Norfolk Vanguard Offshore Wind Farm (Vattenfall) -- fund details, Hethersett/South Norfolk eligible?
- Norfolk Boreas Offshore Wind Farm (Vattenfall) -- fund details, eligibility
- Dudgeon Offshore Wind Farm (Equinor) -- community fund, how to apply
- Sheringham Shoal (Equinor/Scatec) -- community benefit fund
- Race Bank (Orsted) -- community fund details
- East Anglia ONE/TWO (ScottishPower Renewables) -- Norfolk community fund eligibility
- Triton Knoll (RWE) -- check South Norfolk eligibility
For each: fund size per year, geographic eligibility area (miles from landfall or grid connection),
grant size range, application process, current open/closed status.

ROAD SCHEME & DEVELOPER COMMUNITY FUNDS:
- National Highways A47 Community Fund -- is Hethersett within eligible area?
- National Highways Environmental Mitigation Fund -- tree/biodiversity near road corridors
- Norwich Western Link community mitigation fund

DEVELOPER CONTRIBUTIONS -- HETHERSETT SPECIFIC:
- Section 106 agreements: Taylor Wimpey and Persimmon are actively building in Hethersett.
  What environmental/community obligations exist? How does HEAT/HEAG access this money?
- South Norfolk CIL (Community Infrastructure Levy) -- neighbourhood portion (15-25%)
  goes to the parish council. How does HEAT/HEAG bid for it?
- Taylor Wimpey Community Fund -- any Hethersett or Norfolk site-specific allocation
- Persimmon Communities Fund -- Hethersett or South Norfolk site-specific fund
- Biodiversity Net Gain (BNG) -- can Hethersett parish create BNG habitat units from
  Taylor Wimpey/Persimmon developments and access associated habitat bank funding?
""",
    },
    {
        "name": "trusts_corporate",
        "label": "Major Trusts & Corporate Grants",
        "focus": """
You are an expert UK fundraiser researching large charitable trusts and corporate
grant programmes for HEAT/HEAG in Hethersett -- a community environmental group
with a parish council mandate and a live UEA academic partnership.

MAJOR INDEPENDENT TRUSTS:
- Esmee Fairbairn Foundation -- environment and natural world strand (strong Norfolk interest)
- Garfield Weston Foundation -- community environment projects
- Tudor Trust -- smaller community grants
- Dulverton Trust -- rural environment, nature conservation (excellent match for Hethersett)
- Ernest Cook Trust -- rural environment, education in nature
- Waterloo Foundation -- climate and environment
- John Ellerman Foundation -- natural environment strand
- Calouste Gulbenkian Foundation UK -- arts/environment/community
- Paul Hamlyn Foundation -- community/youth/environment
- Wates Family Enterprise Trust -- community/environment
- Zurich Insurance Foundation -- climate resilience community grants
- Aviva Foundation -- environment/community
- Henry Smith Charity -- community grants
- Rank Foundation -- youth/community/environment
- Nationwide Foundation -- energy poverty/environment overlap
- Joseph Rowntree Foundation -- climate justice, community power

SUPERMARKETS & RETAIL:
- Tesco Community Grants (Bags of Help via Groundwork) -- current round open?
- Asda Foundation -- community grants, environment strand
- Sainsbury's Community Investment -- local grant schemes
- Co-op Foundation -- community and climate grants
- Waitrose & Partners Foundation -- local community/environment
- Morrisons Foundation -- community grants

ENERGY COMPANIES & UTILITIES:
- E.ON Next Community Fund -- current round status
- OVO Foundation / OVO Energy community grants
- Octopus Energy community grants (Green Octopus?)
- British Gas / Centrica community grants
- EDF Energy community fund
- SSE / SSEN Community Fund
- Scottish Power community grants
- National Grid community fund
- Anglian Water conservation grants
- Good Energy community grants

OFFSHORE WIND CORPORATE (confirm current rounds):
- Orsted UK Community Fund -- Hornsea series Norfolk community fund
- Vattenfall Norfolk Vanguard / Norfolk Boreas community fund
- Triton Knoll (RWE) community fund

TECH & BANKING:
- Amazon Sustainability community grants
- Google.org -- climate/environment community grants
- Lloyds Bank Foundation -- community grants
- NatWest Group Foundation -- environment/community
- HSBC UK community grants

For each: is the programme currently open? Grant sizes? Norfolk or rural preference?
Can volunteer-led community groups with parish council backing apply?
""",
    },
    {
        "name": "verify_enrich",
        "label": "Verify & Deepen the Most Promising Leads",
        "focus": """
You are an expert UK grant fundraiser performing a verification pass on grants
found for HEAT/HEAG in Hethersett, Norfolk.

Your task: re-check the most important grant programmes and confirm:
1. Is the programme definitively still open as of 2025?
2. What is the EXACT maximum and minimum grant amount?
3. Is there a confirmed deadline or is it rolling?
4. What is the direct URL to the application page (not just the homepage)?
5. Are parish councils or community groups explicitly mentioned as eligible?
6. Has it changed name or moved to a new funder?

PRIORITY RE-CHECKS:
- Awards for All England (NLCF)
- England Woodland Creation Offer (Forestry Commission)
- Rural Community Energy Fund (RCEF) -- Phase 3 / current successor
- Community Energy Fund (DESNZ) -- latest round status
- Norfolk Community Foundation -- current open funds
- Groundwork East community grants
- UK Shared Prosperity Fund / REPF via South Norfolk
- LEADER South Norfolk -- current status
- ECO4 Flex community targeting
- E.ON Next Community Fund -- current round
- Orsted Hornsea community benefit fund -- confirm Hethersett geographic eligibility zone
- Vattenfall Norfolk Vanguard fund -- confirm South Norfolk eligibility
- National Highways A47 community fund -- does Hethersett qualify?
- South Norfolk CIL neighbourhood portion -- how does HEAT/HEAG access it?
- Taylor Wimpey Hethersett community fund -- confirm site-specific programme
- Active Travel England grants for parish council e-bike / active travel schemes
- LEVI Fund / ORCS -- EV charger grants for parish council car parks
- Biffa Award -- current round open?
- Tesco Community Grants (Bags of Help) -- current round?

Also search for any new government net zero or community environment grants
announced in 2025 that were not in earlier results.

Return a final comprehensive JSON list of all verified grants.
""",
    },
]

# ---------------------------------------------------------------------------
# Core agentic loop for a single phase
# ---------------------------------------------------------------------------

def _run_phase(
    phase: dict,
    discovered_funders: list[str],
    progress: ProgressCallback,
    known_db_funders: list[str] | None = None,
) -> list[dict]:
    """
    Run one research phase using Sonnet. Returns a list of raw grant dicts.
    Caps at MAX_SEARCHES_PER_PHASE web searches then nudges the model to compile.
    """
    phase_name = phase["name"]
    phase_label = phase["label"]
    progress(f"Starting phase: {phase_label}", "phase")

    funder_context = ""
    if known_db_funders:
        funder_context += (
            "\n\nFunders ALREADY IN THE DATABASE — SKIP THESE ENTIRELY. "
            "Do not research, verify, or include them in your output:\n"
            + "\n".join(f"  • {f}" for f in known_db_funders[:80])
        )
    if discovered_funders:
        funder_context += (
            "\n\nFunders found in earlier phases this run (do not duplicate):\n"
            + "\n".join(f"  • {f}" for f in discovered_funders[:40])
        )

    system = f"""You are a tenacious, expert UK grant fundraiser with 20 years of experience
securing funding for community environmental groups in rural England. You know the UK grant
landscape intimately — every major funder, every recurring programme, every nuance of
eligibility for parish councils and community groups.

{APPLICANT_PROFILE}

Current research phase: {phase_label}

{phase["focus"]}
{funder_context}

MANDATORY RULES — NO EXCEPTIONS:
1. You MUST use web_search for every programme before including it. Do NOT rely on
   training knowledge. Grant deadlines, amounts and eligibility change constantly.
2. Search BEFORE you write any JSON. Your first action must be a web_search call.
3. You have a budget of {MAX_SEARCHES_PER_PHASE} web searches for this phase.
   Prioritise the programmes most likely to be open and relevant — do not waste
   searches on programmes you already know are closed or ineligible.
4. Follow leads: if a result mentions an open funder you haven't searched, search them.
5. Every grant in your final JSON must have been verified by a live web_search call.
   If you cannot find live confirmation, mark confidence "low" and note it.
6. Only output the final ```json ... ``` array once you have used your search budget.
   Do not output JSON mid-way through — search first, compile at the end.

Output format — each grant must have:
  title            (string — the specific programme name, NOT just the funder name)
  funder           (string)
  description      (string — 2–4 sentences: what it funds, typical award size, why it
                    suits HEAT/HEAG specifically. Be concrete, not generic.)
  url              (string or null — MUST be the direct URL to the specific grant or
                    programme page, e.g. ".../funding/programmes/xxxxx". A homepage
                    like "https://www.tnlcommunityfund.org.uk" is NOT acceptable —
                    use null if you cannot find the specific page URL)
  deadline         (string — exact date, "rolling", "annual — check website", or "unknown")
  max_amount       (integer GBP or null)
  min_amount       (integer GBP or null)
  focus_areas      (array of strings from: tree planting, rewilding, solar, energy,
                    insulation, heat pumps, biodiversity, education, electric vehicles,
                    net zero, community, biodiversity survey, wildflower, hedgerow,
                    water, climate action, circular economy)
  eligibility_notes (string — specific notes on whether parish councils / community
                     groups can apply; flag any uncertainty)
  confidence       ("high", "medium", or "low" — how confident are you this is current/open)
"""

    prompt = f"""Research {phase_label} for HEAT and HEAG in Hethersett.

Start searching NOW — your first action must be a web_search call. Do not write any text before searching.

For every programme in your brief:
1. Search for it by name to get current status, amounts, deadline and application URL
2. Only include it in your output once you have live search results confirming its status

After searching all programmes, output a single ```json ... ``` array.
"""

    messages = [{"role": "user", "content": prompt}]
    searches_this_phase = 0
    nudge_sent = False

    cached_system = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

    for iteration in range(15):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            system=cached_system,
            tools=[{"type": "web_search_20260209", "name": "web_search"}],
            messages=messages,
        )

        # Count searches in this response
        new_searches = sum(
            1 for block in response.content
            if hasattr(block, "type") and block.type == "tool_use"
        )
        searches_this_phase += new_searches
        if new_searches > 0:
            progress(
                f"  {phase_label}: {searches_this_phase}/{MAX_SEARCHES_PER_PHASE} searches…",
                "info",
            )

        if response.stop_reason == "end_turn":
            text = "".join(
                block.text
                for block in response.content
                if hasattr(block, "text") and block.text
            )
            grants = _parse_grants_json(text)
            progress(
                f"  {phase_label}: complete — {len(grants)} grants found after "
                f"{searches_this_phase} searches",
                "found",
            )
            return grants

        # Append assistant turn and continue
        messages.append({"role": "assistant", "content": response.content})

        # Always acknowledge outstanding tool_use blocks first (API requirement)
        tool_results = [
            {"type": "tool_result", "tool_use_id": block.id, "content": ""}
            for block in response.content
            if hasattr(block, "type") and block.type == "tool_use"
        ]
        if searches_this_phase >= MAX_SEARCHES_PER_PHASE and tool_results and not nudge_sent:
            nudge_sent = True
            messages.append({
                "role": "user",
                "content": tool_results + [{
                    "type": "text",
                    "text": (
                        "You've used your search budget. Please now compile everything "
                        "you've found into the final ```json ... ``` array and stop."
                    ),
                }],
            })
        elif tool_results:
            messages.append({"role": "user", "content": tool_results})

    progress(f"  {phase_label}: hit iteration limit — extracting partial results", "info")
    # Extract whatever text was in the last response
    last_text = "".join(
        block.text
        for block in messages[-1].get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    ) if messages else ""
    return _parse_grants_json(last_text)


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------

def _parse_grants_json(text: str) -> list[dict]:
    """Extract a JSON array from model output text."""
    if not text:
        return []

    # Try ```json ... ``` block first
    match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if match:
        raw = match.group(1)
    else:
        # Fall back to first [...] array
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            return []
        raw = match.group(0)

    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        # Try to salvage a truncated array
        try:
            # Find the last complete object
            truncated = raw.rstrip().rstrip(",")
            if not truncated.endswith("]"):
                truncated += "]"
            data = json.loads(truncated)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []


# ---------------------------------------------------------------------------
# Master orchestrator
# ---------------------------------------------------------------------------

def research_grants_deep(
    focus_areas: list[str],
    progress: ProgressCallback,
    phases_to_run: list[str] | None = None,
    known_funders: list[str] | None = None,
) -> list[dict]:
    """
    Run all research phases and return the combined de-duplicated grant list.

    phases_to_run: if provided, only run these phase names (useful for resuming).
    known_funders: funders already in the database — the agent will skip them.
    """
    # verify_enrich always runs last; other phases filtered by user selection
    active_phases = [
        p for p in PHASES
        if p["name"] == "verify_enrich"
        or phases_to_run is None
        or p["name"] in phases_to_run
    ]

    all_grants: list[dict] = []
    discovered_funders: list[str] = []
    known_db_funders: list[str] = list(known_funders or [])

    if known_db_funders:
        progress(
            f"Skipping {len(known_db_funders)} funders already in the database — "
            "the agent will focus on finding new sources only.",
            "info",
        )

    progress(
        f"Beginning deep research across {len(active_phases)} specialist phases. "
        "This will take a while — that's intentional. Thoroughness is the goal.",
        "phase",
    )

    for i, phase in enumerate(active_phases, 1):
        progress(
            f"[{i}/{len(active_phases)}] {phase['label']}",
            "phase",
        )
        try:
            phase_grants = _run_phase(
                phase, discovered_funders, progress, known_db_funders=known_db_funders
            )
        except Exception as e:
            progress(f"  Phase {phase['name']} error: {e}", "info")
            phase_grants = []

        # Accumulate funders for cross-phase context
        for g in phase_grants:
            funder = g.get("funder", "")
            if funder and funder not in discovered_funders:
                discovered_funders.append(funder)

        # Merge — deduplicate by (title, funder)
        existing_keys = {
            (g.get("title", "").lower(), g.get("funder", "").lower())
            for g in all_grants
        }
        new_count = 0
        for g in phase_grants:
            key = (g.get("title", "").lower(), g.get("funder", "").lower())
            if key not in existing_keys:
                all_grants.append(g)
                existing_keys.add(key)
                new_count += 1

        progress(
            f"  Phase complete: +{new_count} new grants (total so far: {len(all_grants)})",
            "found",
        )

    progress(
        f"Research complete. {len(all_grants)} grants found across all phases. Running verification…",
        "phase",
    )
    return _verify_grants(all_grants, progress)


# ---------------------------------------------------------------------------
# Single-pass grant verifier — independent grader, runs after all phases
# ---------------------------------------------------------------------------

def _verify_grants(grants: list[dict], progress: ProgressCallback) -> list[dict]:
    """
    Independent grader pass: reviews the combined grant list and removes entries
    that are clearly ineligible, confirmed closed, or have no real URL.
    Returns REMOVE decisions only (small output) then filters the original list.
    Falls back to the unverified list if parsing fails.
    """
    if not grants:
        return grants

    progress(f"Verifier: reviewing {len(grants)} grants for eligibility and status…", "phase")

    # Summarise each grant minimally to keep token count low
    summaries = []
    for i, g in enumerate(grants):
        summaries.append(
            f"{i}: title={g.get('title','?')} | funder={g.get('funder','?')} | "
            f"url={g.get('url','none')} | eligibility={g.get('eligibility_notes','?')} | "
            f"confidence={g.get('confidence','?')} | deadline={g.get('deadline','?')}"
        )
    grants_summary = "\n".join(summaries)

    system = f"""You are an independent grant eligibility verifier for HEAT/HEAG in Hethersett, Norfolk.

HEAT is a committee of Hethersett Parish Council (a public body).
HEAG is a volunteer community group backed by the parish council.
Neither is a registered charity. Neither is a farmer, housing association, or NHS body.

Your task: identify which grants from the list below should be REMOVED.

REMOVE a grant if ANY of the following are true:
  - Eligibility explicitly excludes parish councils and community groups
    (e.g. "registered charities only", "farmers only", "local authorities with min
    population >50,000", "housing associations only", "NHS bodies only")
  - The grant is confirmed closed since before 2024 with no active successor
  - The URL is blank or is a generic company homepage (e.g. "https://www.tesco.com"
    with no path — not a grant page)

KEEP a grant if:
  - Eligibility includes or could include community groups, parish councils,
    or voluntary organisations — even if competitive
  - The grant might still be open (uncertain is fine — keep it)
  - Confidence is "low" but the programme is plausibly current

You may make up to 6 web searches to spot-check specific grants you are unsure about.
Focus searches on low-confidence grants or grants with homepage-only URLs.

Return ONLY a JSON array of grants to REMOVE, in this format:
```json
[{{"index": 0, "title": "...", "funder": "...", "reason": "..."}}]
```
If nothing should be removed, return: ```json\n[]\n```
Do not return any other text."""

    prompt = f"""Review these {len(grants)} grants and return the list of indices to remove:\n\n{grants_summary}"""

    messages = [{"role": "user", "content": prompt}]
    total_searches = 0
    nudge_sent = False

    for iteration in range(10):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            system=system,
            tools=[{"type": "web_search_20260209", "name": "web_search"}],
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            text = "".join(
                block.text for block in response.content
                if hasattr(block, "text") and block.text
            )
            try:
                m = re.search(r"```json\s*([\s\S]*?)```", text)
                removals = json.loads(m.group(1).strip()) if m else []
            except Exception:
                removals = []

            remove_indices = {r.get("index") for r in removals if isinstance(r, dict)}
            verified = [g for i, g in enumerate(grants) if i not in remove_indices]

            progress(
                f"Verifier: {len(verified)} grants passed, {len(removals)} removed",
                "found",
            )
            return verified if verified else grants

        messages.append({"role": "assistant", "content": response.content})
        tool_results = [
            {"type": "tool_result", "tool_use_id": block.id, "content": ""}
            for block in response.content
            if hasattr(block, "type") and block.type == "tool_use"
        ]
        total_searches += len(tool_results)
        if tool_results:
            if total_searches >= 6 and not nudge_sent:
                nudge_sent = True
                messages.append({
                    "role": "user",
                    "content": tool_results + [{
                        "type": "text",
                        "text": "You've used your search budget. Please now return the removal list JSON.",
                    }],
                })
            else:
                messages.append({"role": "user", "content": tool_results})

    progress("Verifier: hit iteration limit — returning unverified list", "info")
    return grants


# ---------------------------------------------------------------------------
# Targeted search — single focused question, no monthly limit
# ---------------------------------------------------------------------------

def research_targeted(
    question: str,
    known_funders: list[str],
    progress: ProgressCallback,
) -> list[dict]:
    """
    Run a single focused search for a specific question.
    Much cheaper than the full 10-phase search — 12 iterations maximum.
    Skips funders already in the database.
    """
    progress(f"Targeted search: {question}", "phase")

    funder_context = ""
    if known_funders:
        funder_context = (
            "\n\nFunders ALREADY IN THE DATABASE — do NOT re-research these. "
            "Skip any programme you recognise from this list:\n"
            + "\n".join(f"  • {f}" for f in known_funders[:80])
        )

    system = f"""You are an expert UK grant fundraiser researching a specific funding
question for HEAT and HEAG in Hethersett, Norfolk.

{APPLICANT_PROFILE}
{funder_context}

RULES:
1. Use web_search for every programme before including it.
2. Focus ONLY on the specific question asked — do not run a broad sweep.
3. Every grant in your final JSON must be verified by a live web_search call.
4. Do NOT include funders from the already-in-database list above.
5. Output a single ```json ... ``` array when done.

Output format — each grant must have:
  title            (string — specific programme name, NOT just the funder name)
  funder           (string)
  description      (string — 2–4 sentences: what it funds, typical award size, why it
                    suits HEAT/HEAG specifically)
  url              (string or null — MUST be the direct URL to the specific grant page,
                    not a homepage. Use null if you cannot find the specific page URL)
  deadline, max_amount, min_amount, focus_areas, eligibility_notes, confidence
"""

    prompt = (
        f"Specific research question: {question}\n\n"
        "Search for grants, funds or programmes that match this specific question. "
        "Start with a web_search NOW. "
        "Output the final ```json ... ``` array when done. "
        "Keep searches focused — this is a targeted lookup, not a broad sweep."
    )

    messages = [{"role": "user", "content": prompt}]
    searches_done = 0
    cached_system = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

    for iteration in range(12):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            system=cached_system,
            tools=[{"type": "web_search_20260209", "name": "web_search"}],
            messages=messages,
        )

        new_searches = sum(
            1 for block in response.content
            if hasattr(block, "type") and block.type == "tool_use"
        )
        searches_done += new_searches
        if new_searches > 0:
            progress(f"  Targeted search: {searches_done} searches completed…", "info")

        if response.stop_reason == "end_turn":
            text = "".join(
                block.text for block in response.content
                if hasattr(block, "text") and block.text
            )
            grants = _parse_grants_json(text)
            progress(
                f"  Targeted search complete — {len(grants)} new grants found "
                f"after {searches_done} searches",
                "found",
            )
            return grants

        messages.append({"role": "assistant", "content": response.content})

        tool_results = [
            {"type": "tool_result", "tool_use_id": block.id, "content": ""}
            for block in response.content
            if hasattr(block, "type") and block.type == "tool_use"
        ]
        if iteration == 9 and response.stop_reason == "tool_use" and tool_results:
            messages.append({
                "role": "user",
                "content": tool_results + [{
                    "type": "text",
                    "text": (
                        "Good research. Please compile your findings into the "
                        "final ```json ... ``` array now."
                    ),
                }],
            })
        elif tool_results:
            messages.append({"role": "user", "content": tool_results})

    progress("  Targeted search: hit iteration limit — extracting partial results", "info")
    last_text = "".join(
        block.text for block in messages[-1].get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    ) if messages else ""
    return _parse_grants_json(last_text)


# ---------------------------------------------------------------------------
# Application chat helper — unchanged in function
# ---------------------------------------------------------------------------

APPLY_HELPER_SYSTEM = f"""You are an experienced, encouraging UK grant application writer
helping volunteers at HEAT and HEAG in Hethersett, Norfolk complete grant applications.

{APPLICANT_PROFILE}

Your approach:
1. Ask targeted questions to understand the project being funded
2. Explain what this specific funder cares about most (their priorities, language, values)
3. Help draft compelling, jargon-free answers the volunteers can copy and refine
4. One or two questions at a time — never overwhelm
5. Periodically summarise what you have so far
6. Flag the sections applicants typically struggle with
7. Point out where the applicant's track record with the parish council is an advantage
8. Be warm, practical, and specific — not vague cheerleading

When drafting text, write it as if you were the applicant — first person, community voice.
"""


def chat_with_assistant(
    grant: dict,
    conversation_history: list[dict],
    user_message: str,
) -> str:
    """Continue a grant application help conversation."""
    grant_context = (
        f"Grant: {grant.get('title', 'Unknown')} from {grant.get('funder', 'Unknown')}\n"
        f"Description: {grant.get('description', '')}\n"
        f"Max award: £{grant.get('max_amount', 'unknown')}\n"
        f"Deadline: {grant.get('deadline', 'unknown')}\n"
        f"Eligibility notes: {grant.get('eligibility_notes', '')}\n"
        f"URL: {grant.get('url', 'not known')}"
    )

    messages = list(conversation_history)
    if not messages:
        messages.append({
            "role": "user",
            "content": f"{grant_context}\n\nUser: {user_message}",
        })
    else:
        messages.append({"role": "user", "content": user_message})

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=3000,
        system=APPLY_HELPER_SYSTEM,
        messages=messages,
    )

    return "".join(
        block.text for block in response.content if hasattr(block, "text") and block.text
    )
