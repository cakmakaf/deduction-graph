"""Hand-authored fixture corpus.

Deliberately adversarial: the 2024 and 2025 passages for each provision are
written to be near-identical in wording and to differ only in the figure and the
year. That is not artificial, it is how tax publications actually read year over
year, and it is precisely the condition under which embedding similarity fails to
discriminate.

The ablation study in milestone 7 runs naive retrieval and scoped retrieval over
this same corpus. If scoped retrieval ever returns a wrong-year chunk, the
scope-precision layer fails and the release is blocked.

Figures here mirror the rule YAML and carry the same verification caveat.
"""

from __future__ import annotations

from deduction_graph.retrieval.schema import Chunk, ChunkMetadata
from deduction_graph.types import AuthorityTier, FilingStatus, Provision


def _chunk(
    chunk_id: str,
    text: str,
    *,
    tax_year: int,
    provision: Provision,
    source: str,
    tier: AuthorityTier = AuthorityTier.PUBLICATION,
    statuses: tuple[FilingStatus, ...] = (),
    section: str | None = None,
) -> Chunk:
    return Chunk(
        text=text,
        metadata=ChunkMetadata(
            chunk_id=chunk_id,
            document_id=chunk_id.rsplit(":", 1)[0],
            source=source,
            tax_year=tax_year,
            provision=provision,
            authority_tier=tier,
            filing_statuses=statuses,
            section=section,
        ),
    )


FIXTURE_CHUNKS: tuple[Chunk, ...] = (
    # --- standard deduction, near-identical across years ---------------------
    _chunk(
        "pub501-2024:sd-single",
        "Standard deduction amount. For most people who file as single, the "
        "standard deduction for the tax year is $14,600. You cannot take the "
        "standard deduction if you itemize deductions on Schedule A.",
        tax_year=2024,
        provision=Provision.STANDARD_DEDUCTION,
        source="Pub 501 (2024)",
        statuses=(FilingStatus.SINGLE,),
        section="Standard Deduction Amount",
    ),
    _chunk(
        "pub501-2025:sd-single",
        "Standard deduction amount. For most people who file as single, the "
        "standard deduction for the tax year is $15,750. You cannot take the "
        "standard deduction if you itemize deductions on Schedule A.",
        tax_year=2025,
        provision=Provision.STANDARD_DEDUCTION,
        source="Pub 501 (2025)",
        statuses=(FilingStatus.SINGLE,),
        section="Standard Deduction Amount",
    ),
    _chunk(
        "pub501-2024:sd-mfj",
        "Standard deduction amount. Taxpayers who are married and file a joint "
        "return may claim a standard deduction of $29,200 for the tax year.",
        tax_year=2024,
        provision=Provision.STANDARD_DEDUCTION,
        source="Pub 501 (2024)",
        statuses=(FilingStatus.MARRIED_FILING_JOINTLY,),
    ),
    _chunk(
        "pub501-2025:sd-mfj",
        "Standard deduction amount. Taxpayers who are married and file a joint "
        "return may claim a standard deduction of $31,500 for the tax year.",
        tax_year=2025,
        provision=Provision.STANDARD_DEDUCTION,
        source="Pub 501 (2025)",
        statuses=(FilingStatus.MARRIED_FILING_JOINTLY,),
    ),
    # --- SALT, where the rule itself changed shape ----------------------------
    _chunk(
        "scha-2024:salt-cap",
        "Limit on state and local tax deduction. Your deduction for state and "
        "local taxes is limited to $10,000, or $5,000 if married filing "
        "separately. This limit applies to the total of state and local income "
        "taxes, sales taxes, and property taxes.",
        tax_year=2024,
        provision=Provision.SALT,
        source="Schedule A (Form 1040) Instructions (2024)",
        tier=AuthorityTier.INSTRUCTION,
    ),
    _chunk(
        "scha-2025:salt-cap",
        "Limit on state and local tax deduction. Your deduction for state and "
        "local taxes is limited to $40,000, or $20,000 if married filing "
        "separately. The limit is reduced for taxpayers with modified adjusted "
        "gross income above $500,000, but not below $10,000.",
        tax_year=2025,
        provision=Provision.SALT,
        source="Schedule A (Form 1040) Instructions (2025)",
        tier=AuthorityTier.INSTRUCTION,
    ),
    # --- mortgage interest, stable across years -------------------------------
    _chunk(
        "pub936-2024:acq-limit",
        "Home acquisition debt limit. You can generally deduct interest on home "
        "acquisition debt of up to $750,000, or $375,000 if married filing "
        "separately. A higher limit of $1,000,000 applies to debt incurred on or "
        "before December 15, 2017.",
        tax_year=2024,
        provision=Provision.MORTGAGE_INTEREST,
        source="Pub 936 (2024)",
    ),
    _chunk(
        "pub936-2025:acq-limit",
        "Home acquisition debt limit. You can generally deduct interest on home "
        "acquisition debt of up to $750,000, or $375,000 if married filing "
        "separately. A higher limit of $1,000,000 applies to debt incurred on or "
        "before December 15, 2017.",
        tax_year=2025,
        provision=Provision.MORTGAGE_INTEREST,
        source="Pub 936 (2025)",
    ),
    # --- student loan interest, phase-out thresholds shift --------------------
    _chunk(
        "pub970-2024:sli-phaseout",
        "Student loan interest deduction phaseout. The deduction is gradually "
        "reduced when your modified adjusted gross income is between $80,000 and "
        "$95,000 for single filers, or between $165,000 and $195,000 for those "
        "filing a joint return. The maximum deduction is $2,500.",
        tax_year=2024,
        provision=Provision.STUDENT_LOAN_INTEREST,
        source="Pub 970 (2024)",
    ),
    _chunk(
        "pub970-2025:sli-phaseout",
        "Student loan interest deduction phaseout. The deduction is gradually "
        "reduced when your modified adjusted gross income is between $85,000 and "
        "$100,000 for single filers, or between $170,000 and $200,000 for those "
        "filing a joint return. The maximum deduction is $2,500.",
        tax_year=2025,
        provision=Provision.STUDENT_LOAN_INTEREST,
        source="Pub 970 (2025)",
    ),
    # --- HSA, limits shift ----------------------------------------------------
    _chunk(
        "pub969-2024:hsa-limit",
        "HSA contribution limits. For self-only high deductible health plan "
        "coverage the annual contribution limit is $4,150. For family coverage "
        "the limit is $8,300. If you are age 55 or older you may contribute an "
        "additional $1,000.",
        tax_year=2024,
        provision=Provision.HSA,
        source="Pub 969 (2024)",
    ),
    _chunk(
        "pub969-2025:hsa-limit",
        "HSA contribution limits. For self-only high deductible health plan "
        "coverage the annual contribution limit is $4,300. For family coverage "
        "the limit is $8,550. If you are age 55 or older you may contribute an "
        "additional $1,000.",
        tax_year=2025,
        provision=Provision.HSA,
        source="Pub 969 (2025)",
    ),
    # --- medical, stable ------------------------------------------------------
    _chunk(
        "scha-2024:medical-floor",
        "Medical and dental expenses. You may deduct only the part of your "
        "medical and dental expenses that exceeds 7.5 percent of your adjusted "
        "gross income.",
        tax_year=2024,
        provision=Provision.MEDICAL,
        source="Schedule A (Form 1040) Instructions (2024)",
        tier=AuthorityTier.INSTRUCTION,
    ),
    _chunk(
        "scha-2025:medical-floor",
        "Medical and dental expenses. You may deduct only the part of your "
        "medical and dental expenses that exceeds 7.5 percent of your adjusted "
        "gross income.",
        tax_year=2025,
        provision=Provision.MEDICAL,
        source="Schedule A (Form 1040) Instructions (2025)",
        tier=AuthorityTier.INSTRUCTION,
    ),
    # --- charitable, stable ---------------------------------------------------
    _chunk(
        "pub526-2024:agi-limits",
        "Limits on deductions. Your deduction for cash contributions to public "
        "charities is generally limited to 60 percent of your adjusted gross "
        "income. Contributions you cannot deduct this year may be carried "
        "forward for up to 5 years.",
        tax_year=2024,
        provision=Provision.CHARITABLE,
        source="Pub 526 (2024)",
    ),
    _chunk(
        "pub526-2025:agi-limits",
        "Limits on deductions. Your deduction for cash contributions to public "
        "charities is generally limited to 60 percent of your adjusted gross "
        "income. Contributions you cannot deduct this year may be carried "
        "forward for up to 5 years.",
        tax_year=2025,
        provision=Provision.CHARITABLE,
        source="Pub 526 (2025)",
    ),
)


def by_year(tax_year: int) -> tuple[Chunk, ...]:
    return tuple(c for c in FIXTURE_CHUNKS if c.metadata.tax_year == tax_year)
