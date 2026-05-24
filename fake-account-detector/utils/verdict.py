from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class VerdictResult:
    verdict: Literal["High Risk Fake", "Suspicious", "Likely Genuine", "Needs Review"]
    risk_score: int
    reasoning: str


def compute_verdict(
    account_prediction: str,
    account_confidence: float,
) -> VerdictResult:
    """
    Compute a final verdict from account prediction confidence only.
    
    Args:
        account_prediction: "Fake" or "Real"
        account_confidence: Confidence from model (0.0 to 1.0)
    
    Returns:
        VerdictResult with verdict, risk_score (0-100), and reasoning
    """
    confidence = min(1.0, max(0.0, float(account_confidence)))
    normalized_prediction = account_prediction.strip().lower()
    # Convert model output into a unified 0-100 risk scale.
    base_risk = int(round((confidence if normalized_prediction == "fake" else (1.0 - confidence)) * 100))

    if normalized_prediction == "fake":
        # Higher confidence fake predictions are escalated directly.
        if confidence >= 0.8:
            return VerdictResult(
                verdict="High Risk Fake",
                risk_score=max(80, base_risk),
                reasoning="Model strongly predicts this account is fake.",
            )

        if confidence >= 0.6:
            return VerdictResult(
                verdict="Suspicious",
                risk_score=max(60, base_risk),
                reasoning="Model predicts fake with moderate confidence.",
            )

        return VerdictResult(
            verdict="Needs Review",
            risk_score=max(45, base_risk),
            reasoning="Model predicts fake but confidence is limited.",
        )

    if normalized_prediction == "real":
        # Real predictions need stronger confidence before being marked low risk.
        if confidence >= 0.75:
            return VerdictResult(
                verdict="Likely Genuine",
                risk_score=min(25, base_risk),
                reasoning="Model strongly predicts this account is genuine.",
            )

        return VerdictResult(
            verdict="Needs Review",
            risk_score=max(35, base_risk),
            reasoning="Model predicts genuine but confidence is not high enough.",
        )

    return VerdictResult(
        verdict="Needs Review",
        risk_score=50,
        reasoning="Prediction label was not recognized.",
    )
