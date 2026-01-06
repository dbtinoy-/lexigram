"""Result Formatting Utilities"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.search.core.models import (  # type: ignore[import-untyped]
        SearchHit,
        SearchResponse,
    )

from lexigram.serialization import dumps


@dataclass
class FormatConfig:
    """Formatting configuration"""

    date_format: str = "%Y-%m-%d %H:%M:%S"
    highlight_pre: str = "<mark>"
    highlight_post: str = "</mark>"
    max_field_length: int = 1000
    truncate_with_ellipsis: bool = True
    include_metadata: bool = True
    include_highlights: bool = True


class ResultFormatter:
    """Formats search results for presentation"""

    def __init__(self, config: FormatConfig | None = None):
        self.config = config or FormatConfig()

    def format_response(self, response: SearchResponse) -> dict[str, Any]:
        """Format complete search response"""
        formatted = {
            "query": getattr(response, "query", ""),
            "total": response.metadata.total,
            "took": response.metadata.took,
            "max_score": response.metadata.max_score,
            "timed_out": response.metadata.timed_out,
        }

        if self.config.include_metadata:
            formatted["metadata"] = {
                "total": response.metadata.total,
                "took": response.metadata.took,
                "max_score": response.metadata.max_score,
                "timed_out": response.metadata.timed_out,
            }

        # Format hits
        formatted["hits"] = list(map(self.format_hit, response.hits))

        # Format facets
        if response.facets:
            formatted["facets"] = self.format_facets(response.facets)

        # Format aggregations
        if response.aggregations:
            formatted["aggregations"] = response.aggregations

        # Format suggestions
        if response.suggestions:
            formatted["suggestions"] = response.suggestions

        return formatted

    def format_hit(self, hit: SearchHit) -> dict[str, Any]:
        """Format individual search hit"""
        formatted = {
            "id": hit.id,
            "score": hit.score,
        }

        # Format document data
        if hit.data:
            formatted["data"] = self._format_document(hit.data)

        # Format highlights
        if self.config.include_highlights and hit.highlights:
            formatted["highlights"] = self._format_highlights(hit.highlights)

        # Add index and type info
        if hit.index:
            formatted["index"] = hit.index
        if hit.type:
            formatted["type"] = hit.type

        return formatted

    def format_facets(self, facets: dict[str, list]) -> dict[str, Any]:
        """Format facet results"""
        formatted = {}

        for field, values in facets.items():
            formatted[field] = [
                {
                    "value": item.get("value") if isinstance(item, dict) else item,
                    "count": item.get("count", 0) if isinstance(item, dict) else 0,
                }
                for item in values
            ]

        return formatted

    def _format_document(self, document: dict[str, Any]) -> dict[str, Any]:
        """Format document data"""
        formatted = {}

        for key, value in document.items():
            formatted[key] = self._format_value(value)

        return formatted

    def _format_value(self, value: Any) -> Any:
        """Format individual value"""
        if isinstance(value, datetime):
            return value.strftime(self.config.date_format)
        if isinstance(value, str):
            return self._truncate_string(value)
        if isinstance(value, dict):
            return self._format_document(value)
        if isinstance(value, list):
            return list(map(self._format_value, value))
        return value

    def _truncate_string(self, text: str) -> str:
        """Truncate string if too long"""
        if len(text) <= self.config.max_field_length:
            return text

        truncated = text[: self.config.max_field_length]

        if self.config.truncate_with_ellipsis:
            truncated += "..."

        return truncated

    def _format_highlights(self, highlights: dict[str, Any]) -> dict[str, Any]:
        """Format highlight data"""
        formatted = {}

        for field, highlight_data in highlights.items():
            if isinstance(highlight_data, list):
                # Multiple highlight fragments
                formatted[field] = list(
                    map(self._process_highlight_fragment, highlight_data),
                )
            else:
                # Single highlight - keep consistent as a list of fragments
                formatted[field] = [
                    self._process_highlight_fragment(str(highlight_data)),
                ]

        return formatted

    def _process_highlight_fragment(self, fragment: str) -> str:
        """Process highlight fragment"""
        # Replace default highlight tags with configured ones
        fragment = fragment.replace("<em>", self.config.highlight_pre)
        return fragment.replace("</em>", self.config.highlight_post)


class ExportFormatter:
    """Formats results for export"""

    def __init__(self, format_type: str = "json"):
        self.format_type = format_type

    def format_for_export(self, response: SearchResponse) -> str | bytes:
        """Format response for export"""
        if self.format_type == "json":
            return self._format_json(response)
        if self.format_type == "csv":
            return self._format_csv(response)
        if self.format_type == "xml":
            return self._format_xml(response)
        raise ValueError(f"Unsupported export format: {self.format_type}")

    def _format_json(self, response: SearchResponse) -> bytes:
        """Format as JSON"""

        formatter = ResultFormatter()
        formatted = formatter.format_response(response)

        return dumps(formatted, indent=2, default=str)

    def _format_csv(self, response: SearchResponse) -> str:
        """Format as CSV"""
        import csv
        import io

        if not response.hits:
            return ""

        output = io.StringIO()

        # Get all unique fields from hits
        all_fields = set()
        for hit in response.hits:
            if hit.data:
                all_fields.update(hit.data.keys())

        fieldnames = ["id", "score", *sorted(all_fields)]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for hit in response.hits:
            row = {"id": hit.id, "score": hit.score or 0}

            if hit.data:
                for field in all_fields:
                    value = hit.data.get(field, "")
                    row[field] = self._flatten_value(value)

            writer.writerow(row)

        return output.getvalue()

    def _format_xml(self, response: SearchResponse) -> str:
        """Format as XML"""

        def dict_to_xml(data: dict[str, Any], root_name: str = "item") -> str:
            xml_parts = [f"<{root_name}>"]

            for key, value in data.items():
                if isinstance(value, dict):
                    xml_parts.append(dict_to_xml(value, key))
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            xml_parts.append(dict_to_xml(item, key))
                        else:
                            xml_parts.append(
                                f"<{key}>{self._escape_xml(str(item))}</{key}>",
                            )
                else:
                    xml_parts.append(f"<{key}>{self._escape_xml(str(value))}</{key}>")

            xml_parts.append(f"</{root_name}>")
            return "".join(xml_parts)

        formatter = ResultFormatter()
        formatted = formatter.format_response(response)

        xml_output = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_output.append("<search_response>")

        # Add metadata
        if "metadata" in formatted:
            xml_output.append(dict_to_xml(formatted["metadata"], "metadata"))

        # Add hits
        if "hits" in formatted:
            for hit in formatted["hits"]:
                xml_output.append(dict_to_xml(hit, "hit"))

        xml_output.append("</search_response>")

        return "\n".join(xml_output)

    def _flatten_value(self, value: Any) -> str:
        """Flatten value for CSV export"""
        if isinstance(value, (list, dict)):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters"""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )


class HighlightProcessor:
    """Processes search result highlights"""

    def __init__(self, pre_tag: str = "<mark>", post_tag: str = "</mark>"):
        self.pre_tag = pre_tag
        self.post_tag = post_tag

    def process_highlights(self, highlights: dict[str, Any]) -> dict[str, Any]:
        """Process and standardize highlights"""
        processed = {}

        for field, highlight_data in highlights.items():
            if isinstance(highlight_data, list):
                processed[field] = list(map(self._standardize_tags, highlight_data))
            else:
                processed[field] = [self._standardize_tags(str(highlight_data))]

        return processed

    def _standardize_tags(self, text: str) -> str:
        """Standardize highlight tags"""
        # Remove existing tags
        text = re.sub(r"</?em>", "", text)
        text = re.sub(r"</?mark>", "", text)

        # Add our tags
        text = text.replace("<em>", self.pre_tag)
        return text.replace("</em>", self.post_tag)

    def extract_highlight_snippets(
        self,
        highlights: dict[str, Any],
        max_length: int = 200,
    ) -> dict[str, str]:
        """Extract highlight snippets"""
        snippets = {}

        for field, highlight_data in highlights.items():
            if isinstance(highlight_data, list):
                # Combine all fragments
                combined = "...".join(highlight_data)
            else:
                combined = str(highlight_data)

            # Truncate if too long
            if len(combined) > max_length:
                combined = combined[:max_length] + "..."

            snippets[field] = combined

        return snippets


__all__ = ["ExportFormatter", "FormatConfig", "HighlightProcessor", "ResultFormatter"]
