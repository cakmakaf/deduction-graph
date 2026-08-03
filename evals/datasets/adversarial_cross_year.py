"""Adversarial cross-year retrieval cases.

Each case names a tax year explicitly and asks a question whose wording matches
the other year's passage just as well. A naive retriever has no way to prefer the
right one. A scoped retriever cannot return the wrong one.

`forbidden_chunk_ids` is the assertion that matters. Returning any of them is a
scope-precision failure and blocks the release.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from deduction_graph.types import FilingStatus, Provision


class CrossYearCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str
    question: str
    tax_year: int
    filing_status: FilingStatus | None
    provisions: tuple[Provision, ...]
    expected_chunk_ids: tuple[str, ...]
    forbidden_chunk_ids: tuple[str, ...]


ADVERSARIAL_CASES: tuple[CrossYearCase, ...] = (
    CrossYearCase(
        case_id="xy-sd-single-2024",
        question="What is the standard deduction for a single filer in 2024?",
        tax_year=2024,
        filing_status=FilingStatus.SINGLE,
        provisions=(Provision.STANDARD_DEDUCTION,),
        expected_chunk_ids=("pub501-2024:sd-single",),
        forbidden_chunk_ids=("pub501-2025:sd-single", "pub501-2025:sd-mfj"),
    ),
    CrossYearCase(
        case_id="xy-sd-single-2025",
        question="What is the standard deduction for a single filer in 2025?",
        tax_year=2025,
        filing_status=FilingStatus.SINGLE,
        provisions=(Provision.STANDARD_DEDUCTION,),
        expected_chunk_ids=("pub501-2025:sd-single",),
        forbidden_chunk_ids=("pub501-2024:sd-single", "pub501-2024:sd-mfj"),
    ),
    CrossYearCase(
        case_id="xy-salt-2024",
        question="What is the limit on the state and local tax deduction for 2024?",
        tax_year=2024,
        filing_status=None,
        provisions=(Provision.SALT,),
        expected_chunk_ids=("scha-2024:salt-cap",),
        forbidden_chunk_ids=("scha-2025:salt-cap",),
    ),
    CrossYearCase(
        case_id="xy-salt-2025",
        question="What is the limit on the state and local tax deduction for 2025?",
        tax_year=2025,
        filing_status=None,
        provisions=(Provision.SALT,),
        expected_chunk_ids=("scha-2025:salt-cap",),
        forbidden_chunk_ids=("scha-2024:salt-cap",),
    ),
    CrossYearCase(
        case_id="xy-sli-2024",
        question="At what income does the student loan interest deduction phase out in 2024?",
        tax_year=2024,
        filing_status=FilingStatus.SINGLE,
        provisions=(Provision.STUDENT_LOAN_INTEREST,),
        expected_chunk_ids=("pub970-2024:sli-phaseout",),
        forbidden_chunk_ids=("pub970-2025:sli-phaseout",),
    ),
    CrossYearCase(
        case_id="xy-sli-2025",
        question="At what income does the student loan interest deduction phase out in 2025?",
        tax_year=2025,
        filing_status=FilingStatus.SINGLE,
        provisions=(Provision.STUDENT_LOAN_INTEREST,),
        expected_chunk_ids=("pub970-2025:sli-phaseout",),
        forbidden_chunk_ids=("pub970-2024:sli-phaseout",),
    ),
    CrossYearCase(
        case_id="xy-hsa-2024",
        question="What is the HSA family contribution limit for 2024?",
        tax_year=2024,
        filing_status=None,
        provisions=(Provision.HSA,),
        expected_chunk_ids=("pub969-2024:hsa-limit",),
        forbidden_chunk_ids=("pub969-2025:hsa-limit",),
    ),
    CrossYearCase(
        case_id="xy-hsa-2025",
        question="What is the HSA family contribution limit for 2025?",
        tax_year=2025,
        filing_status=None,
        provisions=(Provision.HSA,),
        expected_chunk_ids=("pub969-2025:hsa-limit",),
        forbidden_chunk_ids=("pub969-2024:hsa-limit",),
    ),
    CrossYearCase(
        case_id="xy-mortgage-2024",
        question="What is the home acquisition debt limit for mortgage interest in 2024?",
        tax_year=2024,
        filing_status=None,
        provisions=(Provision.MORTGAGE_INTEREST,),
        expected_chunk_ids=("pub936-2024:acq-limit",),
        forbidden_chunk_ids=("pub936-2025:acq-limit",),
    ),
    CrossYearCase(
        case_id="xy-mortgage-2025",
        question="What is the home acquisition debt limit for mortgage interest in 2025?",
        tax_year=2025,
        filing_status=None,
        provisions=(Provision.MORTGAGE_INTEREST,),
        expected_chunk_ids=("pub936-2025:acq-limit",),
        forbidden_chunk_ids=("pub936-2024:acq-limit",),
    ),
    CrossYearCase(
        case_id="xy-medical-2024",
        question="What percentage of AGI must medical expenses exceed to be deductible in 2024?",
        tax_year=2024,
        filing_status=None,
        provisions=(Provision.MEDICAL,),
        expected_chunk_ids=("scha-2024:medical-floor",),
        forbidden_chunk_ids=("scha-2025:medical-floor",),
    ),
    CrossYearCase(
        case_id="xy-charitable-2025",
        question="What is the AGI limit on cash charitable contributions in 2025?",
        tax_year=2025,
        filing_status=None,
        provisions=(Provision.CHARITABLE,),
        expected_chunk_ids=("pub526-2025:agi-limits",),
        forbidden_chunk_ids=("pub526-2024:agi-limits",),
    ),
)
