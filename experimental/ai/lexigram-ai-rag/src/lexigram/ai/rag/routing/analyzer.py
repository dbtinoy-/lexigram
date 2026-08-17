"""Query analyzer for extracting features from queries."""

from __future__ import annotations

import re

from lexigram.ai.rag.multimodal.types import Modality
from lexigram.ai.rag.routing.types import QueryFeatures, QueryIntent


class QueryAnalyzer:
    """Analyzes queries to extract features for routing decisions.

    Extracts various features from queries including:
    - Basic features: length, keywords
    - Intent classification: factual, conversational, analytical, etc.
    - Language detection
    - Domain classification
    - Entity detection
    - Modality detection

    Example:
        ```python
        analyzer = QueryAnalyzer()
        features = await analyzer.analyze("How do I configure authentication?")
        logger.info(f"Intent: {features.intent}")
        logger.info(f"Keywords: {features.keywords}")
        logger.info(f"Complexity: {features.complexity}")
        ```
    """

    # Intent patterns (simple keyword-based classification)
    INTENT_PATTERNS: dict[QueryIntent, list[str]] = {
        QueryIntent.FACTUAL: [
            r"\bwhat\b",
            r"\bwho\b",
            r"\bwhen\b",
            r"\bwhere\b",
            r"\bdefine\b",
            r"\bexplain\b",
            r"\btell me\b",
        ],
        QueryIntent.PROCEDURAL: [
            r"\bhow\b",
            r"\bsteps\b",
            r"\bguide\b",
            r"\btutorial\b",
            r"\bconfigure\b",
            r"\bsetup\b",
            r"\binstall\b",
        ],
        QueryIntent.ANALYTICAL: [
            r"\bcompare\b",
            r"\bdifference\b",
            r"\bversus\b",
            r"\bvs\b",
            r"\banalyze\b",
            r"\bevaluate\b",
            r"\bpros and cons\b",
        ],
        QueryIntent.CREATIVE: [
            r"\bwrite\b",
            r"\bcreate\b",
            r"\bgenerate\b",
            r"\bcompose\b",
            r"\bpoem\b",
            r"\bstory\b",
            r"\bideas\b",
        ],
        QueryIntent.NAVIGATIONAL: [
            r"\bfind\b",
            r"\blocate\b",
            r"\bpage\b",
            r"\bdocumentation\b",
            r"\breference\b",
            r"\blink\b",
        ],
        QueryIntent.CONVERSATIONAL: [
            r"\bhello\b",
            r"\bhi\b",
            r"\bthanks\b",
            r"\bthank you\b",
            r"\bhow are you\b",
            r"\bbye\b",
        ],
    }

    # Domain keywords
    DOMAIN_KEYWORDS: dict[str, list[str]] = {
        "technical": [
            "api",
            "code",
            "function",
            "class",
            "method",
            "algorithm",
            "database",
            "server",
            "configuration",
            "deploy",
            "debug",
        ],
        "medical": [
            "patient",
            "disease",
            "treatment",
            "symptom",
            "diagnosis",
            "medication",
            "doctor",
            "hospital",
            "clinical",
        ],
        "legal": [
            "law",
            "legal",
            "contract",
            "regulation",
            "compliance",
            "statute",
            "court",
            "litigation",
            "rights",
        ],
        "financial": [
            "money",
            "investment",
            "stock",
            "profit",
            "revenue",
            "cost",
            "budget",
            "finance",
            "accounting",
        ],
    }

    # Stop words to exclude from keywords
    STOP_WORDS: set[str] = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "he",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "that",
        "the",
        "to",
        "was",
        "will",
        "with",
        "this",
        "but",
        "they",
        "have",
        "had",
        "what",
        "when",
        "where",
        "who",
        "which",
        "why",
        "how",
        "or",
        "can",
        "could",
        "should",
        "would",
    }

    def __init__(
        self,
        *,
        extract_keywords: bool = True,
        detect_entities: bool = True,
        classify_domain: bool = True,
    ):
        """Initialize the query analyzer.

        Args:
            extract_keywords: Whether to extract keywords.
            detect_entities: Whether to detect named entities.
            classify_domain: Whether to classify query domain.
        """
        self.extract_keywords = extract_keywords
        self.detect_entities = detect_entities
        self.classify_domain = classify_domain

    async def analyze(self, query: str) -> QueryFeatures:
        """Analyze a query and extract features.

        Args:
            query: Query text to analyze.

        Returns:
            Extracted query features.
        """
        # Basic features
        length = len(query)
        text_lower = query.lower()

        # Classify intent
        intent = self._classify_intent(text_lower)

        # Extract keywords
        keywords = self._extract_keywords(query) if self.extract_keywords else []

        # Detect language (simple heuristic)
        language = self._detect_language(query)

        # Classify domain
        domain = self._classify_domain(text_lower) if self.classify_domain else None

        # Detect entities (simple pattern-based)
        has_entities = self._detect_entities(query) if self.detect_entities else False

        # Detect modalities
        modalities = self._detect_modalities(text_lower)

        # Calculate complexity
        complexity = self._calculate_complexity(query, keywords)

        return QueryFeatures(
            text=query,
            length=length,
            intent=intent,
            language=language,
            domain=domain,
            keywords=keywords,
            has_entities=has_entities,
            modalities=modalities,
            complexity=complexity,
        )

    def _classify_intent(self, query_lower: str) -> QueryIntent:
        """Classify query intent using pattern matching.

        Args:
            query_lower: Lowercased query text.

        Returns:
            Classified intent.
        """
        scores: dict[QueryIntent, int] = {}

        for intent, patterns in self.INTENT_PATTERNS.items():
            score = sum(
                1
                for pattern in patterns
                if re.search(pattern, query_lower, re.IGNORECASE)
            )
            if score > 0:
                scores[intent] = score

        # Return intent with highest score, default to FACTUAL
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        return QueryIntent.FACTUAL

    def _extract_keywords(self, query: str) -> list[str]:
        """Extract keywords from query.

        Args:
            query: Query text.

        Returns:
            List of extracted keywords.
        """
        # Simple word extraction (split on whitespace and punctuation)
        words = re.findall(r"\b\w+\b", query.lower())

        # Filter out stop words and short words
        keywords = [
            word for word in words if word not in self.STOP_WORDS and len(word) > 2
        ]

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for keyword in keywords:
            if keyword not in seen:
                seen.add(keyword)
                unique_keywords.append(keyword)

        return unique_keywords[:10]  # Limit to top 10 keywords

    def _detect_language(self, query: str) -> str:
        """Detect query language (simple heuristic).

        Args:
            query: Query text.

        Returns:
            Language code (default: 'en').
        """
        # Simple heuristic: check for non-ASCII characters
        # In production, use langdetect or similar library
        if any(ord(char) > 127 for char in query):
            # Non-ASCII detected, could be non-English
            # For now, still return 'en' as default
            return "en"
        return "en"

    def _classify_domain(self, query_lower: str) -> str | None:
        """Classify query domain based on keywords.

        Args:
            query_lower: Lowercased query text.

        Returns:
            Domain classification or None if no match.
        """
        scores: dict[str, int] = {}

        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score > 0:
                scores[domain] = score

        # Return domain with highest score if above threshold
        if scores:
            max_domain = max(scores.items(), key=lambda x: x[1])
            if max_domain[1] >= 2:  # Require at least 2 matching keywords
                return max_domain[0]

        return None

    def _detect_entities(self, query: str) -> bool:
        """Detect if query contains named entities.

        Args:
            query: Query text.

        Returns:
            True if entities detected, False otherwise.
        """
        # Simple pattern-based detection
        # Look for capitalized words (potential proper nouns)
        capitalized_words = re.findall(r"\b[A-Z][a-z]+\b", query)

        # Filter out common sentence starters
        sentence_starters = {"What", "When", "Where", "Who", "Why", "How", "Which"}
        entities = list(
            filter(lambda word: word not in sentence_starters, capitalized_words),
        )

        return len(entities) > 0

    def _detect_modalities(self, query_lower: str) -> list[Modality]:
        """Detect modalities mentioned in the query.

        Args:
            query_lower: Lowercased query text.

        Returns:
            List of detected modalities.
        """
        modalities = [Modality.TEXT]  # Always include text

        # Check for image-related terms
        image_terms = [
            "image",
            "picture",
            "photo",
            "visual",
            "diagram",
            "chart",
            "graph",
        ]
        if any(term in query_lower for term in image_terms):
            modalities.append(Modality.IMAGE)

        # Check for audio-related terms
        audio_terms = ["audio", "sound", "music", "voice", "recording", "podcast"]
        if any(term in query_lower for term in audio_terms):
            modalities.append(Modality.AUDIO)

        # Check for video-related terms
        video_terms = ["video", "movie", "clip", "footage", "film"]
        if any(term in query_lower for term in video_terms):
            modalities.append(Modality.VIDEO)

        return modalities

    def _calculate_complexity(self, query: str, keywords: list[str]) -> float:
        """Calculate query complexity score.

        Args:
            query: Query text.
            keywords: Extracted keywords.

        Returns:
            Complexity score (0-1).
        """
        # Factors:
        # 1. Query length (longer = more complex)
        # 2. Number of keywords (more = more complex)
        # 3. Presence of complex punctuation
        # 4. Number of clauses (commas, semicolons)

        # Length score (0-1, max at 500 chars)
        length_score = min(len(query) / 500, 1.0)

        # Keyword score (0-1, max at 15 keywords)
        keyword_score = min(len(keywords) / 15, 1.0)

        # Punctuation complexity (0-1)
        complex_punctuation = query.count(",") + query.count(";") + query.count(":")
        punctuation_score = min(complex_punctuation / 5, 1.0)

        # Average the scores
        complexity = (length_score + keyword_score + punctuation_score) / 3

        return round(complexity, 2)
