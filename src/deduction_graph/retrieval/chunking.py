"""Chunking for tax guidance documents.

Design note: tax publications are split by section and rule boundary, not by a
fixed token count. A chunk that spans two filing statuses or two tax years is
worse than useless, because it will match both and be correct for neither.

TODO(milestone-2): implement the section-aware splitter against real Pub 17 and
Pub 501 text. The metadata assignment is the part that needs care, not the split.
"""

from __future__ import annotations

from deduction_graph.retrieval.schema import Chunk, ChunkMetadata


def chunk_document(
    text: str,
    *,
    base_metadata: ChunkMetadata,
    max_chars: int = 1800,
) -> list[Chunk]:
    """Split on blank-line paragraph boundaries, packing up to max_chars.

    A deliberately simple v1. The important property is that it never merges
    across a heading, which is enforced by the caller passing pre-split sections.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[Chunk] = []
    buffer: list[str] = []
    size = 0
    index = 0

    def flush() -> None:
        nonlocal buffer, size, index
        if not buffer:
            return
        chunks.append(
            Chunk(
                text="\n\n".join(buffer),
                metadata=base_metadata.model_copy(
                    update={"chunk_id": f"{base_metadata.document_id}:{index:04d}"}
                ),
            )
        )
        index += 1
        buffer = []
        size = 0

    for para in paragraphs:
        if size + len(para) > max_chars and buffer:
            flush()
        buffer.append(para)
        size += len(para)
    flush()
    return chunks
