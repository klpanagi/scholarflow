"""
Niobe Academic Specialist — Seed Script

Seeds 15 knowledge-base skills and 6 role-based agent configs into the database.
Each skill's prompt_template contains the distilled knowledge from the Matrixx Niobe plugin.

Skills:
1. academic-writing
2. academic-paper-review
3. eu-horizon
4. grant-writing
5. deliverable-writing
6. project-management
7. technical-lead
8. research-methodology
9. literature-review
10. scientific-presentation
11. data-management-plan
12. ip-exploitation
13. research-ideation
14. citation-verification
15. reproducibility-assessment
"""

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Skill, AgentConfig, AgentRole, Strategy, agent_skills_table


# ─────────────────────────────────────────────────────────────────────────────
# NIOBE SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────────────────────

NIOBE_SYSTEM_PROMPT = """You are Niobe — a Research, Project Management, and Technical Leadership Expert.

## Identity
- Temperature: 0.15 (precise, analytical)
- Output context: 16,000 tokens
- Thinking budget: 8,000 tokens

## Core Capabilities
1. **Academic Writing** — IMRaD structure, venue formatting (IEEE/ACM/Springer/Elsevier), abstract crafting, rebuttals, camera-ready preparation
2. **7-Stage Paper Review Pipeline** — INTAKE → STRUCTURAL → CLAIMS → LITERATURE → METHODOLOGY → ADVERSARIAL → SYNTHESIS. Produces dual documents: review-summary.md + response-to-authors.md
3. **Research Methodology** — Quantitative/qualitative/mixed methods, hypothesis formulation, experimental design, statistical analysis, sampling strategies
4. **Literature Review** — PRISMA 2020, search strategy, bibliometric analysis, meta-analysis, gap identification
5. **Grant & EU Proposal Writing** — Horizon Europe (RIA/IA/CSA/ERC/MSCA), NSF, NIH, ERC individual grants
6. **Deliverable & Report Writing** — EU deliverable types (R/DEM/DEC/DATA/DMP/ETHICS), reporting periods, KPI tracking
7. **Project Management** — Agile/Scrum/Kanban, WBS, Gantt, RACI, EVM, risk management
8. **Technical Leadership** — ADRs, code review strategy, tech debt, system design, incident management
9. **Scientific Presentation** — Conference talks, posters, pitch decks, slide design, demo preparation
10. **Data Management** — FAIR principles, DMP templates, GDPR, repositories, metadata standards
11. **IP & Exploitation** — TRL levels, patent process, licensing models, commercialization pathways
12. **Document Analysis** — PDF/DOCX/XLSX/PPTX extraction and analysis
13. **Research Ideation** — Hypothesis generation, gap analysis, novelty assessment, cross-domain inspiration, idea scoring
14. **Citation Verification** — Claim extraction, citation fact-checking, evidence grounding, reference validation, statistical claim verification
15. **Reproducibility Assessment** — Workflow reconstruction, code/data availability, computational reproducibility, open science compliance

## Behavioral Rules
- Never write application code, UI/UX, DevOps, or DSL engineering
- Focus exclusively on academic, research, project management, and technical leadership domains
- Always cite specific frameworks, templates, and best practices
- When reviewing papers, follow the 7-stage pipeline rigorously
- For EU proposals, always reference the specific Work Programme and call requirements
- Use structured output (headers, tables, checklists) for clarity
- When uncertain, state confidence level and recommend verification

## Output Format
- Use markdown headers (##, ###) for structure
- Use tables for comparisons and rubrics
- Use checklists (- [ ]) for actionable items
- Use code blocks for templates and examples
- Always include a "Key Takeaways" or "Summary" section at the end
"""


# ─────────────────────────────────────────────────────────────────────────────
# SKILL DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

ACADEMIC_WRITING_SKILL = {
    "name": "academic-writing",
    "description": "Academic paper writing for journals and conferences: IMRaD structure, abstract crafting, argumentation flow, citation practices, venue-specific formatting (IEEE/ACM/Springer/Elsevier), camera-ready preparation, cover letters, rebuttals.",
    "tags": ["academic", "writing", "papers", "journals", "conferences", "IMRaD"],
    "builtin_tools": ["search_papers", "format_citation", "find_citation"],
    "prompt_template": """# Academic Writing Skill

## IMRaD Structure
All empirical research papers follow Introduction → Methods → Results → and Discussion structure.

### Introduction (≈25% of paper)
- **Funnel structure**: Broad context → specific gap → your contribution
- Paragraph 1: Motivation — why does this domain matter?
- Paragraph 2-3: Background — what is known? Key concepts and prior work.
- Paragraph 4: Gap — what is missing or problematic?
- Paragraph 5: Contribution — what you did and what it achieves.
- Final paragraph: Paper outline ("Section 2 reviews… Section 3 describes…")

### Methods (≈25% of paper)
- Enough detail for reproducibility
- Subsections: Participants/Materials, Procedure, Measures, Analysis
- Use past tense, passive or active voice (venue-dependent)
- Include ethical approvals if applicable

### Results (≈25% of paper)
- Present findings without interpretation
- Use tables and figures for key data
- Report statistical results (test statistic, df, p-value, effect size)
- Reference every table/figure in text

### Discussion (≈25% of paper)
- Paragraph 1: Summary of key findings
- Paragraphs 2-4: Interpretation and relation to prior work
- Paragraph 5: Limitations (be honest but not self-defeating)
- Paragraph 6: Future work
- Final paragraph: Strong concluding statement

## Abstract Crafting
- **Length**: 150-250 words (check venue requirement)
- **Structure**: Context (1-2 sentences) → Problem (1 sentence) → Approach (2-3 sentences) → Results (1-2 sentences) → Implication (1 sentence)
- Write LAST, after the paper is complete
- Avoid abbreviations, citations, and jargon
- Must be self-contained — reader decides whether to read the paper based on this

## Citation Practices
- **When to cite**: Claims not your own, methodology borrowed, data used, significant influence
- **When NOT to cite**: Common knowledge, your own established work (unless relevant)
- **Citation density**: 1-3 citations per paragraph in related work; 0-1 in methods/results
- **Balance**: Include recent (last 3-5 years) AND seminal works
- **Avoid**: Citation padding (citing irrelevant work to please reviewers), self-citation inflation

## Venue-Specific Formatting

### IEEE
- Two-column format, 8.5×11 inch
- Title: 24pt, Authors: 11pt, Body: 10pt
- Numbered references [1], [2], …
- Figures below, tables above content
- Max 6-8 pages for conference, 10-14 for journal

### ACM
- Single-column submission format (review), two-column final
- ACM Reference Format for citations
- CCS concepts required
- Artifact evaluation encouraged

### Springer (LNCS/LNAI)
- Single-column, A4 format
- Title: 14pt bold, Authors: 12pt, Body: 10pt
- Numbered references [1]
- Max 12-15 pages for proceedings

### Elsevier
- Single-column submission, typeset by publisher
- Harvard or numbered citation (journal-dependent)
- Highlights required (3-5 bullet points)
- Graphical abstract encouraged

## Submission Artifacts

### Cover Letter
- Address to editor by name
- Paper title and type (research article, review, etc.)
- 2-3 sentence summary of contribution and significance
- Why this journal is the right fit
- Statement of originality (not under review elsewhere)
- Suggested reviewers (3-5, with justification)
- Conflicts of interest

### Rebuttal
- Thank reviewers for constructive feedback
- Address EVERY point raised
- Use quotes from reviews followed by your response
- Describe specific changes made (cite section/page/line)
- If you disagree, provide evidence and reasoning
- Be respectful and professional

### Camera-Ready
- Address ALL reviewer comments
- Check formatting requirements precisely
- Verify figures are high-resolution (300+ DPI)
- Ensure all references are complete and consistent
- Run spell-check and grammar-check
- Verify hyperlinks work
""",
}

ACADEMIC_PAPER_REVIEW_SKILL = {
    "name": "academic-paper-review",
    "description": "End-to-end academic paper review with 7-stage pipeline: structural analysis, claim-evidence mapping, literature grounding, methodology verification, adversarial red team, and synthesis. Produces dual documents (review-summary.md + response-to-authors.md) with venue-specific rubrics.",
    "tags": ["academic", "review", "peer-review", "pipeline", "rubrics"],
    "builtin_tools": ["search_papers", "extract_pdf_text", "extract_citations", "format_citation", "find_citation"],
    "prompt_template": """# Academic Paper Review — 7-Stage Pipeline

## Overview
This pipeline produces TWO mandatory documents:
1. **review-summary.md** — Internal review notes with detailed scoring
2. **response-to-authors.md** — Polished letter to authors with actionable feedback

## Stage 0: INTAKE
- Extract structured data from PDF (title, authors, abstract, sections, figures, tables, references)
- Identify paper type: empirical / theoretical / survey / systems / position
- Extract metadata: venue target, submission date, word count
- Flag missing sections or formatting issues

## Stage 1: STRUCTURAL ANALYSIS
- **IMRaD completeness**: Check all required sections exist and are substantive
- **Figure quality**: Resolution, labeling, caption quality, color accessibility
- **Table quality**: Clear headers, units, statistical annotations
- **Reference quality**: Recency, relevance, completeness, self-citation ratio
- **Writing quality**: Grammar, clarity, flow, jargon usage
- Score each dimension 1-10

## Stage 2: CLAIM EXTRACTION
Build a **Claim-Evidence Ledger**:
| Claim | Location | Evidence | Strength |
|-------|----------|----------|----------|
| "Our method outperforms SOTA" | Abstract, §4.2 | Table 2, ablation study | Strong |
| "Approach generalizes across domains" | §1 | Only tested on 2 datasets | Weak |

Strength classification:
- **Strong**: Multiple evidence sources, statistical significance, reproducible
- **Moderate**: Some evidence, but gaps or limitations exist
- **Weak**: Claim made but evidence is insufficient or missing
- **Unsupported**: No evidence provided for claim

## Stage 3: LITERATURE GROUNDING
Run 3 parallel searches:
1. **Related Work Searcher**: Find papers the authors SHOULD have cited but didn't
2. **Baseline Scout**: Find stronger baselines that should have been compared against
3. **Novelty Assessor**: Find prior work that threatens the paper's novelty claims

For each search:
- Query Semantic Scholar, arXiv, CrossRef
- Compare against paper's reference list
- Identify gaps and missed connections
- Assess whether novelty claims hold up

## Stage 4: METHODOLOGY VERIFICATION
- **Statistical rigor**: Appropriate tests, sample sizes, multiple comparison corrections
- **Reproducibility**: Code availability, hyperparameters, random seeds, hardware specs
- **Math verification**: Check key equations for correctness, notation consistency
- **Experimental design**: Controls, ablations, evaluation metrics, dataset splits
- **Threats to validity**: Internal, external, construct, conclusion validity

## Stage 5: ADVERSARIAL RED TEAM
Three parallel adversarial analyses:

### Breaker (Logical Flaws)
- Find logical fallacies, circular reasoning, unsupported inferences
- Check for cherry-picked results, survivorship bias
- Identify confounding variables not addressed

### Butcher (Missing Experiments)
- What experiments would a skeptical reviewer demand?
- Are ablation studies complete?
- Are there obvious failure cases not discussed?
- Is the evaluation dataset representative?

### Collector (Novelty Threats)
- Is this incremental or truly novel?
- What's the minimum viable novelty for this venue?
- Are there concurrent works that diminish novelty?

## Stage 6: SYNTHESIS
- Merge all stage outputs into coherent assessment
- Calibrate against venue rubric (use venue-specific scoring dimensions)
- Assess overall contribution significance
- **Quality gate**: Does this paper meet the venue's minimum bar?

## Output Documents

### review-summary.md (Internal)
```markdown
# Review Summary: [Paper Title]

## Paper Type: [empirical/theoretical/survey/systems/position]

## Scores
| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Novelty | 7/10 | 25% | 1.75 |
| Technical Quality | 6/10 | 30% | 1.80 |
| Presentation | 8/10 | 15% | 1.20 |
| Reproducibility | 5/10 | 15% | 0.75 |
| Impact | 7/10 | 15% | 1.05 |
| **Total** | | | **6.55/10** |

## Claim-Evidence Ledger
[Table from Stage 2]

## Literature Gaps
[List from Stage 3]

## Methodology Issues
[List from Stage 4]

## Adversarial Findings
### Logical Flaws (Breaker)
### Missing Experiments (Butcher)
### Novelty Threats (Collector)

## Recommendation
[Accept / Weak Accept / Borderline / Weak Reject / Reject]
```

### response-to-authors.md (External)
```markdown
# Review of [Paper Title]

## Summary
[2-3 paragraph summary of the paper and its contributions]

## Strengths
1. [Strength 1 with specific evidence]
2. [Strength 2]

## Weaknesses
1. **[Weakness Category]**: [Description with specific references to sections/lines]
   - *Suggestion*: [Actionable recommendation]
2. [Weakness 2]

## Questions for Authors
1. [Question 1]
2. [Question 2]

## Minor Issues
- [Typo/formatting issue 1]
- [Issue 2]

## Overall Assessment
[1-2 paragraphs summarizing the overall assessment and recommendation]

## Confidence
[Reviewer confidence: 1-5, with justification]
```

## Common Weaknesses Quick Reference
| Category | Example | Impact |
|----------|---------|--------|
| Weak baselines | Comparing only against old methods | High |
| Small datasets | Testing on 1-2 datasets only | High |
| No ablation | Can't isolate contribution of each component | Medium |
| Missing stats | No p-values, confidence intervals, or effect sizes | Medium |
| Poor writing | Grammar errors, unclear explanations | Low-Medium |
| Incomplete related work | Missing recent or relevant citations | Medium |
| No code | Results can't be verified | High |
""",
}

EU_HORIZON_SKILL = {
    "name": "eu-horizon",
    "description": "Horizon Europe proposal expertise: programme structure, funding instruments (RIA/IA/CSA/ERC/MSCA), evaluation criteria, Part B structure, budget rules, consortium requirements, WP conventions, TRL levels, ethics, and Open Science.",
    "tags": ["EU", "Horizon-Europe", "proposals", "funding", "RIA", "IA", "CSA", "ERC", "MSCA"],
    "builtin_tools": ["search_papers", "search_web"],
    "prompt_template": """# Horizon Europe Skill

## Programme Structure
Horizon Europe (2021-2027) has three pillars:

### Pillar 1: Excellent Science
- European Research Council (ERC) — frontier research
- Marie Skłodowska-Curie Actions (MSCA) — researcher mobility
- Research Infrastructures

### Pillar 2: Global Challenges & Industrial Competitiveness
- Cluster 1: Health
- Cluster 2: Culture, Creativity, Inclusive Society
- Cluster 3: Civil Security for Society
- Cluster 4: Digital, Industry, Space
- Cluster 5: Climate, Energy, Mobility
- Cluster 6: Food, Bioeconomy, Natural Resources, Agriculture

### Pillar 3: Innovative Europe
- European Innovation Council (EIC)
- European Innovation Ecosystems
- European Institute of Innovation & Technology (EIT)

## Funding Instruments

### Research and Innovation Action (RIA)
- 100% funding rate
- 3-5 partners minimum
- 2-4 year duration
- €2-10M typical budget
- Focus: Research + Innovation

### Innovation Action (IA)
- 70% funding rate (100% for non-profit)
- 3+ partners
- 2-4 year duration
- €3-15M typical budget
- Focus: Innovation + Demonstration

### Coordination and Support Action (CSA)
- 100% funding rate
- 1+ partner
- 1-3 year duration
- €0.5-2M typical budget
- Focus: Coordination, networking, policy support

### ERC Grants
- **Starting Grant (StG)**: 2-7 years post-PhD, up to €1.5M/5yr
- **Consolidator Grant (CoG)**: 7-12 years post-PhD, up to €2M/5yr
- **Advanced Grant (AdG)**: Established PIs, up to €2.5M/5yr
- **Synergy Grant (SyG)**: 2-4 PIs, up to €10M/6yr

### MSCA
- **Doctoral Networks (DN)**: Training networks, 15+ ESRs
- **Postdoctoral Fellowships (PF)**: Individual fellowships
- **Staff Exchanges (SE)**: Intersectoral/international secondments
- **COFUND**: Co-funding of regional/national programmes

## Evaluation Criteria (Standard)
1. **Excellence** (50%)
   - Soundness of concept, quality of objectives
   - Clarity and credibility of methodology
   - Ambition and innovation
   - Interdisciplinary approach (if relevant)

2. **Impact** (30%)
   - Credibility of measures to achieve expected impact
   - Measures to enhance impact (dissemination, exploitation, communication)
   - Strategic exploitation plan

3. **Implementation** (20%)
   - Quality and effectiveness of work plan
   - Appropriateness of consortium
   - Resources and management

## Part B Structure (max 70 pages for RIA/IA)
1. **Excellence** (≈15 pages)
   - Objectives and alignment with work programme
   - Relation to state of the art
   - Methodology (including inter/multidisciplinary aspects)

2. **Impact** (≈15 pages)
   - Expected outcomes and impact pathway
   - Dissemination, exploitation, communication measures
   - Measures to maximise impact (standard + additional)

3. **Implementation** (≈15 pages)
   - Work plan (Gantt chart, work packages, deliverables, milestones)
   - Consortium composition and capacity
   - Resources (person-months, budget per WP)

4. **Members of the Consortium** (≈10 pages)
   - Partner descriptions, relevant expertise
   - Consortium as a whole

5. **Ethics and Security** (remaining pages)

## Budget Rules
- **Personnel costs**: Actual costs × time spent on project
- **Subcontracting**: Must be justified, competitive tendering
- **Other direct costs**: Travel, equipment, consumables
- **Indirect costs**: 25% flat rate of direct eligible costs (minus subcontracting and in-kind contributions)
- **No profit**: Non-profit entities only for indirect cost claim

## Work Package Conventions
- **WP1**: Management and Coordination
- **WP2-WPn**: Research/Innovation WPs (aligned with objectives)
- **WPn+1**: Dissemination, Exploitation, Communication
- **WPn+2**: Ethics requirements (if needed)

Each WP needs:
- Objectives, description of work, deliverables, milestones
- Lead partner, participants, person-months per partner
- Start/end month

## TRL Levels
| TRL | Description | Evidence |
|-----|-------------|----------|
| 1 | Basic principles observed | Scientific publication |
| 2 | Technology concept formulated | Application paper |
| 3 | Experimental proof of concept | Lab demo, prototype |
| 4 | Technology validated in lab | Lab-scale demo |
| 5 | Technology validated in relevant environment | Simulated environment demo |
| 6 | Technology demonstrated in relevant environment | Prototype in relevant environment |
| 7 | System prototype demonstration | Operational environment demo |
| 8 | System complete and qualified | Test and demonstration |
| 9 | System proven in operational environment | Mission-proven |

## Ethics Requirements
- Human participants: Informed consent, data protection (GDPR)
- Animals: 3Rs (Replace, Reduce, Refine)
- Dual use: Export control, potential misuse
- Environment: Environmental impact assessment
- Developing countries: Benefit sharing, capacity building

## Open Science
- **Open Access**: All publications must be OA (Gold or Green)
- **Open Data**: FAIR data principles, Data Management Plan (DMP)
- **Open Source**: Software should be shared when possible
- **EOSC**: European Open Science Cloud integration
""",
}

GRANT_WRITING_SKILL = {
    "name": "grant-writing",
    "description": "General grant and funding proposal writing beyond EU: NSF, NIH, ERC individual grants, national agencies, industry calls. Budget narratives, biosketches, broader impacts, evaluation criteria alignment, panel review processes.",
    "tags": ["grants", "funding", "NSF", "NIH", "ERC", "proposals"],
    "builtin_tools": ["search_papers", "search_web"],
    "prompt_template": """# Grant Writing Skill

## NSF Proposals

### Program Types
- **CAREER**: Junior faculty, 5-year plan integrating research + education
- **Standard/Continuing Grant**: Regular research proposals
- **EAGER**: High-risk, high-reward, 2 pages + budget
- **RAPID**: Time-sensitive research (e.g., natural disasters)
- **Workshop/Conference**: Conference support

### NSF Merit Review Criteria
**Intellectual Merit:**
- How important is the proposed activity?
- How well does it advance knowledge?
- How qualified is the PI/team?
- How creative and original?
- How well conceived and organized?

**Broader Impacts:**
- Benefit to society
- Broadening participation (underrepresented groups)
- Enhancement of infrastructure (research, education, facilities)
- Dissemination to broad audiences
- Benefits to specific organizations

### Proposal Structure
1. **Cover Sheet** (NSF Form 1207)
2. **Project Summary** (1 page max) — Overview, Intellectual Merit, Broader Impacts
3. **Project Description** (15 pages max) — Introduction, Prior Work, Research Plan, Broader Impacts, Timeline
4. **References Cited** (no page limit)
5. **Budget and Budget Justification** (2-15 pages)
6. **Facilities, Equipment, and Other Resources** (2-3 pages)
7. **Data Management Plan** (2 pages max)
8. **Postdoctoral Mentoring Plan** (1 page, if postdoc included)
9. **Supplementary Documents** (as needed)

## NIH Proposals

### Grant Types
- **R01**: Major research project, 3-5 years, $250K-$500K/year
- **R21**: Exploratory/developmental, 2 years, $275K total
- **R03**: Small research grants, 2 years, $50K/year
- **K99/R00**: Pathway to Independence Award
- **U01**: Cooperative agreement

### NIH Structure (R01)
1. **Specific Aims** (1 page) — 2-4 specific aims, significance, innovation
2. **Research Strategy** (12 pages) — Significance, Innovation, Approach
3. **Biosketches** (NIH format, 5 pages each)
4. **Budget and Justification**
5. **Resources** (facilities, equipment)
6. **Protection of Human Subjects / Vertebrate Animals**
7. **Data Sharing Plan**
8. **Authentication of Key Biological Resources**
9. **Letters of Support**

### NIH Scoring (1-9)
| Score | Descriptor | Meaning |
|-------|-----------|---------|
| 1 | Exceptional | Outstanding, virtually no weaknesses |
| 2 | Outstanding | Excellent with minor weaknesses |
| 3 | Excellent | Very good with some weaknesses |
| 4 | Very Good | Good with several weaknesses |
| 5 | Good | Sound with significant weaknesses |
| 6 | Fair | Fundamentally flawed |
| 7-9 | Poor/Marginal | Not fundable |

## ERC Individual Grants

### Grant Types
- **Starting Grant (StG)**: 2-7 years post-PhD, up to €1.5M/5yr
- **Consolidator Grant (CoG)**: 7-12 years post-PhD, up to €2M/5yr
- **Advanced Grant (AdG)**: Established PIs, up to €2.5M/5yr

### ERC Evaluation Criteria
1. **Ground-breaking Nature, Potential Impact** (50%)
   - Novelty and ambition
   - Potential for scientific breakthrough
   - Impact on the field

2. **PI's Research Track Record and Profile** (50%)
   - Publications in top venues
   - Independence and leadership
   - Research group development
   - Peer recognition

### ERC Part B1 (15 pages)
- State of the art and objectives
- Methodology
- Alignment with Frontier Research

### ERC Part B2 (10 pages)
- CV (max 2 pages)
- Early achievements track record
- Ten most important publications
- Major grants held

## National Agencies
- **UKRI (UK)**: Standard, New Investigator, Future Leaders
- **DFG (Germany)**: Individual Grants, Emmy Noether, Heisenberg
- **ANR (France)**: AAPG, JCJC, PRCE
- **NWO (Netherlands)**: Veni, Vidi, Vici (talent scheme)

## Reviewer Psychology
1. **First impression matters**: Title, abstract, first page set the tone
2. **Scanning pattern**: Reviewers skim — use headers, bold, bullets
3. **Negative bias**: Weaknesses are weighted more than strengths
4. **Comparison**: Your proposal is judged against others in the same panel
5. **Feasibility**: Ambitious but achievable is the sweet spot
6. **Specificity**: Vague claims are dismissed; specific plans are valued

## Common Rejection Reasons
1. Not novel enough (incremental)
2. Poorly motivated research questions
3. Weak methodology or missing details
4. Unrealistic scope for the budget/timeline
5. PI lacks track record for this specific area
6. Broader impacts not credible
7. Poor writing quality
8. Missing key references
""",
}

DELIVERABLE_WRITING_SKILL = {
    "name": "deliverable-writing",
    "description": "EU project deliverable writing expertise: deliverable types (R/DEM/DEC/DATA/DMP/ETHICS), dissemination levels, document structure, reporting periods, KPI tracking, risk registers, D&E plans, periodic vs final reports.",
    "tags": ["EU", "deliverables", "reports", "dissemination", "DMP", "ethics"],
    "builtin_tools": ["search_papers", "format_citation"],
    "prompt_template": """# Deliverable Writing Skill

## Deliverable Types
| Code | Type | Description |
|------|------|-------------|
| R | Report | Research reports, technical reports, studies |
| DEM | Demonstrator | Prototype, pilot, proof of concept |
| DEC | Other | Websites, videos, press releases, workshops |
| DATA | Dataset | Research data generated |
| DMP | Data Management Plan | FAIR data handling plan |
| ETHICS | Ethics | Ethics requirements deliverables |

## Dissemination Levels
| Code | Level | Description |
|------|-------|-------------|
| PU | Public | Fully public, no restrictions |
| SEN | Sensitive | Limited audience (e.g., consortium + reviewers) |
| EU-CL | EU Classified | Restricted to EU institutions |
| CO | Confidential | Restricted to consortium members |
| INT | Internal | Restricted to specific partners |

## Document Structure Template
```
# [Deliverable Number] — [Title]

## Document Information
- Deliverable: D[X.Y]
- Type: [R/DEM/DEC/DATA/DMP/ETHICS]
- Dissemination Level: [PU/SEN/CO]
- Due Date: [Month X]
- Lead Partner: [Partner Name]
- Authors: [List]
- Version: [X.Y]
- Date: [DD/MM/YYYY]
- Reviewers: [List]
- Status: [Draft/Reviewed/Approved/Final]

## Executive Summary (1-2 pages)
[Key findings, conclusions, recommendations]

## Table of Contents

## 1. Introduction
[Context, objectives of this deliverable]

## 2. [Main Content Sections]
[Structure depends on deliverable type]

## 3. Conclusions and Next Steps

## References

## Annexes (if needed)
```

## Reporting Periods
| Period | Typical Duration | Focus |
|--------|-----------------|-------|
| Period 1 | Months 1-18 | Setup, initial research, baselines |
| Period 2 | Months 19-36 | Main research, first results |
| Period 3 | Months 37-54 | Validation, exploitation |
| Period 4 | Months 55-60 | Final results, dissemination |

## KPI Tracking
Always include a KPI table in periodic reports:
| KPI | Target | Actual | Status | Notes |
|-----|--------|--------|--------|-------|
| Publications | 10 | 8 | On track | 2 in review |
| Demos | 5 | 3 | At risk | Delayed by 3 months |
| Patents | 2 | 1 | On track | 1 filed |

## Risk Register
| ID | Risk | Probability | Impact | Mitigation | Owner | Status |
|----|------|-------------|--------|------------|-------|--------|
| R1 | Key researcher leaves | Low | High | Cross-training, documentation | PM | Open |
| R2 | Technology not feasible | Medium | High | Alternative approach identified | TRL | Mitigated |

## D&E Plan (Dissemination and Exploitation)
### Dissemination Activities
- Scientific publications (journals, conferences)
- Workshop organization
- Website and social media
- Newsletters and press releases
- Standardization contributions

### Exploitation Activities
- Commercial exploitation (products, services)
- Further research (follow-up projects)
- Policy influence
- Education and training

### Communication Activities
- Public engagement
- Media relations
- Stakeholder workshops

## Amendment Procedures
- Minor amendments: Notify PO, no formal approval needed
- Major amendments (budget >25%, consortium changes): Formal amendment request
- Timeline: Submit request 2-3 months before desired effective date
""",
}

PROJECT_MANAGEMENT_SKILL = {
    "name": "project-management",
    "description": "Project management expertise: Agile/Scrum/Kanban, Waterfall, WBS, Gantt charts, resource planning (RACI), risk management, stakeholder engagement, earned value management, meeting management.",
    "tags": ["project-management", "Agile", "Scrum", "WBS", "Gantt", "risk"],
    "builtin_tools": [],
    "prompt_template": """# Project Management Skill

## Methodologies

### Agile/Scrum
- **Sprint**: 1-4 week iterations
- **Roles**: Product Owner, Scrum Master, Development Team
- **Ceremonies**: Sprint Planning, Daily Standup, Sprint Review, Retrospective
- **Artifacts**: Product Backlog, Sprint Backlog, Increment
- **When to use**: Uncertain requirements, fast-changing environment, software development

### Kanban
- Visual board (To Do → In Progress → Done)
- WIP limits per column
- Continuous flow (no sprints)
- Pull-based system
- **When to use**: Continuous delivery, operations, support

### Waterfall
- Sequential phases: Requirements → Design → Implementation → Testing → Deployment
- Heavy documentation upfront
- Change control process
- **When to use**: Fixed requirements, regulated industries, construction

## Work Breakdown Structure (WBS)
```
Project
├── 1. Planning
│   ├── 1.1 Requirements Gathering
│   ├── 1.2 Stakeholder Analysis
│   └── 1.3 Project Charter
├── 2. Design
│   ├── 2.1 Architecture
│   ├── 2.2 Detailed Design
│   └── 2.3 Design Review
├── 3. Implementation
│   ├── 3.1 Module A
│   ├── 3.2 Module B
│   └── 3.3 Integration
├── 4. Testing
│   ├── 4.1 Unit Tests
│   ├── 4.2 Integration Tests
│   └── 4.3 User Acceptance
└── 5. Deployment
    ├── 5.1 Staging
    ├── 5.2 Production
    └── 5.3 Handover
```

## Gantt Chart Best Practices
- Show dependencies between tasks
- Include milestones (diamonds)
- Color-code by team/phase
- Show critical path
- Update weekly
- Include buffer time (10-20%)

## RACI Matrix
| Activity | PM | Tech Lead | Dev Team | Stakeholders |
|----------|-----|-----------|----------|--------------|
| Requirements | A | C | I | R |
| Architecture | C | R/A | C | I |
| Implementation | I | A | R | I |
| Testing | A | C | R | I |
| Deployment | R/A | C | R | I |

R = Responsible, A = Accountable, C = Consulted, I = Informed

## Risk Management

### Risk Register
| ID | Risk | Probability | Impact | Score | Mitigation | Owner |
|----|------|-------------|--------|-------|------------|-------|
| R1 | [Description] | H/M/L | H/M/L | P×I | [Action] | [Person] |

### Risk Response Strategies
- **Avoid**: Change plan to eliminate risk
- **Mitigate**: Reduce probability or impact
- **Transfer**: Insurance, outsourcing
- **Accept**: Acknowledge and budget for contingency

## Stakeholder Management
1. **Identify**: Who is affected? Who has influence?
2. **Analyze**: Power/Interest grid
3. **Plan**: Communication frequency and method
4. **Engage**: Regular updates, feedback loops
5. **Monitor**: Satisfaction, concerns, changing dynamics

## Earned Value Management (EVM)
- **PV (Planned Value)**: Budgeted cost of work scheduled
- **EV (Earned Value)**: Budgeted cost of work performed
- **AC (Actual Cost)**: Actual cost of work performed
- **SPI = EV/PV**: Schedule Performance Index (<1 = behind)
- **CPI = EV/AC**: Cost Performance Index (<1 = over budget)
- **EAC = BAC/CPI**: Estimate at Completion

## Status Reporting
Weekly status should include:
1. Accomplishments this week
2. Plans for next week
3. Risks and issues
4. Metrics (burndown, velocity, budget)
5. Decisions needed

## Meeting Management
- Always have an agenda
- Start and end on time
- Assign a note-taker
- Document decisions and action items
- Follow up within 24 hours
""",
}

TECHNICAL_LEAD_SKILL = {
    "name": "technical-lead",
    "description": "Technical leadership expertise: architecture decision records (ADRs), code review strategy, tech debt management, system design, team mentoring, technical roadmaps, incident management, build/release engineering.",
    "tags": ["tech-lead", "ADR", "architecture", "code-review", "tech-debt", "system-design"],
    "builtin_tools": [],
    "prompt_template": """# Technical Lead Skill

## Architecture Decision Records (ADR)

### Template
```markdown
# ADR-[NNN]: [Title]

## Status
[Proposed | Accepted | Deprecated | Superseded by ADR-XXX]

## Context
[What is the issue that we're seeing that is motivating this decision?]

## Decision
[What is the change that we're proposing and/or doing?]

## Consequences
### Positive
- [Benefit 1]
- [Benefit 2]

### Negative
- [Tradeoff 1]
- [Tradeoff 2]

### Risks
- [Risk 1 and mitigation]

## Alternatives Considered
### Option A: [Name]
- Pros: [...]
- Cons: [...]

### Option B: [Name]
- Pros: [...]
- Cons: [...]

## References
- [Link 1]
- [Link 2]
```

## Code Review Strategy

### Feedback Tiers
| Tier | Label | Meaning | Action Required |
|------|-------|---------|-----------------|
| 🔴 | Blocker | Must fix before merge | Author must address |
| 🟠 | Concern | Should fix, discuss if disagree | Author should address |
| 🟡 | Suggestion | Nice to have, optional | Author decides |
| 🟢 | Nit | Style, minor, no functional impact | Author decides |
| ❓ | Question | Need clarification | Author explains |
| 👍 | Praise | Something done well | No action |

### Review Checklist
- [ ] Does it solve the stated problem?
- [ ] Is it testable? Are tests included?
- [ ] Are edge cases handled?
- [ ] Is error handling appropriate?
- [ ] Is it readable and maintainable?
- [ ] Does it follow project conventions?
- [ ] Are there security concerns?
- [ ] Is performance acceptable?
- [ ] Is documentation updated?

## Tech Debt Management

### Classification
| Type | Description | Priority |
|------|-------------|----------|
| Deliberate | "We know this is wrong but we need to ship" | Plan for fix |
| Inadvertent | "Now we know the right way" | Fix soon |
| Bit rot | "Dependencies changed, code aged" | Fix when touched |

### Paydown Strategy
1. **20% rule**: Spend 20% of sprint capacity on tech debt
2. **Boy Scout Rule**: Leave code better than you found it
3. **Dedicated sprints**: Quarterly tech debt sprint
4. **Track it**: JIRA/Linear tickets with "tech-debt" label

## System Design Document Template
```markdown
# System Design: [Name]

## Overview
[1-2 paragraph summary]

## Requirements
### Functional
- [Requirement 1]
- [Requirement 2]

### Non-Functional
- Performance: [specific metrics]
- Scalability: [growth projections]
- Availability: [SLA targets]
- Security: [compliance requirements]

## High-Level Architecture
[Diagram description]

## Component Design
### Component A
- Responsibility
- Interface
- Dependencies
- Data model

### Component B
[Same structure]

## Data Model
[ER diagram or schema]

## API Design
[Endpoints, request/response formats]

## Deployment Architecture
[Infrastructure diagram]

## Monitoring & Observability
[Metrics, logs, alerts]

## Risks and Mitigations
| Risk | Mitigation |
|------|------------|
| [Risk] | [Plan] |
```

## Technical Roadmap

### Now/Next/Later Framework
- **Now** (this quarter): Committed work, clear scope
- **Next** (next quarter): Planned work, scope may shift
- **Later** (6+ months): Vision, exploratory

### Capacity Estimation
1. Team velocity (story points per sprint)
2. Available sprint capacity (holidays, meetings)
3. Planned vs unplanned work ratio (60/40 is healthy)
4. Buffer for incidents and support (10-20%)

## Incident Management

### Severity Levels
| Level | Impact | Response Time | Example |
|-------|--------|---------------|---------|
| SEV-1 | Complete outage | 15 min | Service down |
| SEV-2 | Major degradation | 30 min | 50% errors |
| SEV-3 | Minor degradation | 2 hours | Slow response |
| SEV-4 | Cosmetic/minor | Next business day | UI glitch |

### Post-Mortem Template
```markdown
# Incident Post-Mortem: [Title]

## Summary
[What happened, when, impact]

## Timeline
- [HH:MM] [Event]
- [HH:MM] [Event]

## Root Cause
[Technical root cause]

## Contributing Factors
[What made this worse]

## Resolution
[How it was fixed]

## Action Items
| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| [Action] | [Person] | [Date] | [Status] |

## Lessons Learned
- [Lesson 1]
- [Lesson 2]
```

## Team Mentoring

### 1:1 Structure (30 min)
- Personal check-in (5 min)
- Project updates (10 min)
- Growth discussion (10 min)
- Action items (5 min)

### Growth Framework
1. **Technical skills**: New languages, frameworks, tools
2. **System design**: Architecture thinking, tradeoffs
3. **Communication**: Writing, presenting, influencing
4. **Leadership**: Mentoring, decision-making, ownership

### Delegation Matrix
| Task Type | Delegate To | Your Role |
|-----------|-------------|-----------|
| Routine | Junior | Review output |
| Complex | Senior | Pair, then review |
| Strategic | Lead | Discuss, decide together |
| Novel | Yourself | Do, then teach |
""",
}

RESEARCH_METHODOLOGY_SKILL = {
    "name": "research-methodology",
    "description": "Research design and methodology: quantitative/qualitative/mixed methods, hypothesis formulation, experimental design, statistical analysis, sampling strategies, validity/reliability, survey design, ethical considerations.",
    "tags": ["research", "methodology", "statistics", "experimental-design", "hypothesis"],
    "builtin_tools": ["search_papers"],
    "prompt_template": """# Research Methodology Skill

## Research Paradigms
| Paradigm | Ontology | Epistemology | Methods |
|----------|----------|--------------|---------|
| Positivist | Objective reality | Observable, measurable | Quantitative |
| Interpretivist | Social construction | Subjective meaning | Qualitative |
| Pragmatist | Reality is useful | What works | Mixed methods |
| Critical | Power structures | Challenge assumptions | Action research |

## Hypothesis Formulation
- **H0 (Null)**: No effect, no difference, no relationship
- **H1 (Alternative)**: Effect exists, difference exists, relationship exists
- **Directional**: H1 specifies direction (e.g., "A > B")
- **Non-directional**: H1 just says "A ≠ B"

### Good Hypotheses
- Testable and falsifiable
- Specific and precise
- Grounded in theory or prior work
- Variables are clearly defined

## Experimental Design

### Designs
| Design | Description | When to Use |
|--------|-------------|-------------|
| Between-subjects | Different groups get different conditions | No carryover effects |
| Within-subjects | Same participants, all conditions | Limited participants |
| Factorial | Multiple IVs, all combinations | Interaction effects |
| Repeated measures | Same participants, multiple time points | Change over time |

### Validity Types
| Type | Threat | Mitigation |
|------|--------|------------|
| Internal | Confounding variables | Randomization, controls |
| External | Generalizability | Representative sample |
| Construct | Measuring the right thing | Validated instruments |
| Conclusion | Correct statistical inference | Appropriate tests |

## Sampling Strategies

### Probability Sampling
- **Simple random**: Equal chance for all
- **Stratified**: Proportional representation of subgroups
- **Cluster**: Random selection of groups, then all members
- **Systematic**: Every nth element

### Non-Probability Sampling
- **Convenience**: Whoever is available
- **Purposive**: Selected based on criteria
- **Snowball**: Participants refer others
- **Quota**: Fixed numbers per subgroup

### Sample Size
- **Quantitative**: Power analysis (typically 80% power, α=0.05)
- **Qualitative**: Saturation (no new themes emerging)
- **Rule of thumb**: 30+ for central limit theorem

## Statistical Analysis

### Choosing the Right Test
| Data Type | Comparison | Test |
|-----------|------------|------|
| Continuous, 2 groups | Independent | t-test (or Mann-Whitney) |
| Continuous, 2+ groups | Independent | ANOVA (or Kruskal-Wallis) |
| Continuous, 2+ groups | Repeated | Repeated measures ANOVA |
| Categorical, 2 vars | Association | Chi-square |
| Continuous, 2 vars | Correlation | Pearson (or Spearman) |
| Continuous, DV | Prediction | Regression |

### Reporting Statistics
- Always report: test statistic, df, p-value, effect size
- Report means with SD or CI
- Use exact p-values (p=0.023, not p<0.05)
- Report effect sizes: Cohen's d, η², r, OR

### Assumptions to Check
- Normality (Shapiro-Wilk, Q-Q plots)
- Homogeneity of variance (Levene's test)
- Independence of observations
- Linearity (for regression)
- Multicollinearity (VIF < 5)

## Qualitative Methods

### Data Collection
- **Interviews**: Structured, semi-structured, unstructured
- **Focus groups**: 6-10 participants, guided discussion
- **Observations**: Participant, non-participant
- **Documents**: Texts, media, artifacts

### Analysis Approaches
- **Thematic analysis**: Identify patterns/themes
- **Grounded theory**: Build theory from data
- **Content analysis**: Systematic coding and counting
- **Discourse analysis**: Language and power
- **Phenomenology**: Lived experiences

### Trustworthiness
- **Credibility**: Member checking, triangulation
- **Transferability**: Thick description
- **Dependability**: Audit trail
- **Confirmability**: Reflexivity

## Mixed Methods
- **Convergent**: Collect both simultaneously, compare
- **Explanatory sequential**: Quant → Qual (explain results)
- **Exploratory sequential**: Qual → Quant (build instrument)
- **Embedded**: One method within the other
- **Transformative**: Framework-driven (e.g., feminist, critical)

## Ethical Considerations
- Informed consent (written, verbal, implied)
- Risk-benefit assessment
- Privacy and confidentiality
- Vulnerable populations (children, prisoners, etc.)
- Data protection (GDPR, HIPAA)
- Research integrity (fabrication, falsification, plagiarism)
""",
}

LITERATURE_REVIEW_SKILL = {
    "name": "literature-review",
    "description": "Systematic literature review methodology: PRISMA 2020, search strategy design, bibliometric analysis, gap identification, synthesis writing, scoping reviews, meta-analysis frameworks.",
    "tags": ["literature-review", "PRISMA", "systematic-review", "bibliometric", "meta-analysis"],
    "builtin_tools": ["search_papers", "search_web", "format_citation"],
    "prompt_template": """# Literature Review Skill

## Review Types
| Type | Purpose | Scope | Time |
|------|---------|-------|------|
| Narrative | Overview of topic | Broad | Flexible |
| Systematic | Answer specific question | Narrow, exhaustive | Months |
| Scoping | Map the evidence | Broad | Weeks-Months |
| Meta-analysis | Statistical synthesis | Narrow | Months |
| Umbrella | Overview of reviews | Very broad | Weeks |
| Rapid | Quick evidence check | Narrow | Days-Weeks |

## PRISMA 2020

### Flow Diagram
```
Identification:
  Records identified (databases: n=)
  Records identified (other sources: n=)
  ↓
  Duplicates removed (n=)
  ↓
Screening:
  Records screened (n=)
  Records excluded (n=)
  ↓
Eligibility:
  Reports sought for retrieval (n=)
  Reports not retrieved (n=)
  ↓
  Reports assessed for eligibility (n=)
  Reports excluded with reasons (n=)
  ↓
Included:
  Studies included in review (n=)
  Studies included in meta-analysis (n=)
```

### Checklist (27 items)
- Title (1), Abstract (2), Introduction (3-5), Methods (6-23), Results (24-26), Discussion (27)

## Search Strategy

### Databases
| Domain | Databases |
|--------|-----------|
| General | Google Scholar, Scopus, Web of Science |
| CS | IEEE Xplore, ACM DL, DBLP |
| Medicine | PubMed, MEDLINE, Cochrane |
| Social | ERIC, PsycINFO, JSTOR |
| Preprints | arXiv, SSRN, medRxiv |

### Query Construction
1. **PICO/PECO**: Population, Intervention/Exposure, Comparison, Outcome
2. **Boolean**: AND (narrow), OR (broaden), NOT (exclude)
3. **Truncation**: educat* (education, educational, educator)
4. **Phrase search**: "machine learning"
5. **Field tags**: TI=(title), AB=(abstract), KW=(keywords)

### Example Search String
```
(TI=("machine learning" OR "deep learning" OR "neural network")
AND TI=("education" OR "learning" OR "student")
AND AB=("outcome" OR "performance" OR "achievement"))
NOT TI=("review" OR "survey")
```

## Screening Process
1. **Title/Abstract screening**: 2 reviewers, independent
2. **Full-text screening**: Against inclusion/exclusion criteria
3. **Conflict resolution**: Third reviewer or discussion
4. **Pilot screening**: Test on 50 papers, refine criteria

## Data Extraction
| Field | Description |
|-------|-------------|
| Study ID | Author, year |
| Population | Sample size, demographics |
| Intervention | What was done |
| Comparison | Control/baseline |
| Outcome | Results, measures |
| Quality | Risk of bias score |

## Quality Assessment
- **Cochrane RoB 2**: For RCTs
- **ROBINS-I**: For non-randomized studies
- **Newcastle-Ottawa**: For observational studies
- **CASP**: For qualitative studies
- **JBI**: For mixed study types

## Synthesis

### Thematic Synthesis
1. Code findings from each study
2. Group codes into descriptive themes
3. Generate analytical themes

### Bibliometric Analysis
- Publication trends over time
- Geographic distribution
- Top authors and institutions
- Citation networks
- Keyword co-occurrence

### Meta-Analysis Concepts
- **Effect size**: Standardized mean difference (Cohen's d), odds ratio, risk ratio
- **Heterogeneity**: I² statistic (25% low, 50% moderate, 75% high)
- **Fixed vs random effects**: Fixed assumes one true effect, random allows variation
- **Forest plot**: Visual display of individual and pooled effects
- **Publication bias**: Funnel plot, Egger's test

## Gap Identification Framework
1. **Theoretical gaps**: Missing theory or framework
2. **Empirical gaps**: Unstudied populations, contexts
3. **Methodological gaps**: Weak designs, missing methods
4. **Practical gaps**: Research not applied
5. **Knowledge gaps**: Contradictory findings
""",
}

SCIENTIFIC_PRESENTATION_SKILL = {
    "name": "scientific-presentation",
    "description": "Scientific presentation design: conference talks, poster sessions, pitch decks for reviewers/investors, keynote structure, visual storytelling for technical audiences, demo preparation, slide design principles.",
    "tags": ["presentations", "slides", "posters", "conference", "demo"],
    "builtin_tools": [],
    "prompt_template": """# Scientific Presentation Skill

## Conference Talk (15-25 minutes)

### Structure
1. **Title slide** (5 sec): Title, authors, affiliations, date
2. **Motivation** (1-2 min): Why does this problem matter?
3. **Background** (2-3 min): Key concepts, prior work (be selective!)
4. **Problem statement** (1 min): Clear, specific problem
5. **Approach** (3-5 min): Your method (high-level, then key details)
6. **Results** (5-7 min): Key findings with clear visuals
7. **Discussion** (2-3 min): Implications, limitations
8. **Conclusion** (1 min): Take-home message
9. **Future work** (30 sec): What's next
10. **Thank you + Q&A** (5-7 min)

### Rules of Thumb
- **10-20-30 rule**: 10 slides, 20 minutes, 30pt minimum font
- **One idea per slide**: If you need to explain it, it's too complex
- **6×6 rule**: Max 6 lines, 6 words per line (or better: fewer)
- **Images > Text**: Use diagrams, charts, screenshots

## Slide Design Principles

### Visual Hierarchy
- **Title**: Largest, top of slide
- **Key point**: Prominent, left-aligned
- **Supporting details**: Smaller, indented
- **Source/citation**: Smallest, bottom

### Color
- **Background**: Dark (navy, charcoal) or white
- **Text**: High contrast (white on dark, black on light)
- **Accent**: 1-2 highlight colors for emphasis
- **Consistent**: Same color = same concept throughout
- **Accessible**: Check for color blindness (avoid red-green)

### Typography
- **Title**: 36-44pt, bold
- **Body**: 24-32pt, regular
- **Code/data**: 18-24pt, monospace
- **Font**: Sans-serif (Arial, Helvetica, Calibri)
- **Limit**: 2 fonts max

### Figures and Charts
- **Label axes**: Always, with units
- **Legend**: Clear, positioned well
- **Data-ink ratio**: Remove chartjunk
- **Color coding**: Consistent across slides
- **Resolution**: 300 DPI minimum

## Poster Presentation

### Layout (A0 portrait)
```
┌─────────────────────────────────┐
│           TITLE/AUTHORS         │
│           (10% height)          │
├───────────┬───────────┬─────────┤
│  INTRO    │  METHODS  │ RESULTS │
│  (20%)    │  (30%)    │ (30%)   │
│           │           │         │
├───────────┴───────────┴─────────┤
│  CONCLUSIONS + FUTURE WORK      │
│  (10% height)                   │
├─────────────────────────────────┤
│  REFERENCES + ACKNOWLEDGMENTS   │
│  (5% height)                    │
└─────────────────────────────────┘
```

### Poster Design Rules
- **Readable from 2 meters**: Title 72pt+, Body 24pt+
- **Flow**: Left-to-right, top-to-bottom
- **White space**: 30-40% of poster area
- **Figures**: At least 40% of content
- **QR code**: Link to paper/code/data

## Pitch Deck (10-12 slides)
For reviewers, investors, or stakeholders:

1. **Hook**: The problem in one compelling statement
2. **Problem**: Who has it? How bad is it?
3. **Solution**: What you're building/doing
4. **Market**: How big is the opportunity?
5. **Product**: Demo or screenshots
6. **Traction**: What have you achieved?
7. **Business model**: How does it make money/sustain?
8. **Competition**: Who else? Why are you better?
9. **Team**: Why can you execute?
10. **Ask**: What do you need? (funding, partners, etc.)
11. **Vision**: Where is this going long-term?

## Demo Preparation

### Checklist
- [ ] Demo script written and timed
- [ ] Backup plan if live demo fails (video, screenshots)
- [ ] Test on presentation machine (resolution, internet)
- [ ] Prepare sample data (don't use real sensitive data)
- [ ] Have terminal/command history ready
- [ ] Practice 3+ times

### Demo Structure
1. **Context** (30 sec): What are we showing?
2. **Setup** (30 sec): Environment, inputs
3. **Core demo** (3-5 min): The "wow" moment
4. **Edge cases** (1 min): Handle gracefully
5. **Conclusion** (30 sec): What did we learn?

## Delivery Techniques

### Speaking
- **Pace**: 120-150 words per minute
- **Pause**: After key points (2-3 seconds)
- **Volume**: Project to the back of the room
- **Eye contact**: 3-5 seconds per person/section
- **Gestures**: Open, purposeful, avoid fidgeting

### Q&A Handling
- **Listen fully**: Don't interrupt
- **Repeat the question**: For the audience
- **If you know**: Answer directly, then elaborate
- **If you don't know**: "That's a great question. I don't have the data to answer that, but here's what I think..."
- **If hostile**: Stay calm, acknowledge the concern, redirect to evidence

### Rehearsal Protocol
1. **Read through**: Get familiar with flow
2. **Stand and deliver**: Practice aloud, time yourself
3. **Record**: Watch yourself, note issues
4. **Present to colleague**: Get feedback
5. **Final run**: Full dress rehearsal
""",
}

DATA_MANAGEMENT_PLAN_SKILL = {
    "name": "data-management-plan",
    "description": "Data management planning: FAIR principles, DMP templates (Horizon Europe, NSF, UKRI), data governance, open data repositories, metadata standards, data lifecycle management, GDPR compliance for research data.",
    "tags": ["DMP", "FAIR", "data-management", "open-data", "GDPR"],
    "builtin_tools": ["search_web"],
    "prompt_template": """# Data Management Plan Skill

## FAIR Principles
| Principle | What It Means | How to Achieve |
|-----------|---------------|----------------|
| **F**indable | Data has persistent ID, rich metadata | DOI, metadata schema, indexed in catalog |
| **A**ccessible | Data can be accessed (possibly with auth) | Open repository, clear access conditions |
| **I**nteroperable | Data uses shared vocabularies/formats | Standard formats (CSV, JSON, HDF5), ontologies |
| **R**eusable | Data has clear license and provenance | CC-BY license, detailed README, version control |

## DMP Structure (Horizon Europe Template)

### 1. Data Summary
- What data will be collected/generated?
- What is the purpose?
- What is the expected volume?
- What formats will be used?

### 2. FAIR Data
- How will data be made findable? (metadata, PIDs)
- How will data be made accessible? (repository, access conditions)
- How will data be made interoperable? (standards, vocabularies)
- How will data be made reusable? (license, provenance, documentation)

### 3. Allocation of Resources
- Who is responsible for data management?
- What resources are needed? (storage, tools, personnel)
- What are the costs?

### 4. Data Security
- How will data be secured? (encryption, access control)
- How will sensitive data be handled?
- What are the backup procedures?

### 5. Ethical Aspects
- Does the data involve human participants?
- How will informed consent be obtained?
- How will privacy be protected?

### 6. Other Issues
- Are there legal restrictions? (IPR, patents)
- Are there ethical restrictions? (sensitive populations)

### 7. Feedback/Updates
- How will the DMP be updated as the project progresses?

## Funder-Specific Requirements

### Horizon Europe
- DMP required within 6 months of project start
- Update at mid-term and end of project
- Use the HE DMP template
- Research data: Open Access by default
- Exceptions: Legal, ethical, security, IPR

### NSF
- 2-page Data Management Plan (most directorates)
- Describe: Types, formats, policies, access, reuse, archival
- Some programs require data sharing (e.g., BIO, GEO)

### UKRI
- DMP required at application stage
- EPSRC: 10 principles for data management
- Data: "as open as possible, as closed as necessary"

## Data Repositories

### Generalist
- **Zenodo**: CERN-backed, DOI assignment, free
- **Figshare**: DOI, private/public, institutional
- **Dryad**: Curated, data publication, DOI
- **Mendeley Data**: Versioned, DOI, linked to papers
- **Harvard Dataverse**: Institutional, DOI, citation

### Discipline-Specific
- **arXiv**: Preprints (physics, CS, math, bio)
- **PDB**: Protein structures
- **GenBank**: Genetic sequences
- **ICPSR**: Social science data
- **LDC**: Linguistic data

## Metadata Standards
| Standard | Domain | Description |
|----------|--------|-------------|
| Dublin Core | General | 15 core elements (title, creator, date…) |
| DataCite | General | DOI metadata schema |
| DDI | Social sciences | Data documentation initiative |
| ISO 19115 | Geospatial | Geographic metadata |
| EML | Ecology | Ecological metadata language |
| FITS | Astronomy | Flexible image transport system |

## Data Lifecycle
```
Plan → Collect → Process → Analyze → Preserve → Share → Reuse
  ↑                                                        │
  └────────────────────────────────────────────────────────┘
```

## Retention & Archiving
- **Minimum retention**: 5-10 years after publication (funder-dependent)
- **Archive format**: Open, non-proprietary (CSV, JSON, HDF5)
- **Storage**: Redundant (3-2-1 rule: 3 copies, 2 media, 1 offsite)
- **Documentation**: README, codebook, data dictionary

## GDPR for Research Data
- **Lawful basis**: Consent, legitimate interest, public task
- **Data minimization**: Collect only what's needed
- **Purpose limitation**: Use only for stated purpose
- **Storage limitation**: Don't keep longer than needed
- **Rights**: Right to access, rectification, erasure (with exceptions for research)
- **DPIA**: Data Protection Impact Assessment for high-risk processing
- **Anonymization**: Remove or pseudonymize identifiers
- **Transfer**: Adequacy decisions, SCCs for international transfers
""",
}

IP_EXPLOITATION_SKILL = {
    "name": "ip-exploitation",
    "description": "Intellectual property and exploitation strategy: patent landscaping, licensing models, TRL advancement plans, commercialization roadmaps, spin-off creation, technology transfer, IP management in consortia, exploitation plans for funded projects.",
    "tags": ["IP", "patents", "licensing", "TRL", "commercialization", "spin-off"],
    "builtin_tools": ["search_web"],
    "prompt_template": """# IP & Exploitation Skill

## TRL Levels with Evidence
| TRL | Description | Evidence Required |
|-----|-------------|-------------------|
| 1 | Basic principles observed | Scientific publication |
| 2 | Technology concept formulated | Application paper, feasibility study |
| 3 | Experimental proof of concept | Lab demo, prototype |
| 4 | Technology validated in lab | Lab-scale demo, test results |
| 5 | Technology validated in relevant environment | Simulated environment demo |
| 6 | Technology demonstrated in relevant environment | Prototype in real conditions |
| 7 | System prototype demonstration | Operational demo |
| 8 | System complete and qualified | Testing, certification |
| 9 | System proven in operational environment | Commercial/military use |

## IP Types
| Type | Protection | Duration | What It Covers |
|------|------------|----------|----------------|
| Patent | Registration | 20 years | Inventions, processes |
| Copyright | Automatic | Life + 70 years | Software, documents, music |
| Trade secret | Secrecy | Unlimited | Formulas, algorithms, processes |
| Trademark | Registration | 10 years (renewable) | Brand names, logos |
| Design right | Registration | 15-25 years | Product appearance |
| Database right | Automatic | 15 years | Database structure/content |

## Patent Process
1. **Prior art search**: Is it novel? (Google Patents, Espacenet, USPTO)
2. **Patentability assessment**: Novel, inventive, industrial application
3. **Drafting**: Claims, description, drawings
4. **Filing**: National (UKIPO, USPTO, DPMA) or international (PCT)
5. **Examination**: Office actions, amendments
6. **Grant**: Publication, maintenance fees
7. **Enforcement**: Infringement monitoring, litigation

## Licensing Models
| Model | Description | When to Use |
|-------|-------------|-------------|
| Exclusive | One licensee, all rights | Strategic partner, high investment |
| Non-exclusive | Multiple licensees | Maximize adoption, standards |
| Sole | Licensor + one licensee | Balanced control |
| Field-of-use | Limited to specific application | Different markets |
| Territorial | Limited to geographic region | Regional partners |

## Open Source Licensing
| License | Permissions | Obligations | Use When |
|---------|------------|-------------|----------|
| MIT | Everything | Include notice | Max adoption |
| Apache 2.0 | Everything | Include notice, state changes | Patents included |
| GPL 3.0 | Everything | Share source of derivatives | Copyleft |
| LGPL 3.0 | Everything | Share source of library | Library linking |
| AGPL 3.0 | Everything | Share source (even SaaS) | Network copyleft |
| BSD 2/3 | Everything | Include notice | Similar to MIT |
| CC-BY | Everything | Attribution | Creative works |

### Dual Licensing
- Open source (GPL) + commercial license
- Users choose: free (with copyleft) or paid (without)
- Common for libraries and frameworks

## Commercialization Pathways
1. **License to existing company**: Royalty revenue, low risk
2. **Spin-off company**: Equity value, high risk/reward
3. **Joint venture**: Shared risk and reward
4. **Open source + services**: Support, consulting, customization
5. **Standards contribution**: Influence industry, FRAND licensing
6. **Publication only**: Academic impact, no commercial return

## Spin-Off Creation Roadmap
1. **Technology readiness**: TRL 4-6 minimum
2. **Market analysis**: TAM, SAM, SOM
3. **Business model**: Revenue streams, cost structure
4. **Team**: CEO, CTO, business development
5. **Funding**: Grants (EIC, SBIR), angels, VCs
6. **Legal entity**: Company incorporation, shareholder agreement
7. **IP assignment**: License or assign IP from university
8. **MVP**: Minimum viable product
9. **First customers**: Pilot users, design partners
10. **Scale**: Series A, growth

## Business Model Canvas
```
┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ Key Partners │ Key Activities│ Value Prop   │ Customer     │ Customer     │
│              │              │              │ Relationships│ Segments     │
│              │ Key Resources│              │              │              │
├──────────────┴──────────────┼──────────────┼──────────────┼──────────────┤
│ Cost Structure              │ Revenue Streams              │
└─────────────────────────────┴─────────────────────────────┘
```

## IP in Funded Projects (Horizon Europe)
- **Background IP**: Pre-existing, owned by originator
- **Foreground IP**: Created during project, owned by creator
- **Access rights**: Needed for implementation, granted on FRAND terms
- **Results ownership**: Creator (unless consortium agreement says otherwise)
- **Protection**: Owner must protect or inform consortium within 60 days
- **Exploitation**: Owner must exploit or transfer within 60 days of project end

## Consortium Agreement Provisions
1. IP ownership allocation
2. Access rights to background IP
3. Access rights to foreground IP
4. Licensing terms (FRAND, royalty-free)
5. Publication procedures (30-day review period)
6. Dispute resolution mechanism
7. Exit provisions

## Exploitation Plan Template
```markdown
# Exploitation Plan

## 1. Results Overview
| Result | Type | Owner | TRL | Market |
|--------|------|-------|-----|--------|
| [Name] | [SW/Service] | [Partner] | [X] | [Sector] |

## 2. Target Markets
- Primary market: [Sector, size, growth]
- Secondary market: [Sector, size, growth]
- Key customers: [Early adopters]

## 3. Exploitation Routes
| Result | Route | Timeline | Resources | Risk |
|--------|-------|----------|-----------|------|
| [Name] | [License/Spin-off] | [Q1 2025] | [€100K] | [Medium] |

## 4. IP Strategy
| Result | IP Type | Status | Protection | License |
|--------|---------|--------|------------|---------|
| [Name] | Patent | Filed | [Country] | [Type] |

## 5. Barriers and Mitigation
| Barrier | Impact | Mitigation |
|---------|--------|------------|
| [Barrier] | [H/M/L] | [Action] |

## 6. Sustainability
- How will exploitation continue after project ends?
- What funding is needed?
- What partnerships are needed?
```

## Technology Transfer Process
1. **Invention disclosure**: Researcher reports discovery
2. **Assessment**: TTO evaluates commercial potential
3. **IP protection**: Patent filing if appropriate
4. **Marketing**: Identify potential licensees
5. **Negotiation**: License terms, royalties
6. **Agreement**: Sign license, manage relationship
7. **Revenue sharing**: Typically 1/3 inventor, 1/3 dept, 1/3 university
""",
}

RESEARCH_IDEATION_SKILL = {
    "name": "research-ideation",
    "description": "Research ideation and hypothesis generation: gap analysis, novelty assessment, research direction synthesis, idea scoring, cross-domain inspiration, systematic opportunity identification.",
    "tags": ["research", "ideation", "hypothesis", "gap-analysis", "novelty", "innovation"],
    "builtin_tools": ["search_papers", "search_web"],
    "prompt_template": """## Research Ideation & Hypothesis Generation

### Systematic Ideation Framework

#### Phase 1: Landscape Mapping
- Survey current state-of-the-art in target domain
- Identify active research fronts and trending topics
- Map key players, groups, and their recent directions
- Catalog recent breakthroughs and their enabling conditions

#### Phase 2: Gap Identification
- **Contradiction gaps**: Conflicting findings across papers
- **Methodology gaps**: Problems no existing method adequately solves
- **Application gaps**: Techniques from one domain untested in another
- **Scale gaps**: Approaches that work small but don't scale
- **Temporal gaps**: Old problems with new enabling technology
- **Negative results**: Important findings nobody published

#### Phase 3: Hypothesis Generation
For each identified gap, generate hypotheses using:
- **Analogical reasoning**: How was a similar problem solved elsewhere?
- **Inversion**: What if the opposite of common assumption is true?
- **Combination**: What if we merge approach A with approach B?
- **Generalization**: Does this specific finding hold more broadly?
- **Specialization**: Can this general method be specialized for a niche?

#### Phase 4: Idea Scoring (1-10 each dimension)
| Dimension | Questions to Ask |
|-----------|-----------------|
| **Novelty** | Has this been done? How different from existing work? |
| **Feasibility** | Can this be done with available resources in 6-12 months? |
| **Impact** | Who cares? How many researchers/practitioners benefit? |
| **Timeliness** | Why now? What enabling technology makes this possible today? |
| **Clarity** | Can you state the contribution in one sentence? |
| **Verifiability** | Can results be clearly measured and compared to baselines? |

#### Phase 5: Research Direction Synthesis
For top-scored ideas, produce:
- **Research question**: Single clear question the work answers
- **Hypothesis**: Testable statement of expected outcome
- **Approach sketch**: 3-5 step methodology outline
- **Required resources**: Data, compute, expertise, collaborators
- **Risk assessment**: What could go wrong, mitigation strategies
- **Expected contribution**: What the community gains

### Cross-Domain Inspiration Techniques
1. **Bibliographic coupling**: Find papers cited together across fields
2. **Concept transplantation**: Take a concept from field A, apply to field B
3. **Tool reuse**: Existing tool from one domain solving different problem
4. **Problem reframing**: Describe your problem using another field's vocabulary
5. **Adversarial collaboration**: What would a critic of your field suggest?

### Common Ideation Anti-Patterns
- **Solution looking for a problem**: Start with the problem, not the method
- **Incremental trap**: Only extending last year's paper by 2%
- **Buzzword chasing**: Using trendy terms without substance
- **Confirmation bias**: Only reading papers that support your idea
- **Scope creep**: Idea that needs 5 years and 20 people

### Literature-Driven Ideation Checklist
- [ ] Read last 3 years of target venue's best papers
- [ ] Check survey papers for identified open problems
- [ ] Review "future work" sections of top papers in area
- [ ] Look at rejected paper topics (if available via preprint servers)
- [ ] Check industry blog posts for unsolved problems
- [ ] Review dataset papers — new benchmarks enable new research
- [ ] Look at challenge/shared task reports for remaining difficulties
""",
}

CITATION_VERIFICATION_SKILL = {
    "name": "citation-verification",
    "description": "Academic citation verification and claim validation: extract claims from papers, verify cited sources exist and support the claims, detect misrepresentation, check reference accuracy, validate statistical claims.",
    "tags": ["citations", "verification", "fact-checking", "claims", "evidence", "integrity"],
    "builtin_tools": ["search_papers", "read_document"],
    "prompt_template": """## Citation Verification & Claim Validation

### Verification Pipeline

#### Stage 1: Claim Extraction
For each paragraph in the paper:
1. Identify factual claims (not opinions or framing)
2. Classify claim type:
   - **Empirical**: "We achieved X% accuracy on dataset Y"
   - **Attribution**: "Smith et al. showed that..."
   - **Methodological**: "This approach works because..."
   - **Comparative**: "Our method outperforms..."
   - **Statistical**: "p < 0.05", "95% CI [X, Y]"
3. Link each claim to its supporting citation(s)
4. Flag unsupported claims (no citation for factual assertion)

#### Stage 2: Citation Existence Check
For each cited reference:
- [ ] Verify the paper exists in academic databases
- [ ] Confirm author names match
- [ ] Confirm title matches (accounting for minor variations)
- [ ] Confirm year of publication is correct
- [ ] Check venue/journal is correct
- [ ] Verify DOI or identifier if provided
- Detect: fabricated references, ghost citations, incorrect years

#### Stage 3: Claim-Citation Alignment
For each claim-citation pair:
1. Read the cited source (or its abstract if full text unavailable)
2. Does the source actually say what the citing paper claims?
3. Classification:
   - **Supported**: Source clearly states or strongly implies the claim
   - **Partially supported**: Source says something related but not exactly the claim
   - **Unsupported**: Source does not address the claim
   - **Contradicted**: Source says the opposite
   - **Overclaimed**: Source says it with caveats/limitations omitted in citing paper

#### Stage 4: Statistical Claim Verification
For statistical claims:
- [ ] Sample size reported and adequate
- [ ] Statistical test appropriate for the design
- [ ] p-values reported correctly (not p < 0.05 when p = 0.048)
- [ ] Confidence intervals consistent with p-values
- [ ] Effect sizes reported (not just significance)
- [ ] Multiple comparisons corrected for
- [ ] Baseline comparisons fair (same data, same preprocessing)

#### Stage 5: Reference Quality Assessment
| Quality Indicator | Check |
|-------------------|-------|
| **Recency** | Are citations current? >50% should be <5 years old |
| **Venue quality** | Are top venues represented? Not just predatory journals |
| **Self-citation rate** | <20% self-citation is typical |
| **Citation diversity** | Not all from same group/institution |
| **Primary sources** | Citing original work, not surveys for factual claims |

### Common Citation Problems
- **Telephone game**: Citing paper C for what paper A originally showed
- **Laundering**: Citations through surveys instead of primary sources
- **Copy-paste errors**: References copied from other papers without checking
- **Strategic citation**: Citing friends/reviewers regardless of relevance
- **Negative result omission**: Not citing papers that contradict the claim

### Verification Output Format
```markdown
## Citation Verification Report

### Summary Statistics
- Total claims extracted: N
- Claims with citations: N
- Unsupported claims: N
- Verified citations: N/N
- Problematic citations: N

### Issues Found

#### Critical Issues
1. [Claim]: "..."
   - Problem: [fabricated reference / misrepresented source / unsupported]
   - Evidence: [what the source actually says]

#### Warnings
1. [Claim]: "..."
   - Problem: [weak support / outdated reference / self-citation heavy]
   - Recommendation: [what to do]

### Verification Score
- Claim support rate: X%
- Citation accuracy: X%
- Statistical rigor: X%
- Overall citation quality: [High/Medium/Low]
```
""",
}

REPRODUCIBILITY_ASSESSMENT_SKILL = {
    "name": "reproducibility-assessment",
    "description": "Assess research reproducibility: workflow reconstruction, methodology verification, code/data availability, computational reproducibility, reporting completeness, open science compliance.",
    "tags": ["reproducibility", "replication", "transparency", "open-science", "methodology", "verification"],
    "builtin_tools": ["read_document", "search_papers"],
    "prompt_template": """## Reproducibility Assessment

### Reproducibility Dimensions

#### 1. Methodological Reproducibility
Can another researcher follow the methods and get equivalent results?

**Checklist:**
- [ ] Research question/hypothesis clearly stated
- [ ] Study design fully described (participants, materials, procedure)
- [ ] Inclusion/exclusion criteria specified
- [ ] Sample size justification provided (power analysis)
- [ ] Randomization procedure described (if applicable)
- [ ] Blinding/masking described (if applicable)
- [ ] All measurements defined with precision
- [ ] Statistical analysis plan specified (ideally pre-registered)

#### 2. Computational Reproducibility
Can the code produce the same results given the same data?

**Checklist:**
- [ ] Code available (GitHub, Zenodo, institutional repo)
- [ ] Code license specified
- [ ] README with setup instructions
- [ ] Dependencies listed with versions (requirements.txt, environment.yml)
- [ ] Random seeds set for all stochastic processes
- [ ] Data processing pipeline documented
- [ ] Hyperparameters specified (not just "default")
- [ ] Hardware requirements noted (GPU, RAM)
- [ ] Expected runtime documented

#### 3. Data Reproducibility
Can the data be accessed and understood?

**Checklist:**
- [ ] Data available (repository, supplement, upon request)
- [ ] Data format documented
- [ ] Variable names and meanings explained
- [ ] Units specified for all measurements
- [ ] Missing data handling explained
- [ ] Data preprocessing steps documented
- [ ] Codebook/data dictionary provided
- [ ] License for data reuse specified
- [ ] DOI or persistent identifier assigned

#### 4. Results Reproducibility
Would independent researchers reach the same conclusions?

**Checklist:**
- [ ] All results reported (including non-significant)
- [ ] Figures match text descriptions
- [ ] Tables internally consistent
- [ ] Error bars/confidence intervals reported
- [ ] Number of independent runs reported
- [ ] Variability across runs reported
- [ ] Ablation studies provided
- [ ] Sensitivity analysis performed
- [ ] Robustness checks included

### Reproducibility Scoring

| Level | Criteria | Score |
|-------|----------|-------|
| **Gold** | Code + data + environment + seeds + pre-registration | 5 |
| **Silver** | Code + data + seeds, no pre-registration | 4 |
| **Bronze** | Code available but incomplete documentation | 3 |
| **Tin** | Data available but no code | 2 |
| **Paper** | Claims reproducibility but nothing shared | 1 |
| **None** | No reproducibility measures | 0 |

### Assessment Output Format
```markdown
## Reproducibility Assessment Report

### Overall Score: [X/5] — [Gold/Silver/Bronze/Tin/Paper/None]

### Methodological Reproducibility: [Pass/Partial/Fail]
- [strengths and issues]

### Computational Reproducibility: [Pass/Partial/Fail]
- Code availability: [Yes/No/Partial]
- Environment specification: [Complete/Missing]
- Random seeds: [Set/Not set]
- [issues]

### Data Reproducibility: [Pass/Partial/Fail]
- Data availability: [Yes/No/Partial]
- Documentation: [Complete/Missing]
- [issues]

### Results Reproducibility: [Pass/Partial/Fail]
- [strengths and issues]

### Barriers to Reproduction
1. [Specific barrier] — [How to fix]
2. ...

### Recommendations
1. [Actionable recommendation with priority]
2. ...
```

### Red Flags for Non-Reproducibility
- "Results may vary due to random initialization" without setting seeds
- "Available upon request" (often means unavailable)
- Proprietary datasets with no alternative
- Custom hardware or lab equipment with no specifications
- Undocumented preprocessing or postprocessing steps
- Selective reporting (only best run, cherry-picked examples)
- Hyperparameters tuned on test set
- Data leakage between train/test

### Computational Environment Documentation
Essential elements for reproducible computational work:
```
## Environment
- OS: [e.g., Ubuntu 22.04]
- Python: [e.g., 3.11.5]
- CUDA: [e.g., 12.1]
- GPU: [e.g., NVIDIA A100 80GB]
- RAM: [e.g., 128GB]
- Key libraries: [name==version]
```

### Pre-Registration Best Practices
- Register before data collection begins
- Include: hypotheses, sample size, analysis plan, stopping rules
- Platforms: OSF, AsPredicted, ClinicalTrials.gov
- Distinguish confirmatory from exploratory analyses
- Report deviations from registered plan with justification
""",
}


# ─────────────────────────────────────────────────────────────────────────────
# ALL SKILLS LIST
# ─────────────────────────────────────────────────────────────────────────────

NIOBE_SKILLS = [
    ACADEMIC_WRITING_SKILL,
    ACADEMIC_PAPER_REVIEW_SKILL,
    EU_HORIZON_SKILL,
    GRANT_WRITING_SKILL,
    DELIVERABLE_WRITING_SKILL,
    PROJECT_MANAGEMENT_SKILL,
    TECHNICAL_LEAD_SKILL,
    RESEARCH_METHODOLOGY_SKILL,
    LITERATURE_REVIEW_SKILL,
    SCIENTIFIC_PRESENTATION_SKILL,
    DATA_MANAGEMENT_PLAN_SKILL,
    IP_EXPLOITATION_SKILL,
    RESEARCH_IDEATION_SKILL,
    CITATION_VERIFICATION_SKILL,
    REPRODUCIBILITY_ASSESSMENT_SKILL,
]


# ─────────────────────────────────────────────────────────────────────────────
# AGENT CONFIGS
# ─────────────────────────────────────────────────────────────────────────────

SCHOLAR_CONFIG = {
    "name": "Scholar",
    "role": "researcher",
    "provider": "opencode",
    "model": "deepseek-v4-flash",
    "temperature": 0.3,
    "max_tokens": 8192,
    "strategy": "direct",
    "system_prompt": (
        "You are a Scholar — the academic discovery specialist.\n\n"
        "YOUR ROLE: Find papers, identify research gaps, verify claims, evaluate methodology.\n"
        "You do NOT write papers, review papers, or manage projects.\n\n"
        "Skills and how you use them:\n"
        "- literature-review: Search across Semantic Scholar, arXiv, CrossRef. Synthesize\n"
        "  findings into coherent literature reviews. Identify seminal works and research fronts.\n"
        "- research-ideation: Identify gaps in existing literature. Generate research hypotheses.\n"
        "  Score ideas on novelty, feasibility, and impact.\n"
        "- citation-verification: Verify citations against source papers. Validate claims.\n"
        "  Check statistical claims and evidence grounding.\n"
        "- research-methodology: Evaluate experimental design quality. Assess statistical rigor.\n"
        "  Check sampling strategies and validity types.\n\n"
        "When searching:\n"
        "- Use multiple sources for comprehensive coverage\n"
        "- Evaluate citation counts, recency, and venue quality\n"
        "- Summarize key findings and methodological approaches\n"
        "- Identify connections between papers and research themes\n"
        "- Flag potential gaps in the literature"
    ),
    "is_default": False,
}

ACADEMIC_WRITER_CONFIG = {
    "name": "Academic Writer",
    "role": "writer",
    "provider": "opencode",
    "model": "deepseek-v4-flash",
    "temperature": 0.3,
    "max_tokens": 12000,
    "strategy": "reflection",
    "system_prompt": (
        "You are an Academic Writer — the content creation specialist.\n\n"
        "YOUR ROLE: Write papers, abstracts, presentations. Generate research ideas.\n"
        "You do NOT review papers, design experiments, or manage grants.\n\n"
        "Skills and how you use them:\n"
        "- academic-writing: Write papers following IMRaD structure. Craft abstracts.\n"
        "  Format for IEEE, ACM, Springer, Elsevier. Write cover letters, rebuttals,\n"
        "  camera-ready responses.\n"
        "- scientific-presentation: Create conference talks, poster presentations,\n"
        "  pitch decks. Design slides with visual hierarchy.\n"
        "- research-ideation: Generate research hypotheses and identify gaps for new\n"
        "  papers. Score ideas on novelty, feasibility, and impact.\n\n"
        "When writing:\n"
        "- Start with a clear thesis or research question\n"
        "- Support claims with evidence and citations\n"
        "- Use transitions to maintain logical flow\n"
        "- Adapt tone and format to target venue\n"
        "- Conclude with implications and future work"
    ),
    "is_default": False,
}

PAPER_REVIEWER_CONFIG = {
    "name": "Paper Reviewer",
    "role": "reviewer",
    "provider": "opencode",
    "model": "deepseek-v4-flash",
    "temperature": 0.1,
    "max_tokens": 16000,
    "strategy": "critique",
    "system_prompt": (
        "You are a Paper Reviewer — the evaluation specialist.\n\n"
        "YOUR ROLE: Review papers, check reproducibility, evaluate EU proposals.\n"
        "You do NOT write papers, design experiments, or manage projects.\n\n"
        "Your 7-stage review process:\n"
        "1. INTAKE: Extract structured data from paper\n"
        "2. STRUCTURAL ANALYSIS: Check IMRaD completeness, figure quality\n"
        "3. CLAIM EXTRACTION: Build claim-evidence ledger\n"
        "4. LITERATURE GROUNDING: Search related work, assess novelty\n"
        "5. METHODOLOGY VERIFICATION: Check statistical rigor, reproducibility\n"
        "6. ADVERSARIAL RED TEAM: Find logical flaws, missing experiments\n"
        "7. SYNTHESIS: Merge outputs, calibrate to venue rubric\n\n"
        "Skills and how you use them:\n"
        "- academic-paper-review: Execute the 7-stage pipeline. Produce\n"
        "  review-summary.md and response-to-authors.md.\n"
        "- reproducibility-assessment: Check code/data availability, workflow\n"
        "  reconstruction, computational reproducibility.\n"
        "- eu-horizon: Evaluate proposals against EU Horizon Europe criteria\n"
        "  (Excellence, Impact, Implementation). Check compliance.\n\n"
        "Output documents:\n"
        "- review-summary.md: Detailed technical review\n"
        "- response-to-authors.md: Constructive feedback for authors"
    ),
    "is_default": False,
}

GRANT_WRITER_CONFIG = {
    "name": "Grant Writer",
    "role": "writer",
    "provider": "opencode",
    "model": "deepseek-v4-flash",
    "temperature": 0.2,
    "max_tokens": 12000,
    "strategy": "reflection",
    "system_prompt": (
        "You are a Grant Writer — the proposal and reporting specialist.\n\n"
        "YOUR ROLE: Write proposals, deliverables, DMPs. Handle EU/NSF/NIH funding.\n"
        "You do NOT review papers, design experiments, or manage projects.\n\n"
        "Skills and how you use them:\n"
        "- grant-writing: Write proposals for NSF (CAREER, EAGER), NIH (R01, R21),\n"
        "  ERC (StG, CoG, AdG). Structure: Specific Aims, Research Plan, Budget.\n"
        "- eu-horizon: Write EU Horizon Europe proposals (RIA, IA, CSA). Handle\n"
        "  evaluation criteria, Part B structure, budget rules, WP conventions.\n"
        "- deliverable-writing: Write EU deliverables (R, DEM, DEC, DATA, ETHICS).\n"
        "  Handle periodic/final reports, KPI tracking, D&E plans.\n"
        "- data-management-plan: Write DMPs following FAIR principles. Handle\n"
        "  GDPR compliance, Open Science requirements.\n\n"
        "When writing proposals:\n"
        "- Align with evaluation criteria (Excellence, Impact, Implementation)\n"
        "- Consider reviewer psychology and common rejection reasons\n"
        "- Build convincing budgets with clear justification"
    ),
    "is_default": False,
}

RESEARCH_METHODOLOGIST_CONFIG = {
    "name": "Research Methodologist",
    "role": "researcher",
    "provider": "opencode",
    "model": "deepseek-v4-flash",
    "temperature": 0.1,
    "max_tokens": 10000,
    "strategy": "direct",
    "system_prompt": (
        "You are a Research Methodologist — the experiment design specialist.\n\n"
        "YOUR ROLE: Design experiments, plan data management, ground in prior work.\n"
        "You do NOT write papers, review papers, or manage grants.\n\n"
        "Skills and how you use them:\n"
        "- research-methodology: Design experiments (between/within/factorial).\n"
        "  Formulate hypotheses. Choose statistical tests. Plan sampling.\n"
        "  Handle qualitative, quantitative, and mixed methods.\n"
        "- data-management-plan: Design FAIR data management plans. Handle GDPR\n"
        "  compliance. Plan data lifecycle (collection, storage, sharing, archiving).\n"
        "- literature-review: Ground experimental designs in prior work. Use\n"
        "  PRISMA methodology for systematic reviews. Identify methodological gaps.\n\n"
        "When advising:\n"
        "- Match methodology to research questions\n"
        "- Consider practical constraints (time, budget, access)\n"
        "- Ensure ethical compliance\n"
        "- Plan for reproducibility and transparency"
    ),
    "is_default": False,
}

PROJECT_MANAGER_CONFIG = {
    "name": "Project Manager",
    "role": "researcher",
    "provider": "opencode",
    "model": "deepseek-v4-flash",
    "temperature": 0.2,
    "max_tokens": 10000,
    "strategy": "direct",
    "system_prompt": (
        "You are a Project Manager — the research leadership specialist.\n\n"
        "YOUR ROLE: Lead projects, track deliverables, manage IP, ensure EU compliance.\n"
        "You do NOT write papers, review papers, or design experiments.\n\n"
        "Skills and how you use them:\n"
        "- project-management: Create WBS, Gantt charts, RACI matrices. Handle\n"
        "  Agile/Scrum/Kanban. Manage risks, stakeholders, scope changes.\n"
        "- technical-lead: Write ADRs. Review code (feedback tiers). Manage tech debt.\n"
        "  Design systems. Handle incidents (SEV levels, post-mortems).\n"
        "- ip-exploitation: Assess TRL levels. Plan IP protection (patents, trade secrets).\n"
        "  Choose licensing models. Plan commercialization and spin-offs.\n"
        "- eu-horizon: Handle EU project structure, WP conventions, periodic reporting,\n"
        "  KPI tracking, consortium coordination.\n\n"
        "When managing:\n"
        "- Balance scope, time, and resources\n"
        "- Communicate clearly with all stakeholders\n"
        "- Document decisions and rationale\n"
        "- Ensure EU compliance and reporting"
    ),
    "is_default": False,
}

SPECIALIZED_AGENT_CONFIGS = [
    SCHOLAR_CONFIG,
    ACADEMIC_WRITER_CONFIG,
    PAPER_REVIEWER_CONFIG,
    GRANT_WRITER_CONFIG,
    RESEARCH_METHODOLOGIST_CONFIG,
    PROJECT_MANAGER_CONFIG,
]


# ─────────────────────────────────────────────────────────────────────────────
# SKILL MAPPINGS FOR SPECIALIZED CONFIGS
# ─────────────────────────────────────────────────────────────────────────────

def get_skills_for_config(config_name: str, all_skills: list[Skill]) -> list[Skill]:
    skill_map = {
        "Scholar": ["literature-review", "research-ideation", "citation-verification", "research-methodology"],
        "Academic Writer": ["academic-writing", "scientific-presentation", "research-ideation"],
        "Paper Reviewer": ["academic-paper-review", "reproducibility-assessment", "eu-horizon"],
        "Grant Writer": ["grant-writing", "eu-horizon", "deliverable-writing", "data-management-plan"],
        "Research Methodologist": ["research-methodology", "data-management-plan", "literature-review"],
        "Project Manager": ["project-management", "technical-lead", "ip-exploitation", "eu-horizon"],
    }
    target_names = skill_map.get(config_name, [])
    return [s for s in all_skills if s.name in target_names]


# ─────────────────────────────────────────────────────────────────────────────
# SEED FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

async def seed_niobe_skills(db: AsyncSession, user_id: str) -> list[Skill]:
    """Insert all 15 Niobe skills into the database.

    If a skill with the same name already exists for this user, skip it.
    Returns list of created Skill objects.
    """
    created = []
    for skill_data in NIOBE_SKILLS:
        result = await db.execute(
            select(Skill).where(
                Skill.user_id == user_id,
                Skill.name == skill_data["name"],
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            created.append(existing)
            continue

        skill = Skill(
            user_id=user_id,
            name=skill_data["name"],
            description=skill_data["description"],
            prompt_template=skill_data["prompt_template"],
            builtin_tools=skill_data.get("builtin_tools", []),
            custom_tools=[],
            input_schema=None,
            output_schema=None,
            tags=skill_data.get("tags", []),
            is_public=True,
        )
        db.add(skill)
        created.append(skill)

    await db.commit()
    for skill in created:
        await db.refresh(skill)
    return created


async def seed_specialized_agents(db: AsyncSession, user_id: str, all_skills: list[Skill]) -> list[AgentConfig]:
    """Create specialized Niobe-based agent configs with appropriate skill subsets."""
    created = []
    for config_data in SPECIALIZED_AGENT_CONFIGS:
        result = await db.execute(
            select(AgentConfig)
            .options(selectinload(AgentConfig.skills))
            .where(
                AgentConfig.user_id == user_id,
                AgentConfig.name == config_data["name"],
            )
        )
        existing = result.scalar_one_or_none()

        config_skills = get_skills_for_config(config_data["name"], all_skills)

        if existing:
            for key, value in config_data.items():
                setattr(existing, key, value)
            existing.skills = config_skills
            await db.commit()
            await db.refresh(existing)
            created.append(existing)
            continue

        config = AgentConfig(user_id=user_id, **config_data)
        config.skills = config_skills
        db.add(config)
        created.append(config)

    await db.commit()
    for config in created:
        await db.refresh(config)
    return created


async def seed_all(db: AsyncSession, user_id: str) -> dict:
    skills = await seed_niobe_skills(db, user_id)
    specialized_configs = await seed_specialized_agents(db, user_id, skills)
    return {
        "skills_created": len(skills),
        "skill_ids": [str(s.id) for s in skills],
        "agent_configs": [
            {"id": str(c.id), "name": c.name, "skills": len(c.skills)} for c in specialized_configs
        ],
    }
