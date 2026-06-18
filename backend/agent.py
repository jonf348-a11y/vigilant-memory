"""
Deep grant research agent for HEAT and HEAG, Hethersett, Norfolk.

Runs 10 specialist research phases covering the full UK environmental
grant landscape, making up to 60 web searches per phase.

Phase order:
  1  national_lottery     – NLCF programmes
  2  government_nature    – DEFRA, Forestry Commission, Natural England
  3  energy_netzero       – DESNZ, ECO4, GBIS, community energy
  4  wildlife_charities   – Wildlife Trusts, RSPB, Woodland Trust, etc.
  5  community_charities  – Groundwork, TCV, Keep Britain Tidy
  6  norfolk_regional     – NCC, South Norfolk, NCF, LEADER, UKSPF
  7  major_trusts         – Esmée Fairbairn, Garfield Weston, Dulverton, etc.
  8  corporate_csr        – Tesco, energy companies, housebuilders
  9  climate_specialist   – Ashden, CEF, Transition Network, etc.
 10  verify_enrich        – Verify and deepen the best leads found
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

# ---------------------------------------------------------------------------
# Shared context injected into every phase
# ---------------------------------------------------------------------------

APPLICANT_PROFILE = """
== APPLICANT PROFILE ==

Organisation 1: HEAT — Hethersett Environmental Action Team
  Type: Self-funded committee of Hethersett Parish Council
  Legal status: Parish council committee (counts as public body for many grants)

Organisation 2: HEAG — Hethersett Environmental Action Group
  Type: Volunteer working group
  Project: "Happy Healthy Hethersett" — net zero project run in partnership
           with OPERGY (an energy services company)
  Legal status: Community/voluntary group associated with parish council

Location: Hethersett, Norfolk, England
  District: South Norfolk (council merged with Breckland as "South Norfolk and
            Breckland Council" in 2019 but retains South Norfolk identity)
  County: Norfolk
  Region: East of England / East Anglia
  Rural/Urban: Large village (~5,000 residents), semi-rural

Project areas they can deliver:
  • Tree planting on village greens, verges, community land
  • Hedgerow planting and habitat connectivity
  • Rewilding small patches of parish-owned land
  • Community solar panel installations (on public buildings)
  • Home insulation advice / referral schemes for residents
  • Heat pump community demonstrations and information days
  • Biodiversity surveys and species monitoring (birds, insects, plants)
  • Community education events, workshops, talks
  • EV charging point feasibility / installation on parish car parks
  • Net zero action planning for the parish
  • Carbon footprint measurement for the village
  • Wildflower meadow creation
  • Community composting and food waste reduction
  • School engagement and education programmes
  • Engagement with local farmers on agri-environment

Track record / assets they can mention:
  • Backed by elected parish council (adds credibility and governance)
  • Partnership with OPERGY on energy work
  • Active volunteer base
  • Community engagement already under way
  • Potential to work with Hethersett Academy and other local schools

Local development context (important for specific funding streams):
  • Major housing development under way in Hethersett by Taylor Wimpey and Persimmon —
    Section 106 agreements and CIL (Community Infrastructure Levy) monies flow from
    these to South Norfolk Council and some portion to the parish
  • Significant road scheme near Hethersett (A47 / Norwich Western Link / NDR corridor) —
    National Highways and Norfolk County Council hold mitigation and community funds
    tied to affected communities
  • Hethersett sits within the offshore wind corridor — Norfolk Vanguard, Norfolk Boreas,
    Hornsea (Ørsted), East Anglia ONE/TWO (ScottishPower), Dudgeon, Sheringham Shoal,
    Race Bank and other offshore wind projects off the Norfolk coast all carry statutory
    community benefit fund obligations; Hethersett is within the typical 35-mile benefit
    zone for several of these

== END APPLICANT PROFILE ==
"""

# ---------------------------------------------------------------------------
# Phase definitions — each has a name, label, focus, and detailed prompt
# ---------------------------------------------------------------------------

PHASES = [
    {
        "name": "national_lottery",
        "label": "National Lottery Community Fund",
        "focus": """
You are an expert UK grant fundraiser researching the National Lottery Community Fund (NLCF)
and related lottery distributors for grants that HEAT/HEAG in Hethersett could apply for.

NLCF programmes to research exhaustively:
- Awards for All England (£300–£10,000, rolling deadline, very accessible for community groups)
- National Lottery Community Fund standard grants (£10,001–£500,000)
- Climate Action Fund (if still open or successor programme exists)
- People and Nature Fund
- Community Led Place programme
- Reaching Communities England
- Fulfilling Lives
- Together for Our Planet (if active)
- The National Lottery Heritage Fund — Landscape Connections, National Lottery Grants for Heritage
- People's Postcode Lottery — Dream Fund, Green Communities
- Big Lottery Fund legacy programmes still disbursing

For each, search:
1. Is it currently open?
2. What are the exact eligibility criteria — can a parish council committee apply?
3. What are the minimum and maximum award amounts?
4. What is the deadline or is it rolling?
5. What geographic restrictions apply — England only, or Norfolk priority?
6. What types of projects are funded?
7. What is the direct application URL?

Be systematic. Search for each programme by name. If you find a programme has closed,
check whether a successor programme has replaced it.
""",
    },
    {
        "name": "government_nature",
        "label": "UK Government — Nature, Forestry & Environment",
        "focus": """
You are an expert UK environmental fundraiser researching UK government grant programmes
for nature, forestry and environment that HEAT/HEAG in Hethersett could access.

Programmes to research exhaustively:
- England Woodland Creation Offer (EWCO) — Forestry Commission, can community groups apply?
- Urban Tree Challenge Fund — trees in towns, who is eligible?
- Woodland Creation Planning Grant
- Woodland Creation Accelerator Fund
- Nature for Climate Fund — community strand
- Green Recovery Challenge Fund — check if reopened or has successor
- Biodiversity Net Gain (BNG) community fund streams — emerging since 2024 legislation
- Community Forest England / Mercia Forest / Great North Woods (East of England?)
- Trees for Climate (30by30 / Big Climate Fuss?)
- Farming in Protected Landscapes (FIPL) — not applicable but check for edge cases
- Higher Tier Countryside Stewardship — check if parish councils qualify
- Landscape Recovery Scheme — check community involvement strand
- Local Nature Recovery Strategies — are there associated funding pots?
- Natural England facilitation funds
- Environment Agency community flood action grants
- DEFRA community grants via local authorities — pass-through funding
- Biodiversity 2030 / 25 Year Environment Plan implementation grants
- Tree Health Pilot grants (diseased tree replacement)
- Hedgerow removal/replacement incentives
- Blue Carbon / wetland community funds

Search for each by name. Verify current status. Note if a programme requires a
landowner applicant vs. allows community groups.
""",
    },
    {
        "name": "energy_netzero",
        "label": "Energy Efficiency, Heat & Net Zero Schemes",
        "focus": """
You are an expert in UK energy efficiency funding researching grants for net zero community
projects that HEAT/HEAG in Hethersett could access.

Programmes to research exhaustively:
- Community Energy Fund (DESNZ) — current rounds open?
- Community Energy England grant schemes and competitions
- Great British Insulation Scheme (GBIS) — community referral or coordinator role?
- ECO4 (Energy Company Obligation 4) — community targeting, flex mechanism
- Warm Homes Plan / Local Grant (successor to Green Homes Grant)
- Warm Homes: Social Housing Fund (Wave 2/3)
- Boiler Upgrade Scheme — homeowner-facing but community facilitation grants?
- Heat Network Transformation Programme — community heat networks
- Low Carbon Workspaces (East of England-based?) — if HQ/PC office exists
- Salix Finance — public sector energy efficiency loans/grants (parish councils?)
- SSEN / National Grid / NGED (National Grid Electricity Distribution) community fund
- OVO Foundation grants
- Octopus Energy community grants
- E.ON Next Community Fund
- EDF Energy community programmes
- British Gas / Centrica community fund
- Shell / BP (declining but check) community energy grants
- Innovate UK Net Zero Living competitions
- Innovate UK Smart Local Energy Systems
- Retrofit Works / PAS2035 funding streams for communities
- Local Authority Delivery Scheme (LAD) successors
- Heat Network Zoning community engagement funds
- Electric Vehicle Infrastructure funding (OZEV/DVLA community EV grants)
- On-street Residential Charge Point Scheme (parish council car parks?)
- Workplace Charging Scheme (if parish office has parking)
- Active Travel England — e-bike, pedestrian grants with net zero angle
- Cycle to Work community equivalents

For each: current status, who can apply, amounts, deadlines, application URL.
""",
    },
    {
        "name": "wildlife_charities",
        "label": "Wildlife & Nature Charities",
        "focus": """
You are an expert in UK wildlife charity funding researching grants for nature/biodiversity
projects that HEAT/HEAG in Hethersett, Norfolk could access.

Organisations and programmes to research:
- Norfolk Wildlife Trust — local grants, Living Landscapes, volunteer support
- RSPB — community conservation grants, Local Group funding, Giving Nature a Home
- Wildlife Trusts national grants (separate from Norfolk WT)
- Woodland Trust — MOREwoods (free trees for landowners/communities), MOREhedges
- Trees for Cities — urban tree planting grants for community groups
- The Tree Council — community tree growing and care grants
- Buglife — B-Lines community grants, pollinator corridor funding
- Butterfly Conservation — community habitat grants
- Plantlife — wild plants/meadows community grants
- Froglife — amphibian/reptile habitat community grants
- People's Trust for Endangered Species (PTES) — community grants
- British Trust for Ornithology (BTO) — survey funding, Breeding Bird Survey support
- Wild Anglia (Norfolk and Suffolk nature partnership) — any community grants?
- Broads Authority — any grants extending to South Norfolk area?
- Natural Cambridgeshire / Cambridge Nature Network adjacent?
- Rivers Trust — community river/catchment grants, Norfolk rivers
- Wildfowl & Wetlands Trust (WWT) — community wetland projects
- Environment Agency Fisheries Improvement Programme
- Angling Trust — community water quality/habitat grants
- Rewilding Britain — community rewilding support grants
- Heal Rewilding — land/community grants
- Saving Nature — species recovery community grants
- Marine Conservation Society (any freshwater/terrestrial strand)

For each, check: Are they currently open? Can a village community group apply?
What is the maximum award? Is there a Norfolk/East Anglia geographic priority?
""",
    },
    {
        "name": "community_charities",
        "label": "Community Development & Action Charities",
        "focus": """
You are an expert in UK community development funding researching grants for community
environmental projects that HEAT/HEAG in Hethersett could access.

Organisations and programmes to research:
- Groundwork UK national grants and competitions
- Groundwork East (the regional trust covering Norfolk) — local programmes
- The Conservation Volunteers (TCV) — community green space grants
- Keep Britain Tidy — Eco-Schools grants, LEAF award funding, green flag communities
- Community First Norfolk — local grants for Norfolk community groups
- CPRE (Campaign to Protect Rural England) Norfolk — local grants or support
- Voluntary Norfolk — capacity-building and environmental grants
- Norfolk Community Foundation — specific funds relevant to environment
- Community Action Norfolk — grants for rural community groups
- NCVO community grants database — any environment-specific pots
- Action with Communities in Rural England (ACRE) — rural community grants
- Rural Community Council of Essex (RCCE) — adjacent, cross-boundary grants
- Community First Responders / Community First — environment strands
- Locality — community asset transfer grants, community power fund
- Power to Change — community business grants (if HEAG incorporates)
- Social Investment Business — community energy investment
- Access Social Care (if any social/environment overlap)
- Community Led Homes (if any eco-housing angle)
- Cohousing Association grants
- Village halls / community building energy grants (if parish has a hall)
- Playing Fields Association grants with environmental angle
- Fields in Trust — green space protection and improvement grants
- Civic Voice community improvement grants
- Design Council Place Programme (if redesigning village spaces)

Search for current open calls, rolling programmes, annual competitions.
Focus on what's accessible for a volunteer-led parish-council-backed group.
""",
    },
    {
        "name": "norfolk_regional",
        "label": "Norfolk & Regional Funders",
        "focus": """
You are an expert in Norfolk and East Anglia grant funding researching local grant programmes
that HEAT/HEAG in Hethersett, South Norfolk could access.

Funders and programmes to research exhaustively:
- Norfolk County Council — environmental grants, climate change fund, parish support grants
- South Norfolk and Breckland Council — environmental improvements, community grants
- New Anglia LEP — UKSPF (UK Shared Prosperity Fund) environmental / community strands
- Rural England Prosperity Fund (REPF) — South Norfolk allocation, project criteria
- LEADER Local Action Group for South Norfolk — current programme, eligible projects
- England Rural Development Programme successor — any community grants
- Norfolk Community Foundation — current open funds (environment, place, wellbeing)
- Community Foundation for Suffolk — cross-border applicants?
- East of England Agricultural Society / RASE — community agriculture/environment grants
- Norfolk Rural Community Council (NRCC) — grants, loan funds, support
- Anglia Water (AWE) Caring for our Catchments / community grants
- Broads Authority (is Hethersett near Broads area?) — if eligible, check grants
- Historic England / Heritage England — any environment/landscape grants for Norfolk
- East of England Development Agency successors — any residual community funds
- Greater Norwich Growth Board — adjacent area, check if Hethersett qualifies
- South Norfolk Partnership — any environmental improvement funding
- Norfolk & Waveney Integrated Care System — if health/environment overlap
- Active Norfolk — physical activity/active travel grants with green angle
- Sport England — green infrastructure/active space grants
- Active Norfolk — physical activity/active travel grants with green angle
- Sport England — green infrastructure/active space grants
- Network Rail community funds (if near railway)
- Armed Forces Covenant Fund Trust (if any military connection in village)

OFFSHORE WIND COMMUNITY BENEFIT FUNDS — HIGH PRIORITY:
Hethersett sits within the benefit zone of multiple offshore wind projects off the Norfolk
coast. Each project carries a statutory community benefit fund obligation. Research ALL of:
- Ørsted Hornsea Three (H3) Community Benefit Fund — off Norfolk/Lincolnshire, one of the
  largest wind farms in the world; what is the annual community pot? Who can apply?
  What is the geographic eligibility zone — does Hethersett / South Norfolk qualify?
- Ørsted Hornsea Four (H4) — any associated community fund announced yet?
- Norfolk Vanguard Offshore Wind Farm (Vattenfall) — community benefit fund details,
  eligibility area, how to apply, current round status
- Norfolk Boreas Offshore Wind Farm (Vattenfall) — same questions
- Dudgeon Offshore Wind Farm (Statoil/Equinor) — community fund, how to apply
- Sheringham Shoal Offshore Wind Farm (Equinor / Scatec) — community benefit fund
- Race Bank Offshore Wind Farm (Ørsted) — community fund details
- East Anglia ONE (ScottishPower Renewables) — community benefit fund, Norfolk eligibility
- East Anglia TWO (ScottishPower Renewables) — same
- East Anglia Hub / THREE — if under construction, any community funds announced?
- Dudgeon Extended (if applicable) — community fund
- Triton Knoll (RWE) — near Lincolnshire/Norfolk border, check eligibility for South Norfolk
- Search broadly: "offshore wind community benefit fund Norfolk 2024 2025 apply"
- Search: "Vattenfall Norfolk community fund apply"
- Search: "Ørsted Hornsea community benefit fund apply 2024"

For each offshore wind fund, establish: fund size per year, geographic eligibility area
(typically stated in miles from landfall or grid connection point), grant size range,
application process, and current open/closed status.

NATIONAL HIGHWAYS / MAJOR ROAD SCHEME FUNDS:
There are major road schemes near Hethersett — the Norwich Western Link, A47 dualling,
and NDR-related works. National Highways and Norfolk County Council manage associated
community and environmental mitigation funds. Research:
- National Highways A47 Community Fund — communities affected by the A47 improvement
  scheme; is Hethersett within the eligible area? Grant sizes, application process
- National Highways Community Fund (general programme) — what communities near major road
  schemes can apply for; search "National Highways community fund Norfolk apply"
- National Highways Environmental Mitigation Fund — green/biodiversity projects near
  road corridors; tree planting, noise bunds, wildflower verges
- Norwich Western Link community mitigation fund — any community benefit fund associated
  with this scheme; search "Norwich Western Link community fund environmental"
- Norfolk County Council road scheme community grants — any parish grants associated
  with NDR (Northern Distributor Road) successor schemes
- Search: "A47 dualling community benefit fund Norfolk"
- Search: "National Highways community fund A47 Norfolk parish"
- Highways England / National Highways biodiversity net gain fund — projects must
  compensate for habitat lost to road building; community groups can sometimes deliver

DEVELOPER CONTRIBUTIONS — TAYLOR WIMPEY & PERSIMMON:
Hethersett has active housing development by Taylor Wimpey and Persimmon. Each planning
consent generates Section 106 and/or CIL obligations. Research:
- Section 106 agreements for Taylor Wimpey development(s) in Hethersett — what
  environmental/community obligations exist? How does the parish access this money?
  Search: "Taylor Wimpey Hethersett planning section 106 community environment"
- Section 106 agreements for Persimmon development(s) in Hethersett — same
  Search: "Persimmon Hethersett planning section 106 environmental contribution"
- South Norfolk Community Infrastructure Levy (CIL) — how is the local portion
  (typically 15–25% goes to the parish council) allocated? Can HEAT/HEAG bid for it?
  Search: "South Norfolk CIL parish council allocation community projects"
- Taylor Wimpey Community Fund — general programme, but also check if there is a
  specific Hethersett site-linked fund; search "Taylor Wimpey Hethersett community fund"
- Persimmon Communities Fund — check for Hethersett or South Norfolk site-specific
  funding; search "Persimmon Hethersett community fund Norfolk"
- Homes England Growth Funds — infrastructure alongside new housing
- Search: "housebuilder community fund environmental South Norfolk 2024 2025"
- Any planning conditions requiring ecological mitigation deliverable by community groups

Be thorough. Search for each specifically. Norfolk has unique funding streams.
""",
    },
    {
        "name": "major_trusts",
        "label": "Major Independent Grant-Making Trusts",
        "focus": """
You are an expert UK fundraiser researching large independent charitable trusts that fund
environmental and community projects that HEAT/HEAG in Hethersett could apply to.

Trusts and foundations to research:
- Esmée Fairbairn Foundation — environment and natural world strand (large grants, strong Norfolk interest)
- Garfield Weston Foundation — community environment projects
- Tudor Trust — smaller grants, community groups
- Nationwide Foundation — housing, energy poverty, environment overlap
- Joseph Rowntree Foundation — climate justice, community power
- Dulverton Trust — rural environment, nature conservation (excellent match)
- Ernest Cook Trust — rural environment, education in nature
- Waterloo Foundation — climate, Wales & beyond, any England strands?
- Arcadia Fund — environment (large grants, check eligibility for small groups)
- The Sigrid Rausing Trust — environment
- Patagonia Environmental Grants — grassroots environment groups (US company, UK grants)
- 11th Hour Project — climate/environment
- John Ellerman Foundation — natural environment strand
- Calouste Gulbenkian Foundation UK — arts/environment/community
- Paul Hamlyn Foundation — community/youth/environment
- Wellcome Trust — climate and health overlap grants
- Wates Family Enterprise Trust — community/environment
- Zurich Insurance Foundation — climate resilience community grants
- Aviva Foundation — environment/community
- Charities Aid Foundation — pass-through environment grants
- Greggs Foundation — northern focus but check if national
- Biffa Award (through Environmental Body) — biodiversity, community, ecology
- Landfill Communities Fund / ENTRUST — projects near landfill sites
- Aggregates Levy Sustainability Fund (ALSF) — near quarries?
- Henry Smith Charity — community grants
- Rank Foundation — youth/community/environment
- St James's Place Foundation — community projects
- abrdn Financial Fairness Trust — community resilience/environment
- KPMG Foundation — community environment
- Morgan Stanley UK Foundation — community projects

Research: current open status, typical grant size, do they fund Norfolk/East Anglia,
can parish council committees / voluntary groups apply, what evidence do they need?
""",
    },
    {
        "name": "corporate_csr",
        "label": "Corporate & Energy Company Grant Programmes",
        "focus": """
You are an expert in corporate CSR grant programmes researching funding for community
environmental projects that HEAT/HEAG in Hethersett could access.

Companies and programmes to research:
- Tesco Community Grants (Bags of Help via Groundwork) — current round open?
- Tesco Stronger Starts — food/community angle
- Asda Foundation — community grants, environment strand
- Sainsbury's — Community Investment, local grant schemes
- Co-op Foundation — community and climate grants
- Waitrose & Partners Foundation — local community/environment
- Morrisons Foundation — community grants
- Persimmon Communities Fund — Persimmon IS actively building in Hethersett; search for
  site-specific or county-level fund; "Persimmon community fund Norfolk Hethersett"
- Taylor Wimpey Community Fund — Taylor Wimpey IS actively building in Hethersett; search
  for their community fund programme and any Norfolk/Hethersett allocation;
  "Taylor Wimpey community fund apply Norfolk"
- Ørsted UK Community Fund / Hornsea Community Benefit Fund — Ørsted operates Hornsea
  offshore wind off the Norfolk coast; search specifically for their community benefit
  fund for Norfolk communities; "Ørsted Hornsea community fund Norfolk apply"
- Vattenfall Norfolk Vanguard / Norfolk Boreas Community Fund — Vattenfall has two major
  wind farms off Norfolk; search for their community benefit fund for local groups
- Bovis Homes / Vistry / Bellway / Barratt — check for any other active sites near Hethersett
- E.ON Next Community Fund — current round?
- OVO Foundation/OVO Energy community grants
- Octopus Energy community grants (Green Octopus?)
- British Gas / Centrica community grants
- EDF Energy community fund
- SSE/SSEN Community Fund
- Scottish Power community grants
- National Grid community fund
- Anglian Water community fund and conservation grants
- Affinity Water grants (if applicable)
- Severn Trent — not Norfolk but check cross-boundary
- Amazon Sustainability — community grants
- Google.org — climate/environment community grants
- Microsoft Climate Innovation Fund — community projects
- Apple (MFR environmental grants) — check
- Lloyds Bank Foundation — community grants
- NatWest Group Foundation — environment/community
- Barclays Community Finance / 100x100
- HSBC UK community grants
- Vodafone Foundation — community/environment
- BT Better Futures — digital/environment community grants
- Network Rail Lineside community grants
- Transport for London / Highways England community environmental mitigations

For each, research: Is a programme currently open? What size grants?
Does it match environment/community projects? Any Norfolk preference?
""",
    },
    {
        "name": "climate_specialist",
        "label": "Climate Action & Net Zero Specialist Funds",
        "focus": """
You are an expert in specialist climate action funding researching grants for net zero
and climate action projects that HEAT/HEAG in Hethersett, Norfolk could access.

Programmes and organisations to research:
- Ashden Awards and grants — community climate action, outstanding organisations
- Climate Emergency Fund (CEF) — community climate mobilisation grants
- Zero Carbon Britain / Centre for Alternative Technology (CAT) grants
- Transition Network / Transition Towns — grants for local transition groups
- Community Climate Action Fund (any current iteration?)
- 10:10 Climate Action grants
- Friends of the Earth Local Groups grants
- ClientEarth community grants
- Stop Climate Chaos coalition — any grant-making?
- Carbon Literacy Project — community engagement funding
- Community Carbon reduction grants
- Climate Outreach — community climate communication grants
- NESTA — sustainable futures community innovation grants
- Innovate UK Sustainable Innovation Fund — community projects
- UK100 — local net zero community support
- Possible / 10:10 — community action grants
- Project Drawdown community implementation grants
- WRAP (Waste & Resources Action Programme) — community waste/circular economy grants
- Keep Britain Tidy — community litter/environment education grants
- Hubbub Foundation — community environmental behaviour change
- Ellen MacArthur Foundation — circular economy community grants
- Forum for the Future — community sustainability grants
- Green Alliance — community climate policy engagement
- Behaviour Change — community environment grants
- Julie's Bicycle — creative green / arts-environment grants
- Climate Justice Fund — community climate grants (Scotland focus but check UK-wide)
- Renewable UK community wind/solar grants
- Solar Trade Association community grants
- Battery storage community fund
- Green Finance Institute — community green finance
- Good Energy community grants
- Triodos Foundation community grants
- Ecology Building Society — green community building grants

Search: current status, grant sizes, eligibility for Norfolk community groups.
""",
    },
    {
        "name": "verify_enrich",
        "label": "Verify & Deepen the Most Promising Leads",
        "focus": """
You are an expert UK grant fundraiser performing a deep verification pass on grants
found for HEAT/HEAG in Hethersett, Norfolk.

Your task is to search for the most important grant programmes in the UK environmental
and community space and verify:
1. Is the programme definitively still open as of 2024/2025?
2. What is the EXACT maximum and minimum grant amount?
3. Is there a confirmed application deadline or is it rolling?
4. What is the direct URL to the application page (not just the homepage)?
5. Are parish councils or community groups explicitly mentioned as eligible applicants?
6. Has the programme changed name or moved to a new funder?
7. Are there any tips or insider knowledge about what makes a strong application?

Specifically re-check:
- Awards for All England (NLCF)
- England Woodland Creation Offer (Forestry Commission)
- Urban Tree Challenge Fund
- Community Energy Fund (DESNZ)
- Biffa Award
- Tesco Bags of Help / Community Grants
- Norfolk Community Foundation open funds
- Groundwork East community grants
- UK Shared Prosperity Fund through South Norfolk
- LEADER South Norfolk
- ECO4 Flex community targeting
- E.ON Next Community Fund
- Octopus Energy community grants
- Any 2024/2025 new government net zero community schemes announced

PRIORITY VERIFICATION — LOCAL NORFOLK FUNDS:
These are high-value, locally specific funds that must be verified carefully:
- Ørsted Hornsea Three community benefit fund — confirm it exists, the geographic
  eligibility radius, annual pot size, how to apply; search "Ørsted Hornsea community
  fund Norfolk" and "Hornsea Three community benefit fund apply"
- Vattenfall Norfolk Vanguard community benefit fund — confirm details, is Hethersett
  (South Norfolk) within eligible area?; search "Vattenfall Norfolk Vanguard community fund"
- National Highways A47 community fund — confirm programme exists for affected Norfolk
  communities; what can the money fund?; search "National Highways A47 Norfolk community fund"
- Taylor Wimpey Hethersett — confirm their community fund programme, what Hethersett
  residents can apply for; search "Taylor Wimpey community fund how to apply 2024 2025"
- Persimmon Hethersett — confirm their Communities Fund programme details and whether
  there is a site-specific allocation; search "Persimmon communities fund how to apply"
- South Norfolk CIL — confirm that the parish council receives a neighbourhood portion
  and how HEAT/HEAG can access it; search "South Norfolk CIL parish allocation 2024"

Also search for:
- "environmental grants open now UK 2025 community"
- "new environmental grants announced 2025 UK government"
- "net zero community grants England 2025 parish council"
- "Norfolk community grants environment 2025"
- "offshore wind community benefit fund Norfolk 2025"

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
) -> list[dict]:
    """
    Run one research phase. Returns a list of raw grant dicts.
    Makes up to 60 tool-use iterations before forcing a final answer.
    """
    phase_name = phase["name"]
    phase_label = phase["label"]
    progress(f"Starting phase: {phase_label}", "phase")

    funder_context = ""
    if discovered_funders:
        funder_context = (
            "\n\nFunders already identified in previous phases (avoid duplicating, "
            "but do cross-reference):\n" + "\n".join(f"  • {f}" for f in discovered_funders[:40])
        )

    system = f"""You are a tenacious, expert UK grant fundraiser with 20 years of experience
securing funding for community environmental groups in rural England. You know the UK grant
landscape intimately — every major funder, every recurring programme, every nuance of
eligibility for parish councils and community groups.

{APPLICANT_PROFILE}

Current research phase: {phase_label}

{phase["focus"]}
{funder_context}

CRITICAL INSTRUCTIONS:
1. Be EXHAUSTIVE. Do not stop after finding 3–4 grants. Search for every programme
   in your focus area. Use multiple, varied search queries.
2. Follow leads. If a search mentions a funder you haven't investigated, search for them.
3. Verify. If a programme might be closed, search to confirm its current status.
4. Be specific. Get actual grant amounts, real deadlines, real application URLs.
5. Do not give up early. Keep searching until you are confident you've covered the field.
6. When you are finally done searching, output ALL grants found as a single JSON array
   wrapped in ```json ... ``` markers. Include every grant you found, even if eligibility
   is uncertain (note uncertainty in eligibility_notes).

Output format — each grant must have:
  title            (string)
  funder           (string)
  description      (string — 2–4 sentences describing what it funds)
  url              (string or null — direct link to grant page)
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

    prompt = f"""Please research {phase_label} thoroughly for HEAT and HEAG in Hethersett.

Search systematically through all the programmes in your brief. For each one:
- Search to confirm it's currently open
- Get the specific grant amounts and deadline
- Get the application URL

Keep searching until you've exhausted all the programmes in this phase.
When done, output the full JSON array of grants found.
"""

    messages = [{"role": "user", "content": prompt}]
    searches_this_phase = 0
    last_search_count = 0
    force_finish_next = False

    for iteration in range(65):
        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=16000,
            thinking={"type": "adaptive"},
            system=system,
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
                f"  {phase_label}: {searches_this_phase} searches completed…",
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

        # At iteration 55, nudge the model to wrap up
        if iteration == 55 and response.stop_reason == "tool_use":
            messages.append({
                "role": "user",
                "content": (
                    "You've done excellent research. Please now compile everything "
                    "you've found into the final ```json ... ``` array and stop."
                ),
            })
        else:
            # Standard tool_use continuation — provide empty tool results for
            # server-side web_search (results are already in the assistant content)
            tool_results = [
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "",
                }
                for block in response.content
                if hasattr(block, "type") and block.type == "tool_use"
            ]
            if tool_results:
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
) -> list[dict]:
    """
    Run all research phases and return the combined de-duplicated grant list.

    phases_to_run: if provided, only run these phase names (useful for resuming).
    """
    active_phases = [
        p for p in PHASES
        if phases_to_run is None or p["name"] in phases_to_run
    ]

    all_grants: list[dict] = []
    discovered_funders: list[str] = []

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
            phase_grants = _run_phase(phase, discovered_funders, progress)
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
        f"Research complete. {len(all_grants)} grants found across all phases.",
        "phase",
    )
    return all_grants


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
        model="claude-opus-4-8",
        max_tokens=3000,
        thinking={"type": "adaptive"},
        system=APPLY_HELPER_SYSTEM,
        messages=messages,
    )

    return "".join(
        block.text for block in response.content if hasattr(block, "text") and block.text
    )
