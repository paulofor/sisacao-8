"""Governed approval helpers for MUEN neural champions.

This module contains the pure validation and planning rules used before a neural
model can be marked as ``approved`` in ``neural_model_registry``. BigQuery I/O is
kept in Cloud Function wrappers so the approval rules remain unit-testable.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

APPROVED_STATUS = "approved"
CANDIDATE_STATUS = "candidate"
RESEARCH_GATE_NAME = "research_walk_forward"
MISSING_ECONOMICS_CRITERION = "muen_economics_missing"


@dataclass(frozen=True)
class ChampionApprovalRequest:
    """Operator request to promote a gated candidate to approved champion."""

    model_version: str
    decision_id: str
    approved_by: str
    approval_ticket: str
    dry_run: bool = True


@dataclass(frozen=True)
class ChampionApprovalPlan:
    """Validation result and BigQuery update plan for champion approval."""

    model_version: str
    decision_id: str
    approved: bool
    dry_run: bool
    current_status: str | None
    target_status: str = APPROVED_STATUS
    failed_checks: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    approval_note: str | None = None
    update_allowed: bool = False
    already_approved: bool = False
    checked_at: str = field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat()
    )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "model_version": self.model_version,
            "decision_id": self.decision_id,
            "approved": self.approved,
            "dry_run": self.dry_run,
            "current_status": self.current_status,
            "target_status": self.target_status,
            "failed_checks": list(self.failed_checks),
            "warnings": list(self.warnings),
            "approval_note": self.approval_note,
            "update_allowed": self.update_allowed,
            "already_approved": self.already_approved,
            "checked_at": self.checked_at,
        }


@dataclass(frozen=True)
class ChampionAuditResult:
    """Summary returned by champion approval audits."""

    approved_count: int
    model_versions: tuple[str, ...]
    warnings: tuple[str, ...]
    checked_at: str = field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat()
    )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "approved_count": self.approved_count,
            "model_versions": list(self.model_versions),
            "warnings": list(self.warnings),
            "checked_at": self.checked_at,
        }


def champion_approval_plan(
    request: ChampionApprovalRequest,
    *,
    registry_row: Mapping[str, Any] | None,
    gate_decision_row: Mapping[str, Any] | None,
) -> ChampionApprovalPlan:
    """Return an approval plan after validating registry and gate evidence.

    The returned plan is intentionally conservative: any missing evidence,
    failed gate criterion, mismatched status, or missing operator attribution
    blocks the update to ``approved``.
    """

    failed: list[str] = []
    warnings: list[str] = []

    if not request.model_version.strip():
        failed.append("model_version_obrigatorio")
    if not request.decision_id.strip():
        failed.append("decision_id_obrigatorio")
    if not request.approved_by.strip():
        failed.append("approved_by_obrigatorio")
    if not request.approval_ticket.strip():
        failed.append("approval_ticket_obrigatorio")

    registry = dict(registry_row or {})
    gate = dict(gate_decision_row or {})
    current_status = _text(registry.get("status"))
    already_approved = current_status == APPROVED_STATUS

    if not registry:
        failed.append("registry_modelo_nao_encontrado")
    elif _text(registry.get("model_version")) != request.model_version:
        failed.append("registry_model_version_divergente")
    elif current_status not in {CANDIDATE_STATUS, APPROVED_STATUS}:
        failed.append("registry_status_invalido_para_aprovacao")
    elif already_approved:
        warnings.append("modelo_ja_aprovado")

    if not gate:
        failed.append("gate_decision_nao_encontrada")
    else:
        failed.extend(_gate_failures(gate, request.decision_id))

    approval_note = None
    if not failed:
        approval_note = _approval_note(request, gate)

    update_allowed = not failed and not already_approved
    return ChampionApprovalPlan(
        model_version=request.model_version,
        decision_id=request.decision_id,
        approved=not failed,
        dry_run=request.dry_run,
        current_status=current_status,
        failed_checks=tuple(failed),
        warnings=tuple(warnings),
        approval_note=approval_note,
        update_allowed=update_allowed,
        already_approved=already_approved,
    )


def audit_approved_champions(rows: Sequence[Mapping[str, Any]]) -> ChampionAuditResult:
    """Summarize approved champions and flag duplicate protocol/snapshot groups."""

    approved_rows = [
        dict(row) for row in rows if _text(row.get("status")) == APPROVED_STATUS
    ]
    versions = tuple(_text(row.get("model_version")) for row in approved_rows)
    warnings: list[str] = []

    seen_groups: dict[tuple[str, str, str], list[str]] = {}
    for row in approved_rows:
        group = (
            _text(row.get("training_dataset_snapshot")),
            _text(row.get("feature_version")),
            _text(row.get("label_version")),
        )
        seen_groups.setdefault(group, []).append(_text(row.get("model_version")))
    for group, group_versions in seen_groups.items():
        if len(group_versions) > 1:
            warnings.append(
                "champions_duplicados:"
                + ":".join(group)
                + "="
                + ",".join(group_versions)
            )

    return ChampionAuditResult(
        approved_count=len(approved_rows),
        model_versions=versions,
        warnings=tuple(warnings),
    )


def _gate_failures(gate: Mapping[str, Any], decision_id: str) -> list[str]:
    failed: list[str] = []
    if _text(gate.get("decision_id")) != decision_id:
        failed.append("gate_decision_id_divergente")
    if _text(gate.get("gate_name")) != RESEARCH_GATE_NAME:
        failed.append("gate_name_invalido")
    if _text(gate.get("decision_status")) != "passed":
        failed.append("gate_status_nao_passou")
    if not bool(gate.get("passed")):
        failed.append("gate_passed_false")
    failed_criteria = _string_list(gate.get("failed_criteria"))
    if failed_criteria:
        failed.append("gate_failed_criteria_presentes")
    if MISSING_ECONOMICS_CRITERION in failed_criteria:
        failed.append("muen_economics_missing")
    if not _text(gate.get("candidate_family_hash")):
        failed.append("candidate_family_hash_ausente")
    if not _text(gate.get("protocol_version")):
        failed.append("protocol_version_ausente")
    if not _text(gate.get("dataset_snapshot")):
        failed.append("dataset_snapshot_ausente")
    return failed


def _approval_note(request: ChampionApprovalRequest, gate: Mapping[str, Any]) -> str:
    decided_at = _text(gate.get("decided_at")) or "unknown_decided_at"
    return (
        "\nApproved champion via MUEN Gate Research "
        f"decision_id={request.decision_id}; "
        f"approved_by={request.approved_by}; "
        f"approval_ticket={request.approval_ticket}; "
        f"gate_decided_at={decided_at}"
    )


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, Sequence):
        return [str(item) for item in value if str(item)]
    return [str(value)]


def _text(value: Any) -> str:
    return str(value or "").strip()
