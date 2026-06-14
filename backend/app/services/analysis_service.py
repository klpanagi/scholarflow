from app.services.llm_service import llm_service


class AnalysisService:

    async def generate_summary(self, title: str, abstract: str | None, full_text: str, doc_type: str) -> dict:
        text_excerpt = full_text[:6000]
        prompt = f"""Analyze this {doc_type} and provide a structured summary.

Title: {title or 'Unknown'}
Abstract: {abstract or 'Not available'}

Content (excerpt):
{text_excerpt}

Respond in JSON format:
{{
  "summary": "2-3 sentence overview of the main contribution",
  "key_findings": ["finding 1", "finding 2", "finding 3"],
  "methodology": "brief description of methods used",
  "contributions": ["contribution 1", "contribution 2"],
  "limitations": ["limitation 1", "limitation 2"],
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
}}"""

        try:
            response = await llm_service.get_completion(
                model="minimax-m3-free",
                messages=[{"role": "user", "content": prompt}],
                provider="opencode-zen",
                temperature=0.3,
                max_tokens=2000,
            )
            import json
            json_match = response[response.find("{"):response.rfind("}") + 1]
            return json.loads(json_match)
        except Exception:
            return {
                "summary": f"Could not auto-analyze this {doc_type}.",
                "key_findings": [],
                "methodology": "",
                "contributions": [],
                "limitations": [],
                "keywords": [],
            }

    async def generate_tags(self, title: str, abstract: str | None, full_text: str) -> list[str]:
        text_excerpt = full_text[:3000]
        prompt = f"""Generate 5-8 relevant academic tags/keywords for this document.

Title: {title or 'Unknown'}
Abstract: {abstract or 'Not available'}
Content: {text_excerpt}

Return ONLY a JSON array of strings, e.g.: ["machine learning", "natural language processing", "transformer"]"""

        try:
            response = await llm_service.get_completion(
                model="minimax-m3-free",
                messages=[{"role": "user", "content": prompt}],
                provider="opencode-zen",
                temperature=0.3,
                max_tokens=500,
            )
            import json
            json_match = response[response.find("["):response.rfind("]") + 1]
            return json.loads(json_match)
        except Exception:
            return []

    async def analyze_strengths_weaknesses(self, title: str, abstract: str | None, full_text: str, doc_type: str) -> dict:
        text_excerpt = full_text[:6000]
        prompt = f"""Perform a critical analysis of this {doc_type}.

Title: {title or 'Unknown'}
Abstract: {abstract or 'Not available'}

Content (excerpt):
{text_excerpt}

Respond in JSON format:
{{
  "strengths": [
    {{"point": "strength description", "evidence": "supporting evidence from text"}},
    ...
  ],
  "weaknesses": [
    {{"point": "weakness description", "evidence": "supporting evidence from text"}},
    ...
  ],
  "suggestions": ["improvement suggestion 1", "improvement suggestion 2"],
  "quality_score": 7.5,
  "quality_rationale": "brief explanation of score"
}}"""

        try:
            response = await llm_service.get_completion(
                model="minimax-m3-free",
                messages=[{"role": "user", "content": prompt}],
                provider="opencode-zen",
                temperature=0.4,
                max_tokens=2000,
            )
            import json
            json_match = response[response.find("{"):response.rfind("}") + 1]
            return json.loads(json_match)
        except Exception:
            return {
                "strengths": [],
                "weaknesses": [],
                "suggestions": [],
                "quality_score": 0,
                "quality_rationale": "Analysis failed",
            }


analysis_service = AnalysisService()
