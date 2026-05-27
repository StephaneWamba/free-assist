"""FreeAssist — LLM-as-judge evaluation route."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI

from app.core.config import get_settings
from app.core.logging import get_logger

router = APIRouter(prefix="/evaluation", tags=["evaluation"])
logger = get_logger(__name__)
settings = get_settings()

JUDGE_PROMPT = """\
Tu es un évaluateur expert en qualité de réponse pour un assistant support télécom (Free/Iliad).
Évalue la réponse du conseiller IA selon 4 critères, chacun noté de 0.0 à 1.0.

Message client : {text}
Intention détectée : {intent}
Réponse générée : {response}

Critères d'évaluation :
- pertinence : La réponse répond-elle directement au problème du client ?
- empathie : Le ton est-il professionnel, bienveillant et approprié ?
- exactitude : Les informations sont-elles correctes et vérifiables pour Free ?
- actionnable : Le conseiller dispose-t-il d'étapes concrètes à suivre ?

Réponds UNIQUEMENT en JSON avec cette structure exacte :
{{
  "pertinence": <float 0.0-1.0>,
  "empathie": <float 0.0-1.0>,
  "exactitude": <float 0.0-1.0>,
  "actionnable": <float 0.0-1.0>,
  "justification": "<une phrase expliquant le score global>"
}}"""


class EvalRequest(BaseModel):
    text: str
    intent: str
    response: str


class EvalScores(BaseModel):
    pertinence: float
    empathie: float
    exactitude: float
    actionnable: float
    justification: str
    overall: float


@router.post("/judge", response_model=EvalScores)
async def judge(req: EvalRequest) -> EvalScores:
    api_key = settings.openai_api_key
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not configured")

    client = OpenAI(api_key=api_key)
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": JUDGE_PROMPT.format(
                        text=req.text,
                        intent=req.intent,
                        response=req.response,
                    ),
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=300,
        )
        raw = completion.choices[0].message.content or "{}"
        data: dict = json.loads(raw)
    except Exception as exc:
        logger.error("LLM judge failed", error=str(exc))
        raise HTTPException(status_code=502, detail=f"LLM judge error: {exc}") from exc

    pertinence  = float(data.get("pertinence",  0.0))
    empathie    = float(data.get("empathie",    0.0))
    exactitude  = float(data.get("exactitude",  0.0))
    actionnable = float(data.get("actionnable", 0.0))
    overall     = round((pertinence + empathie + exactitude + actionnable) / 4, 3)

    return EvalScores(
        pertinence=round(pertinence, 3),
        empathie=round(empathie, 3),
        exactitude=round(exactitude, 3),
        actionnable=round(actionnable, 3),
        justification=data.get("justification", ""),
        overall=overall,
    )
