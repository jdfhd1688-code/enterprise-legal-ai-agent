"""Reject hallucinated citations by checking them against current retrieval hits."""

from __future__ import annotations

from app.schemas.kb import RetrievalResult
from app.schemas.risk import CitationStatus, EvidenceStatus, RiskAnalysis


class CitationGuard:
    """Validate citations using only the controlled retrieval result."""

    def validate(self, risk: RiskAnalysis, retrieval: RetrievalResult) -> RiskAnalysis:
        verified = 0
        unverified = 0
        for finding in risk.findings:
            for basis in finding.legal_basis:
                match = next(
                    (
                        hit for hit in retrieval.hits
                        if hit.chunk.article_no == basis.article_no
                        and (
                            hit.chunk.title == basis.title
                            or hit.chunk.title in basis.title
                        )
                    ),
                    None,
                )
                if match is None:
                    basis.citation_status = CitationStatus.unverified
                    unverified += 1
                else:
                    basis.citation_status = CitationStatus.verified
                    basis.document_id = match.chunk.document_id
                    basis.text = match.chunk.content
                    verified += 1
            finding.legal_evidence = list(finding.legal_basis)
            citation_ok = bool(finding.legal_basis) and all(
                basis.citation_status == CitationStatus.verified
                for basis in finding.legal_basis
            )
            finding.evidence_sufficient = bool(finding.contract_evidence) and citation_ok
            if finding.evidence_sufficient:
                finding.evidence_status = EvidenceStatus.sufficient
            elif finding.contract_evidence or finding.legal_basis or finding.playbook_evidence:
                finding.evidence_status = EvidenceStatus.partial
            else:
                finding.evidence_status = EvidenceStatus.insufficient
            finding.requires_human_review = finding.requires_human_review or not finding.evidence_sufficient

        if any(item.evidence_status == EvidenceStatus.insufficient for item in risk.findings):
            risk.evidence_status = EvidenceStatus.insufficient
        elif any(item.evidence_status == EvidenceStatus.partial for item in risk.findings):
            risk.evidence_status = EvidenceStatus.partial
        else:
            risk.evidence_status = EvidenceStatus.sufficient
        risk.evidence_sufficient = risk.evidence_status == EvidenceStatus.sufficient
        risk.citation_validation_summary = f"verified={verified}; unverified={unverified}"
        if unverified:
            risk.requires_human_review = True
        return risk
