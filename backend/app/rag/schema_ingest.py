"""Convert IT Department ITR JSON Schemas into RAG-friendly text chunks
and embed them into the `itr_rulebook` pgvector collection.

The schemas (downloaded from incometax.gov.in) are JSON-Schema draft-04 files
with `$ref` indirection through a `definitions` block. We resolve refs once,
then walk the resulting tree and emit one chunk per **top-level section**
of an ITR form (PersonalInfo, ITR1_IncomeDeductions, Schedule80C, ...). Each
chunk lists the section's fields, types, descriptions, and which fields are
required, so a chat retrieval like "what fields does Schedule80C have in ITR-1"
returns a single self-contained answer.

Usage:
    backend/venv/Scripts/python.exe -m app.rag.schema_ingest               # ingests all
    backend/venv/Scripts/python.exe -m app.rag.schema_ingest --form ITR-1  # one form
    backend/venv/Scripts/python.exe -m app.rag.schema_ingest --dry-run     # preview chunks
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

# UTF-8 stdout so the rupee symbol etc. don't crash Windows cp932 consoles.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


_KB_DIR = Path(__file__).resolve().parents[2] / "knowledge_base" / "itr_schemas"
_SAMPLES_DIR = Path(__file__).resolve().parents[2] / "knowledge_base" / "itr_samples"

_FORM_DESCRIPTIONS = {
    "ITR-1": "ITR-1 (Sahaj) — for resident individuals with income up to Rs 50 lakh from salary, one house property, and other sources.",
    "ITR-2": "ITR-2 — for individuals and HUFs with capital gains, multiple house properties, or foreign income (no business income).",
    "ITR-3": "ITR-3 — for individuals and HUFs having income from business or profession (proprietors, professionals, freelancers).",
    "ITR-4": "ITR-4 (Sugam) — for individuals/HUFs/firms (other than LLP) with presumptive income under sections 44AD, 44ADA, 44AE.",
    "ITR-5": "ITR-5 — for firms, LLPs, AOPs, BOIs, artificial juridical persons, cooperative societies, local authorities.",
    "ITR-6": "ITR-6 — for companies (other than those claiming exemption under section 11).",
    "ITR-7": "ITR-7 — for persons including companies required to furnish returns under sections 139(4A) to 139(4F) (trusts, political parties, research institutions).",
}


# ---------------------------------------------------------------------------
# JSON-Schema resolver
# ---------------------------------------------------------------------------

def _resolve_ref(node: Any, root: dict, _seen: Optional[set] = None) -> Any:
    """Recursively resolve `$ref` references against `root`. Inlines them so
    the rest of the pipeline can ignore the indirection. Cycles are broken
    by leaving the second occurrence unresolved.
    """
    _seen = _seen or set()
    if isinstance(node, dict):
        if "$ref" in node and isinstance(node["$ref"], str):
            ref = node["$ref"]
            if ref.startswith("#/"):
                if ref in _seen:
                    return {"_circular_ref": ref}
                target = root
                for part in ref[2:].split("/"):
                    if not isinstance(target, dict) or part not in target:
                        return {"_unresolved_ref": ref}
                    target = target[part]
                return _resolve_ref(target, root, _seen | {ref})
        return {k: _resolve_ref(v, root, _seen) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve_ref(v, root, _seen) for v in node]
    return node


def _summarize_type(node: dict) -> str:
    """One-word/short type label for a schema node."""
    if not isinstance(node, dict):
        return "unknown"
    t = node.get("type")
    if isinstance(t, list):
        return "/".join(t)
    if t == "object":
        return "object"
    if t == "array":
        return "array"
    if t in ("integer", "number", "string", "boolean"):
        return t
    if "enum" in node:
        return f"enum({len(node['enum'])} values)"
    return "object"


def _short_desc(node: dict, max_len: int = 140) -> str:
    """Short single-line description from a schema node, falling back to
    title or empty string if neither is present."""
    if not isinstance(node, dict):
        return ""
    desc = node.get("description") or node.get("title") or ""
    desc = " ".join(str(desc).split())  # collapse whitespace
    if len(desc) > max_len:
        desc = desc[: max_len - 1] + "…"
    return desc


def _enum_summary(node: dict) -> str:
    """If the node has an enum, return a tiny inline note; else empty."""
    enum = node.get("enum") if isinstance(node, dict) else None
    if not enum:
        return ""
    if len(enum) <= 6:
        return f" Allowed: {', '.join(map(str, enum))}."
    return f" Allowed values: {', '.join(map(str, enum[:6]))}, … ({len(enum)} total)."


# ---------------------------------------------------------------------------
# Chunk emitter
# ---------------------------------------------------------------------------

def _emit_section_chunk(
    form: str,
    section_name: str,
    section_node: dict,
    parent_required: list[str],
) -> str:
    """Render one section of a form as a single chunk."""
    type_label = _summarize_type(section_node)
    description = _short_desc(section_node, max_len=280)

    lines: list[str] = []
    lines.append(f"{form} > {section_name} ({type_label})")
    if description:
        lines.append(f"Description: {description}")
    if section_name in parent_required:
        lines.append("This section is REQUIRED.")
    else:
        lines.append("This section is optional.")

    if isinstance(section_node, dict):
        required = section_node.get("required") or []
        properties = section_node.get("properties") or {}

        if required:
            req_list = ", ".join(required[:20])
            if len(required) > 20:
                req_list += f", … ({len(required)} total)"
            lines.append(f"Required fields: {req_list}.")

        if properties:
            lines.append("Fields:")
            for prop_name, prop_node in list(properties.items())[:60]:
                if not isinstance(prop_node, dict):
                    continue
                p_type = _summarize_type(prop_node)
                p_desc = _short_desc(prop_node, max_len=160)
                p_enum = _enum_summary(prop_node)
                req_marker = " [required]" if prop_name in required else ""
                bits = f"  - {prop_name} ({p_type}){req_marker}"
                if p_desc:
                    bits += f": {p_desc}"
                if p_enum:
                    bits += p_enum
                lines.append(bits)

                # Surface one level of nested object structure so retrieval can
                # answer "what's inside DeductUndChapVIA" without a second hop.
                if p_type == "object":
                    sub_props = list((prop_node.get("properties") or {}).keys())[:12]
                    if sub_props:
                        more = "" if len(sub_props) <= 12 else f", … ({len(prop_node['properties'])} total)"
                        lines.append(f"      sub-fields: {', '.join(sub_props)}{more}")

            if len(properties) > 60:
                lines.append(f"  … plus {len(properties) - 60} more fields.")

    return "\n".join(lines)


def _form_overview_chunk(form: str, root_node: dict) -> str:
    """One header chunk per form listing all top-level sections + form description."""
    sections = list((root_node.get("properties") or {}).keys())
    required = root_node.get("required") or []
    desc = _FORM_DESCRIPTIONS.get(form, "")

    lines = [f"{form} — Indian Income Tax Return Form (AY 2025-26)."]
    if desc:
        lines.append(desc)
    lines.append("")
    lines.append(f"Top-level sections in {form}:")
    for s in sections:
        marker = " (required)" if s in required else ""
        lines.append(f"  - {s}{marker}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Schema loader
# ---------------------------------------------------------------------------

def _load_form_root(schema_path: Path) -> tuple[str, dict]:
    """Load a schema, resolve refs, and return (form_id, root_form_node)
    where root_form_node is the body of the per-form definition (e.g. ITR1).
    """
    raw = json.loads(schema_path.read_text(encoding="utf-8"))
    resolved = _resolve_ref(raw, raw)

    # Schema layout: { "ITR": { "properties": { "ITR1": {...} } } }
    itr_node = resolved.get("properties", {}).get("ITR") or resolved.get("ITR")
    if not isinstance(itr_node, dict):
        raise ValueError(f"{schema_path.name}: missing top-level ITR node")

    inner_props = itr_node.get("properties") or {}
    # Find the ITR{N} key (ITR1 / ITR2 / ITR3 ...).
    form_key = next((k for k in inner_props if k.upper().startswith("ITR") and k != "ITR"), None)
    if form_key is None:
        raise ValueError(f"{schema_path.name}: could not find form node under ITR.properties")

    form_id = f"ITR-{form_key[-1]}"
    return form_id, inner_props[form_key]


def chunks_for_form(schema_path: Path) -> list[tuple[str, str]]:
    """Return [(chunk_text, source_label), ...] for every section in a form."""
    form_id, form_root = _load_form_root(schema_path)
    out: list[tuple[str, str]] = []

    out.append((_form_overview_chunk(form_id, form_root), schema_path.name))

    parent_required = form_root.get("required") or []
    for section_name, section_node in (form_root.get("properties") or {}).items():
        if not isinstance(section_node, dict):
            continue
        out.append((
            _emit_section_chunk(form_id, section_name, section_node, parent_required),
            schema_path.name,
        ))
    return out


def chunks_for_samples() -> list[tuple[str, str]]:
    """Render the worked-example sample JSONs into descriptive chunks."""
    out: list[tuple[str, str]] = []
    if not _SAMPLES_DIR.exists():
        return out
    for sample in sorted(_SAMPLES_DIR.glob("*_sample_data.json")):
        try:
            payload = json.loads(sample.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        # The samples are nested ITR/{ITRn}/...
        itr = payload.get("ITR") or {}
        if not isinstance(itr, dict) or not itr:
            continue
        form_key = next(iter(itr))
        form_id = f"ITR-{form_key[-1]}"
        body = itr[form_key]

        # Flatten dict-of-dicts into "Section.field = value" lines, capped
        # at a reasonable depth so we don't bloat the embedding.
        def _walk(node: Any, prefix: str, lines: list[str], depth: int = 0):
            if depth > 3 or len(lines) > 60:
                return
            if isinstance(node, dict):
                for k, v in node.items():
                    new_prefix = f"{prefix}.{k}" if prefix else k
                    if isinstance(v, (dict, list)):
                        _walk(v, new_prefix, lines, depth + 1)
                    else:
                        lines.append(f"{new_prefix} = {v}")
            elif isinstance(node, list):
                lines.append(f"{prefix} = [array of {len(node)} item(s)]")

        flat: list[str] = []
        _walk(body, "", flat)
        chunk_lines = [
            f"{form_id} — worked sample data (illustrative values only).",
            "",
            "Filled fields:",
        ] + [f"  {l}" for l in flat[:60]]
        if len(flat) > 60:
            chunk_lines.append(f"  … plus {len(flat) - 60} more lines.")
        out.append(("\n".join(chunk_lines), sample.name))
    return out


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def build_all_chunks(form_filter: Optional[str] = None) -> list[tuple[str, str]]:
    """Return all chunks for every schema (or just one if filtered)."""
    out: list[tuple[str, str]] = []
    schemas = sorted(_KB_DIR.glob("itr*_schema.json"))
    if not schemas:
        raise FileNotFoundError(f"No schemas under {_KB_DIR} — copy them in first.")
    for schema in schemas:
        form_id_guess = f"ITR-{schema.stem[3:].split('_')[0]}"  # itr1_schema → ITR-1
        if form_filter and form_id_guess.lower() != form_filter.lower():
            continue
        try:
            out.extend(chunks_for_form(schema))
        except Exception as e:
            print(f"WARN: failed to parse {schema.name}: {e}", file=sys.stderr)
    if not form_filter:
        out.extend(chunks_for_samples())
    return out


def ingest_schemas(
    form_filter: Optional[str] = None,
    *,
    collection: str = "itr_rulebook",
    replace_existing_schema_chunks: bool = True,
) -> int:
    """Embed schema chunks and write rows to `rag_documents`.

    By default we delete previously-ingested schema chunks (those whose source
    ends in `_schema.json` or `_sample_data.json`) before re-ingesting, so the
    other tax_rules.txt content stays put. Returns the number of rows written.
    """
    from sentence_transformers import SentenceTransformer
    from app.database import SessionLocal
    from app.models import RagDocument

    chunks = build_all_chunks(form_filter)
    if not chunks:
        return 0

    print(f"Encoding {len(chunks)} chunk(s) with all-MiniLM-L6-v2 …", flush=True)
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    texts = [c[0] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)

    db = SessionLocal()
    written = 0
    try:
        if replace_existing_schema_chunks:
            db.query(RagDocument).filter(
                RagDocument.collection == collection,
                RagDocument.source.like("itr%_schema.json")
                | RagDocument.source.like("%_sample_data.json"),
            ).delete(synchronize_session=False)
            db.commit()

        for idx, ((text, source), vec) in enumerate(zip(chunks, embeddings)):
            # Topic: extract "ITR-N" from the chunk header for filtered retrieval.
            topic = "itr-schema"
            head = text.split("\n", 1)[0]
            if head.startswith("ITR-"):
                topic = head.split()[0].lower()  # "itr-1", "itr-2", ...

            db.add(RagDocument(
                collection=collection,
                source=source,
                chunk_index=idx,
                topic=topic,
                content=text,
                embedding=vec.tolist(),
                extra_metadata={
                    "kind": "schema" if source.endswith("_schema.json") else "sample",
                    "char_len": len(text),
                },
            ))
            written += 1
        db.commit()
    finally:
        db.close()
    return written


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.rag.schema_ingest",
                                     description="Ingest ITR JSON schemas into pgvector RAG.")
    parser.add_argument("--form", help="Limit to one form, e.g. ITR-1")
    parser.add_argument("--collection", default="itr_rulebook")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print chunks instead of writing to DB")
    parser.add_argument("--keep-existing", action="store_true",
                        help="Don't delete previously-ingested schema chunks")
    args = parser.parse_args()

    if args.dry_run:
        chunks = build_all_chunks(args.form)
        print(f"\n{len(chunks)} chunk(s) would be ingested:\n")
        for i, (text, source) in enumerate(chunks):
            head = text.split("\n", 1)[0]
            print(f"  [{i:>3}] {source:<28} {head[:80]}")
        print()
        return

    n = ingest_schemas(
        form_filter=args.form,
        collection=args.collection,
        replace_existing_schema_chunks=not args.keep_existing,
    )
    print(f"Ingested {n} schema chunk(s) into '{args.collection}'.")


if __name__ == "__main__":
    main()
