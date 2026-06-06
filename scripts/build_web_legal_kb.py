from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from legal_doc_agent.legal_kb import LegalKnowledgeBase


RETRIEVED_AT = "2026-06-06T00:00:00Z"
VERSION_DATE = "2026-06-06"

SEED_DOCUMENTS = [
    {
        "source": {
            "key": "delaware-code-title8",
            "name": "Delaware Code Title 8",
            "jurisdiction": "Delaware",
            "source_url": "https://delcode.delaware.gov/title8/c001/",
            "official_level": "official",
        },
        "citation": "8 Del. C. § 101",
        "title": "Incorporators; formation; purposes",
        "jurisdiction": "Delaware",
        "doc_type": "statute-authority-note",
        "url": "https://delcode.delaware.gov/title8/c001/sc01/index.html#101",
        "heading": "Formation authority note",
        "path": "/title8/c001/sc01/101",
        "text": (
            "Authority note for Delaware corporate formation. Section 101 supports "
            "forming a Delaware corporation by filing a certificate of incorporation "
            "with the Division of Corporations and permits lawful business purposes. "
            "Use this when drafting formation checklists, incorporator actions, and "
            "corporate-purpose placeholders."
        ),
    },
    {
        "source": {
            "key": "delaware-code-title8",
            "name": "Delaware Code Title 8",
            "jurisdiction": "Delaware",
            "source_url": "https://delcode.delaware.gov/title8/c001/",
            "official_level": "official",
        },
        "citation": "8 Del. C. § 102",
        "title": "Contents of certificate of incorporation",
        "jurisdiction": "Delaware",
        "doc_type": "statute-authority-note",
        "url": "https://delcode.delaware.gov/title8/c001/sc01/index.html#102",
        "heading": "Certificate contents authority note",
        "path": "/title8/c001/sc01/102",
        "text": (
            "Authority note for certificate of incorporation contents. Section 102 "
            "supports checking company name, registered office and agent, business "
            "purpose language, stock authorization, incorporator information, and "
            "optional charter provisions before drafting Delaware C-corp documents."
        ),
    },
    {
        "source": {
            "key": "delaware-code-title8",
            "name": "Delaware Code Title 8",
            "jurisdiction": "Delaware",
            "source_url": "https://delcode.delaware.gov/title8/c001/",
            "official_level": "official",
        },
        "citation": "8 Del. C. § 109",
        "title": "Bylaws",
        "jurisdiction": "Delaware",
        "doc_type": "statute-authority-note",
        "url": "https://delcode.delaware.gov/title8/c001/sc01/index.html#109",
        "heading": "Bylaws authority note",
        "path": "/title8/c001/sc01/109",
        "text": (
            "Authority note for bylaws. Section 109 supports preparing bylaws that "
            "govern internal corporate administration, subject to the certificate of "
            "incorporation and Delaware law. Use this for bylaws, officer roles, "
            "meetings, notice, quorum, and governance checklist language."
        ),
    },
    {
        "source": {
            "key": "delaware-code-title8",
            "name": "Delaware Code Title 8",
            "jurisdiction": "Delaware",
            "source_url": "https://delcode.delaware.gov/title8/c001/",
            "official_level": "official",
        },
        "citation": "8 Del. C. § 141(a)",
        "title": "Board management authority",
        "jurisdiction": "Delaware",
        "doc_type": "statute-authority-note",
        "url": "https://delcode.delaware.gov/title8/c001/sc04/index.html#141",
        "heading": "Board authority note",
        "path": "/title8/c001/sc04/141/a",
        "text": (
            "Authority note for board authority. Section 141(a) supports routing "
            "corporate business and affairs through the board of directors unless the "
            "statute or certificate of incorporation provides otherwise. Use this for "
            "initial board consent, officer appointments, equity approvals, and banking "
            "authorization resolutions."
        ),
    },
    {
        "source": {
            "key": "delaware-code-title8",
            "name": "Delaware Code Title 8",
            "jurisdiction": "Delaware",
            "source_url": "https://delcode.delaware.gov/title8/c001/",
            "official_level": "official",
        },
        "citation": "8 Del. C. § 141(f)",
        "title": "Board action without meeting",
        "jurisdiction": "Delaware",
        "doc_type": "statute-authority-note",
        "url": "https://delcode.delaware.gov/title8/c001/sc04/index.html#141",
        "heading": "Board consent authority note",
        "path": "/title8/c001/sc04/141/f",
        "text": (
            "Authority note for written or electronic board consent. Section 141(f) "
            "supports board action without a meeting when the required directors consent, "
            "subject to the corporation's governing documents and statutory requirements. "
            "Use this for initial board consent and unanimous consent packages."
        ),
    },
    {
        "source": {
            "key": "delaware-code-title8",
            "name": "Delaware Code Title 8",
            "jurisdiction": "Delaware",
            "source_url": "https://delcode.delaware.gov/title8/c001/",
            "official_level": "official",
        },
        "citation": "8 Del. C. § 151",
        "title": "Classes and series of stock",
        "jurisdiction": "Delaware",
        "doc_type": "statute-authority-note",
        "url": "https://delcode.delaware.gov/title8/c001/sc05/index.html#151",
        "heading": "Stock class authority note",
        "path": "/title8/c001/sc05/151",
        "text": (
            "Authority note for stock classes and series. Section 151 supports checking "
            "authorized shares, classes, rights, powers, preferences, limitations, and "
            "board resolutions before issuing founder shares or creating option plans."
        ),
    },
    {
        "source": {
            "key": "delaware-code-title8",
            "name": "Delaware Code Title 8",
            "jurisdiction": "Delaware",
            "source_url": "https://delcode.delaware.gov/title8/c001/",
            "official_level": "official",
        },
        "citation": "8 Del. C. § 152",
        "title": "Issuance of stock; consideration",
        "jurisdiction": "Delaware",
        "doc_type": "statute-authority-note",
        "url": "https://delcode.delaware.gov/title8/c001/sc05/index.html#152",
        "heading": "Stock issuance consideration authority note",
        "path": "/title8/c001/sc05/152",
        "text": (
            "Authority note for issuing stock. Section 152 supports documenting board "
            "approval, consideration, share counts, issuance terms, and payment records "
            "for founder stock purchase agreements, stock ledgers, and capitalization "
            "tables."
        ),
    },
    {
        "source": {
            "key": "delaware-code-title8",
            "name": "Delaware Code Title 8",
            "jurisdiction": "Delaware",
            "source_url": "https://delcode.delaware.gov/title8/c001/",
            "official_level": "official",
        },
        "citation": "8 Del. C. § 157",
        "title": "Rights and options respecting stock",
        "jurisdiction": "Delaware",
        "doc_type": "statute-authority-note",
        "url": "https://delcode.delaware.gov/title8/c001/sc05/index.html#157",
        "heading": "Options and rights authority note",
        "path": "/title8/c001/sc05/157",
        "text": (
            "Authority note for rights and options. Section 157 supports drafting "
            "checklists for option rights, share limits, exercise terms, board approvals, "
            "and delegated authority when preparing equity incentive or founder vesting "
            "materials."
        ),
    },
    {
        "source": {
            "key": "delaware-code-title8",
            "name": "Delaware Code Title 8",
            "jurisdiction": "Delaware",
            "source_url": "https://delcode.delaware.gov/title8/c001/",
            "official_level": "official",
        },
        "citation": "8 Del. C. § 228",
        "title": "Stockholder consent without meeting",
        "jurisdiction": "Delaware",
        "doc_type": "statute-authority-note",
        "url": "https://delcode.delaware.gov/title8/c001/sc07/index.html#228",
        "heading": "Stockholder consent authority note",
        "path": "/title8/c001/sc07/228",
        "text": (
            "Authority note for stockholder written consent. Section 228 supports "
            "checking whether stockholder action may be taken without a meeting, the "
            "minimum voting power needed, consent delivery, notice, and record-date "
            "issues for founder and equity approvals."
        ),
    },
    {
        "source": {
            "key": "us-code-house",
            "name": "U.S. Code, Office of the Law Revision Counsel",
            "jurisdiction": "US-Federal",
            "source_url": "https://uscode.house.gov/",
            "official_level": "official",
        },
        "citation": "26 U.S.C. § 83(b)",
        "title": "Election for property transferred in connection with services",
        "jurisdiction": "US-Federal",
        "doc_type": "statute-authority-note",
        "url": "https://uscode.house.gov/view.xhtml?req=(title:26%20section:83%20edition:prelim)",
        "heading": "83(b) election authority note",
        "path": "/title26/83/b",
        "text": (
            "Authority note for restricted founder stock tax elections. Section 83(b) "
            "supports flagging that service providers receiving substantially nonvested "
            "property may need timely tax-election review, including transfer date, fair "
            "market value, amount paid, filing deadline, and qualified tax counsel review."
        ),
    },
]


def build_database(out_path: Path) -> None:
    if out_path.exists():
        out_path.unlink()
    kb = LegalKnowledgeBase(out_path)
    kb.initialize()
    seen_sources: set[str] = set()
    for item in SEED_DOCUMENTS:
        source = item["source"]
        source_key = str(source["key"])
        if source_key not in seen_sources:
            kb.upsert_source(
                key=source_key,
                name=str(source["name"]),
                jurisdiction=str(source["jurisdiction"]),
                source_url=str(source["source_url"]),
                official_level=str(source["official_level"]),
                retrieved_at=RETRIEVED_AT,
            )
            seen_sources.add(source_key)
        document = kb.upsert_document(
            source_key=source_key,
            citation=str(item["citation"]),
            title=str(item["title"]),
            jurisdiction=str(item["jurisdiction"]),
            doc_type=str(item["doc_type"]),
            version_date=VERSION_DATE,
            effective_date=VERSION_DATE,
            url=str(item["url"]),
        )
        section = kb.upsert_section(
            document_id=document.id,
            citation=str(item["citation"]),
            heading=str(item["heading"]),
            text=str(item["text"]),
            path=str(item["path"]),
            order_index=1,
        )
        kb.add_chunk(
            section_id=section.id,
            chunk_text=str(item["text"]),
            token_count=max(1, len(str(item["text"]).split())),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the deployed legal SQLite FTS5 KB.")
    parser.add_argument("--out", type=Path, default=Path("api/legal_kb.sqlite"))
    args = parser.parse_args()
    build_database(args.out)
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
