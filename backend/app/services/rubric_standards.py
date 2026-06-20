"""
Rubric standards for manuscript rating.

Each standard defines weighted criteria for evaluating academic papers.
Standards are based on established peer review guidelines from major publishers.
"""

from dataclasses import dataclass, field


@dataclass
class RubricCriterion:
    """A single criterion in a rubric standard."""
    name: str
    weight: float  # 0.0 to 1.0, sum of all weights = 1.0
    description: str
    anchors: dict[str, str]  # score_range -> description


@dataclass
class RubricStandard:
    """A complete rubric standard with weighted criteria."""
    id: str
    name: str
    description: str
    publisher: str
    criteria: list[RubricCriterion] = field(default_factory=list)

    @property
    def total_weight(self) -> float:
        return sum(c.weight for c in self.criteria)



IEEE = RubricStandard(
    id="ieee",
    name="IEEE",
    description="Institute of Electrical and Electronics Engineers — standard for CS/Engineering papers",
    publisher="IEEE",
    criteria=[
        RubricCriterion(
            name="Technical Soundness",
            weight=0.25,
            description="Methodology rigor, correctness of analysis, experimental design, reproducibility",
            anchors={
                "1-20": "Major technical flaws, incorrect methodology, results unreliable",
                "21-40": "Several technical issues, limited experimental validation",
                "41-60": "Adequate methodology, results support most claims",
                "61-80": "Rigorous approach, comprehensive experiments, results reliable",
                "81-100": "Flawless methodology, extensive validation, results definitive",
            },
        ),
        RubricCriterion(
            name="Originality & Novelty",
            weight=0.15,
            description="Novel contributions, fresh perspective, advancement of state-of-the-art",
            anchors={
                "1-20": "Incremental work, no novelty, duplicates existing results",
                "21-40": "Minor extension of existing work, limited new insights",
                "41-60": "Meaningful contribution, advances the field moderately",
                "61-80": "Significant novelty, opens new research directions",
                "81-100": "Groundbreaking contribution, fundamentally advances the field",
            },
        ),
        RubricCriterion(
            name="Significance & Impact",
            weight=0.15,
            description="Potential impact on the field, practical implications, theoretical advances",
            anchors={
                "1-20": "Niche interest, minimal impact on the field",
                "21-40": "Limited impact, addresses a narrow problem",
                "41-60": "Moderate significance, useful to a subcommunity",
                "61-80": "High significance, broad impact potential",
                "81-100": "Transformative impact, reshapes the field",
            },
        ),
        RubricCriterion(
            name="Clarity of Presentation",
            weight=0.15,
            description="Writing quality, figure/table quality, logical flow, readability",
            anchors={
                "1-20": "Confusing, poorly organized, many errors",
                "21-40": "Unclear in places, some structural issues",
                "41-60": "Clear and understandable, adequate organization",
                "61-80": "Excellent writing, well-structured, high-quality figures",
                "81-100": "Exemplary clarity, publication-ready, figures outstanding",
            },
        ),
        RubricCriterion(
            name="Literature Grounding",
            weight=0.15,
            description="Related work coverage, citation quality, positioning in the field",
            anchors={
                "1-20": "Poor coverage, missing key references, no positioning",
                "21-40": "Partial coverage, some important works missing",
                "41-60": "Adequate coverage, most relevant works cited",
                "61-80": "Comprehensive review, excellent positioning",
                "81-100": "Exhaustive review, perfect contextualization",
            },
        ),
        RubricCriterion(
            name="Reproducibility",
            weight=0.10,
            description="Dataset availability, code availability, experimental setup clarity",
            anchors={
                "1-20": "Impossible to reproduce, no details provided",
                "21-40": "Difficult to reproduce, missing key details",
                "41-60": "Reproducible with effort, most details provided",
                "61-80": "Straightforward to reproduce, good documentation",
                "81-100": "Fully reproducible, code/data publicly available",
            },
        ),
        RubricCriterion(
            name="Ethics & Compliance",
            weight=0.05,
            description="Ethical considerations, IRB approval, consent, conflicts of interest",
            anchors={
                "1-20": "Serious ethical concerns, no compliance",
                "21-40": "Minor ethical issues, incomplete compliance",
                "41-60": "Adequate ethical standards, basic compliance",
                "61-80": "Good ethical practices, full compliance",
                "81-100": "Exemplary ethics, exceeds requirements",
            },
        ),
    ],
)



ACM = RubricStandard(
    id="acm",
    name="ACM",
    description="Association for Computing Machinery — emphasis on software and systems",
    publisher="ACM",
    criteria=[
        RubricCriterion(
            name="Technical Soundness",
            weight=0.20,
            description="System design, implementation correctness, evaluation rigor",
            anchors={
                "1-20": "Fundamental design flaws, incorrect implementation",
                "21-40": "Several issues, limited evaluation",
                "41-60": "Sound design, adequate evaluation",
                "61-80": "Rigorous design and evaluation",
                "81-100": "Exemplary engineering, comprehensive validation",
            },
        ),
        RubricCriterion(
            name="Originality & Novelty",
            weight=0.15,
            description="Novel techniques, fresh approaches, creative solutions",
            anchors={
                "1-20": "Existing technique applied without changes",
                "21-40": "Minor modifications to existing work",
                "41-60": "Novel approach to known problem",
                "61-80": "Significant innovation, new paradigm",
                "81-100": "Breakthrough contribution",
            },
        ),
        RubricCriterion(
            name="Significance & Impact",
            weight=0.15,
            description="Practical utility, adoption potential, community impact",
            anchors={
                "1-20": "No practical value",
                "21-40": "Limited applicability",
                "41-60": "Useful for specific scenarios",
                "61-80": "Broad practical impact",
                "81-100": "Transformative for the community",
            },
        ),
        RubricCriterion(
            name="Clarity of Presentation",
            weight=0.15,
            description="Documentation quality, code readability, artifact availability",
            anchors={
                "1-20": "Poorly documented, unreadable code",
                "21-40": "Partial documentation",
                "41-60": "Adequate documentation",
                "61-80": "Excellent documentation and artifacts",
                "81-100": "Exemplary, production-quality artifacts",
            },
        ),
        RubricCriterion(
            name="Literature Grounding",
            weight=0.15,
            description="Related systems comparison, baselines used, positioning",
            anchors={
                "1-20": "No comparison with existing systems",
                "21-40": "Minimal comparison",
                "41-60": "Adequate comparison with baselines",
                "61-80": "Comprehensive comparison",
                "81-100": "Exhaustive positioning",
            },
        ),
        RubricCriterion(
            name="Reproducibility",
            weight=0.15,
            description="Open-source code, Docker/container support, dataset availability, README quality",
            anchors={
                "1-20": "No artifacts, impossible to reproduce",
                "21-40": "Partial artifacts, difficult to reproduce",
                "41-60": "Artifacts available, reproducible with effort",
                "61-80": "Well-documented artifacts, easy to reproduce",
                "81-100": "Full open-source with CI/CD, one-click reproduce",
            },
        ),
        RubricCriterion(
            name="Ethics & Compliance",
            weight=0.05,
            description="Data privacy, user consent, responsible disclosure",
            anchors={
                "1-20": "Serious ethical concerns",
                "21-40": "Minor issues",
                "41-60": "Adequate",
                "61-80": "Good practices",
                "81-100": "Exemplary",
            },
        ),
    ],
)



NATURE = RubricStandard(
    id="nature",
    name="Nature/Science",
    description="High-impact general science — emphasis on significance and broad interest",
    publisher="Nature/Science",
    criteria=[
        RubricCriterion(
            name="Technical Soundness",
            weight=0.20,
            description="Methodology rigor, data quality, statistical analysis",
            anchors={
                "1-20": "Fundamental flaws",
                "21-40": "Several issues",
                "41-60": "Adequate",
                "61-80": "Rigorous",
                "81-100": "Flawless",
            },
        ),
        RubricCriterion(
            name="Originality & Novelty",
            weight=0.15,
            description="Novel findings, paradigm shifts, new discoveries",
            anchors={
                "1-20": "Known results",
                "21-40": "Minor extensions",
                "41-60": "New findings",
                "61-80": "Significant discoveries",
                "81-100": "Paradigm-shifting",
            },
        ),
        RubricCriterion(
            name="Significance & Impact",
            weight=0.25,
            description="Broad scientific impact, cross-disciplinary interest, societal relevance",
            anchors={
                "1-20": "Niche interest",
                "21-40": "Limited audience",
                "41-60": "Moderate interest",
                "61-80": "High interest, broad impact",
                "81-100": "Transformative, front-page potential",
            },
        ),
        RubricCriterion(
            name="Clarity of Presentation",
            weight=0.10,
            description="Writing quality, figure clarity, accessibility to general scientists",
            anchors={
                "1-20": "Unclear",
                "21-40": "Dense",
                "41-60": "Clear",
                "61-80": "Excellent",
                "81-100": "Exemplary",
            },
        ),
        RubricCriterion(
            name="Literature Grounding",
            weight=0.15,
            description="Context in broader literature, positioning relative to field",
            anchors={
                "1-20": "Poor",
                "21-40": "Partial",
                "41-60": "Adequate",
                "61-80": "Comprehensive",
                "81-100": "Exhaustive",
            },
        ),
        RubricCriterion(
            name="Reproducibility",
            weight=0.10,
            description="Data availability, methods detail, supplementary materials",
            anchors={
                "1-20": "No data",
                "21-40": "Partial data",
                "41-60": "Data available",
                "61-80": "Full data + code",
                "81-100": "Exemplary open science",
            },
        ),
        RubricCriterion(
            name="Ethics & Compliance",
            weight=0.05,
            description="Ethics approval, consent, responsible conduct",
            anchors={
                "1-20": "Serious concerns",
                "21-40": "Minor issues",
                "41-60": "Adequate",
                "61-80": "Good",
                "81-100": "Exemplary",
            },
        ),
    ],
)



MEDICAL = RubricStandard(
    id="medical",
    name="Medical (CONSORT)",
    description="Clinical and medical research — emphasis on methodology and ethics",
    publisher="CONSORT/ICMJE",
    criteria=[
        RubricCriterion(
            name="Technical Soundness",
            weight=0.20,
            description="Study design, statistical power, blinding, randomization, controls",
            anchors={
                "1-20": "Major design flaws, insufficient power",
                "21-40": "Several methodological issues",
                "41-60": "Adequate design",
                "61-80": "Rigorous RCT or well-designed study",
                "81-100": "Gold-standard methodology",
            },
        ),
        RubricCriterion(
            name="Originality & Novelty",
            weight=0.10,
            description="New therapeutic approaches, novel biomarkers, fresh hypotheses",
            anchors={
                "1-20": "Duplicate of existing studies",
                "21-40": "Minor variations",
                "41-60": "New approach",
                "61-80": "Significant innovation",
                "81-100": "Breakthrough",
            },
        ),
        RubricCriterion(
            name="Significance & Impact",
            weight=0.15,
            description="Clinical relevance, patient outcomes, guideline impact",
            anchors={
                "1-20": "No clinical relevance",
                "21-40": "Limited relevance",
                "41-60": "Moderate clinical impact",
                "61-80": "High clinical significance",
                "81-100": "Practice-changing",
            },
        ),
        RubricCriterion(
            name="Clarity of Presentation",
            weight=0.15,
            description="CONSORT compliance, table/figure quality, readability",
            anchors={
                "1-20": "Major reporting deficiencies",
                "21-40": "Partial CONSORT compliance",
                "41-60": "Adequate reporting",
                "61-80": "Excellent CONSORT adherence",
                "81-100": "Exemplary reporting",
            },
        ),
        RubricCriterion(
            name="Literature Grounding",
            weight=0.15,
            description="Systematic review, Cochrane references, current evidence",
            anchors={
                "1-20": "No systematic review",
                "21-40": "Partial review",
                "41-60": "Adequate review",
                "61-80": "Comprehensive systematic review",
                "81-100": "Meta-analysis included",
            },
        ),
        RubricCriterion(
            name="Reproducibility",
            weight=0.15,
            description="Protocol registration, data sharing, CONSORT checklist",
            anchors={
                "1-20": "No protocol, no data sharing",
                "21-40": "Partial registration",
                "41-60": "Registered protocol",
                "61-80": "Full CONSORT + data available",
                "81-100": "Open data, open protocol, open analysis",
            },
        ),
        RubricCriterion(
            name="Ethics & Compliance",
            weight=0.10,
            description="IRB approval, informed consent, trial registration, COI disclosure",
            anchors={
                "1-20": "No ethics approval, no consent",
                "21-40": "Incomplete compliance",
                "41-60": "Basic compliance",
                "61-80": "Full ICMJE compliance",
                "81-100": "Exemplary ethics",
            },
        ),
    ],
)



GENERAL = RubricStandard(
    id="general",
    name="General",
    description="Balanced default for any academic paper",
    publisher="General Academic",
    criteria=[
        RubricCriterion(
            name="Technical Soundness",
            weight=0.20,
            description="Methodology rigor, correctness, experimental design",
            anchors={
                "1-20": "Major flaws",
                "21-40": "Several issues",
                "41-60": "Adequate",
                "61-80": "Rigorous",
                "81-100": "Flawless",
            },
        ),
        RubricCriterion(
            name="Originality & Novelty",
            weight=0.15,
            description="Novel contributions, fresh perspective",
            anchors={
                "1-20": "Incremental",
                "21-40": "Minor extension",
                "41-60": "Meaningful",
                "61-80": "Significant",
                "81-100": "Groundbreaking",
            },
        ),
        RubricCriterion(
            name="Significance & Impact",
            weight=0.15,
            description="Potential impact, practical implications",
            anchors={
                "1-20": "Niche",
                "21-40": "Limited",
                "41-60": "Moderate",
                "61-80": "High",
                "81-100": "Transformative",
            },
        ),
        RubricCriterion(
            name="Clarity of Presentation",
            weight=0.15,
            description="Writing quality, figures, logical flow",
            anchors={
                "1-20": "Confusing",
                "21-40": "Unclear",
                "41-60": "Clear",
                "61-80": "Excellent",
                "81-100": "Exemplary",
            },
        ),
        RubricCriterion(
            name="Literature Grounding",
            weight=0.15,
            description="Related work coverage, citation quality",
            anchors={
                "1-20": "Poor",
                "21-40": "Partial",
                "41-60": "Adequate",
                "61-80": "Comprehensive",
                "81-100": "Exhaustive",
            },
        ),
        RubricCriterion(
            name="Reproducibility",
            weight=0.10,
            description="Data/code availability, experimental setup",
            anchors={
                "1-20": "Impossible",
                "21-40": "Difficult",
                "41-60": "Possible",
                "61-80": "Straightforward",
                "81-100": "Fully reproducible",
            },
        ),
        RubricCriterion(
            name="Ethics & Compliance",
            weight=0.10,
            description="Ethical considerations, compliance",
            anchors={
                "1-20": "Serious concerns",
                "21-40": "Minor issues",
                "41-60": "Adequate",
                "61-80": "Good",
                "81-100": "Exemplary",
            },
        ),
    ],
)




RUBRIC_STANDARDS: dict[str, RubricStandard] = {
    s.id: s for s in [IEEE, ACM, NATURE, MEDICAL, GENERAL]
}


def get_rubric_standard(standard_id: str) -> RubricStandard:
    """Get a rubric standard by ID. Falls back to GENERAL if not found."""
    return RUBRIC_STANDARDS.get(standard_id, GENERAL)


def list_rubric_standards() -> list[dict]:
    """List all available rubric standards (for API/UI)."""
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "publisher": s.publisher,
            "criteria_count": len(s.criteria),
        }
        for s in RUBRIC_STANDARDS.values()
    ]


def detect_rubric_from_paper(paper_venue: str | None, paper_doi: str | None, paper_arxiv_id: str | None) -> str:
    """Heuristically detect the best rubric standard from paper metadata.

    Returns the rubric standard ID.
    """
    venue_lower = (paper_venue or "").lower()
    doi_lower = (paper_doi or "").lower()
    arxiv_lower = (paper_arxiv_id or "").lower()

    # Nature/Science family
    if any(k in venue_lower for k in ["nature", "science", "cell", "lancet", "pnas"]):
        return "nature"

    # Medical journals
    if any(k in venue_lower for k in [
        "journal of", "medical", "clinical", "bmj", "jama", "nejm",
        "lancet", "plos medicine", "bmc",
    ]):
        return "medical"

    # IEEE family
    if any(k in venue_lower for k in ["ieee", "acm trans", "acm sig"]):
        return "ieee"

    # ACM family
    if any(k in venue_lower for k in ["acm", "sigsoft", "sigplan", "sigchi", "fse", "issta", "oopsla"]):
        return "acm"

    # arXiv category hints
    if arxiv_lower.startswith("cs."):
        return "acm"
    if arxiv_lower.startswith(("q-bio.", "physics.", "math.", "stat.")):
        return "nature"

    # DOI prefix hints
    if doi_lower.startswith("10.1109/"):  # IEEE
        return "ieee"
    if doi_lower.startswith("10.1145/"):  # ACM
        return "acm"
    if doi_lower.startswith("10.1038/"):  # Nature
        return "nature"
    if doi_lower.startswith(("10.1016/", "10.1056/", "10.1001/")):  # Elsevier/NEJM/JAMA
        return "medical"

    return "general"
