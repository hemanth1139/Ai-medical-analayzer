"""
download_pmc.py
===============
Build an evaluation dataset from PubMed Central open-access case reports.

Fetches real titles and abstracts via NCBI E-utilities (esearch + efetch).
Does NOT inject synthetic lab values — each row records what was actually retrieved.

Columns:
  pmcid, title, ground_truth_report, data_source, has_numeric_values, ai_generated_advice
"""

import csv
import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple

USER_AGENT = "PatientActionGuide/1.0 (research evaluation)"
EFETCH_DELAY_SEC = 0.4  # NCBI rate limit: max 3 requests/sec without API key

# Patterns that suggest clinically useful numeric content in abstracts
NUMERIC_PATTERNS = [
    r"\d+\.?\d*\s*(?:mg/dL|mmol/L|g/dL|%|mIU/L|U/L|mmHg|bpm)",
    r"(?:HbA1c|glucose|cholesterol|creatinine|hemoglobin|eGFR)\s*[<>=:]?\s*\d",
]


def _request(url: str, insecure: bool = False) -> bytes:
    ctx = ssl._create_unverified_context() if insecure else ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as response:
            return response.read()
    except urllib.error.URLError as e:
        if not insecure and "CERTIFICATE_VERIFY_FAILED" in str(e):
            print("WARNING: SSL verification failed; retrying without certificate verification.")
            return _request(url, insecure=True)
        raise


def search_pmc_ids(query: str, retmax: int) -> List[str]:
    encoded = urllib.parse.quote(query)
    url = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=pmc&term={encoded}&retmode=json&retmax={retmax}"
    )
    data = json.loads(_request(url).decode())
    return data.get("esearchresult", {}).get("idlist", [])


def fetch_abstract_xml(pmcid: str) -> Optional[str]:
    """Return abstract plain text for a PMC numeric ID, or None if unavailable."""
    url = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=pmc&id={pmcid}&rettype=xml"
    )
    try:
        raw = _request(url).decode("utf-8", errors="replace")
    except Exception:
        return None

    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return None

    # PMC JATS: <abstract><p>...</p></abstract>
    parts = []
    for elem in root.iter():
        if elem.tag.endswith("abstract-title"):
            if elem.text:
                parts.append(elem.text.strip())
        if elem.tag.endswith("p") and _is_inside_abstract(elem, root):
            text = "".join(elem.itertext()).strip()
            if text:
                parts.append(text)

    abstract = " ".join(parts).strip()
    return abstract if abstract else None


def _is_inside_abstract(elem, root) -> bool:
    """Check if element is nested under an <abstract> tag."""
    # Walk parent chain via recursive search (ElementTree has no parent pointers)
    for abstract in root.iter():
        if abstract.tag.endswith("abstract"):
            for child in abstract.iter():
                if child is elem:
                    return True
    return False


def fetch_title_from_summary(pmcid: str, summary_cache: dict) -> str:
    info = summary_cache.get(pmcid, {})
    return info.get("title", "").strip()


def has_numeric_clinical_values(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(pat, text_lower, re.IGNORECASE) for pat in NUMERIC_PATTERNS)


def build_ground_truth_report(title: str, abstract: Optional[str], pmcid: str) -> Tuple[str, str]:
    """
    Returns (report_text, data_source).
    data_source is one of: abstract, title_only
    """
    if abstract and len(abstract) > 80:
        report = f"PMC{pmcid} Case Report.\nTitle: {title}\n\nClinical Summary (from published abstract):\n{abstract}"
        return report, "abstract"

    report = f"PMC{pmcid} Case Report.\nTitle: {title}\n\n(No abstract available — evaluation uses title context only.)"
    return report, "title_only"


def fetch_summaries(pmc_ids: list[str]) -> dict:
    if not pmc_ids:
        return {}
    ids_str = ",".join(pmc_ids)
    url = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        f"?db=pmc&id={ids_str}&retmode=json"
    )
    try:
        data = json.loads(_request(url).decode())
        return data.get("result", {})
    except Exception:
        return {}


def fetch_real_world_cases(
    output_file: str = "real_world_cases.csv",
    count: int = 100,
    query: Optional[str] = None,
) -> int:
    if query is None:
        query = (
            "(cholesterol OR glucose OR hemoglobin OR creatinine OR HbA1c OR anemia) "
            "AND case report"
        )

    print(f"Searching PMC for: {query}")
    # Request extra IDs because some may lack abstracts
    id_list = search_pmc_ids(query, retmax=count * 3)

    if not id_list:
        print("No articles found.")
        return 0

    print(f"Found {len(id_list)} candidate articles. Fetching metadata and abstracts...")
    summaries = fetch_summaries(id_list[: count * 2])

    cases = []
    for pmcid in id_list:
        if len(cases) >= count:
            break

        title = fetch_title_from_summary(pmcid, summaries)
        if not title:
            continue

        time.sleep(EFETCH_DELAY_SEC)
        abstract = fetch_abstract_xml(pmcid)
        report, source = build_ground_truth_report(title, abstract, pmcid)
        numeric = has_numeric_clinical_values(report)

        cases.append(
            {
                "pmcid": f"PMC{pmcid}",
                "title": title,
                "ground_truth_report": report,
                "data_source": source,
                "has_numeric_values": str(numeric),
                "ai_generated_advice": "",
            }
        )
        status = f"abstract OK, numeric={numeric}" if source == "abstract" else "title only"
        print(f"  [{len(cases)}/{count}] PMC{pmcid}: {status}")

    fieldnames = [
        "pmcid",
        "title",
        "ground_truth_report",
        "data_source",
        "has_numeric_values",
        "ai_generated_advice",
    ]

    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cases)

    abstract_count = sum(1 for c in cases if c["data_source"] == "abstract")
    numeric_count = sum(1 for c in cases if c["has_numeric_values"] == "True")

    print(f"\nSaved {len(cases)} records to {output_file}")
    print(f"  With abstracts : {abstract_count}")
    print(f"  With numeric values detected: {numeric_count}")
    print("  Note: No synthetic lab values were injected.")
    return len(cases)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download PMC case reports for evaluation.")
    parser.add_argument("--output", default="real_world_cases.csv")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--query", default=None, help="Custom PubMed Central search query")
    args = parser.parse_args()
    fetch_real_world_cases(args.output, args.count, args.query)
