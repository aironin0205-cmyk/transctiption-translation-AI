import hashlib, json
from datetime import datetime
from typing import Any, Dict, List, Optional
import requests
from tenacity import retry, stop_after_attempt, wait_exponential_jitter
from sqlalchemy.orm import Session
from .config import settings
from .models import LLMRun

def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def models_from_csv(csv: str) -> List[str]:
    return [m.strip() for m in (csv or "").split(",") if m.strip()]

class OpenRouterClient:
    def __init__(self):
        self.base = settings.openrouter_base_url.rstrip("/")
        self.key = settings.openrouter_api_key

    @retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=10))
    def chat(self, model: str, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> Dict[str, Any]:
        url = f"{self.base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "X-Title": "SubtitleAI-MVP",
        }
        payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        r = requests.post(url, headers=headers, json=payload, timeout=180)
        r.raise_for_status()
        return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=10))
    def embed(self, model: str, inputs: List[str]) -> List[List[float]]:
        url = f"{self.base}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "X-Title": "SubtitleAI-MVP",
        }
        payload = {"model": model, "input": inputs}
        r = requests.post(url, headers=headers, json=payload, timeout=180)
        r.raise_for_status()
        data = r.json()
        return [d["embedding"] for d in data["data"]]

client = OpenRouterClient()

def call_with_fallbacks(
    db: Session,
    job_id: Optional[str],
    cue_id: Optional[str],
    agent_name: str,
    primary_model: str,
    fallback_models: List[str],
    messages: List[Dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 2000,
    meta: Optional[Dict[str, Any]] = None,
) -> str:
    all_models = [primary_model] + list(fallback_models)
    inp = json.dumps(messages, ensure_ascii=False)
    run = LLMRun(
        job_id=job_id,
        cue_id=cue_id,
        agent_name=agent_name,
        model=primary_model,
        provider="openrouter",
        status="error",
        input_sha=_sha(inp),
        meta=meta or {},
    )
    db.add(run)
    db.commit()

    last_err = None
    for m in all_models:
        try:
            run.model = m
            run.started_at = datetime.utcnow()
            db.commit()
            resp = client.chat(m, messages, temperature=temperature, max_tokens=max_tokens)
            content = resp["choices"][0]["message"]["content"]
            run.status = "success"
            run.finished_at = datetime.utcnow()
            run.output_sha = _sha(content)
            usage = resp.get("usage") or {}
            run.prompt_tokens = usage.get("prompt_tokens")
            run.completion_tokens = usage.get("completion_tokens")
            db.commit()
            return content
        except Exception as e:
            last_err = str(e)
            run.status = "error"
            run.error_message = last_err
            run.finished_at = datetime.utcnow()
            db.commit()
            continue
    raise RuntimeError(f"All models failed for {agent_name}. Last error: {last_err}")
