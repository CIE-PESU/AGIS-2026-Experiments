"""Test script for AsyncPipelineExecutor with local MongoDB.
 
Run with: python test_async_pipeline.py
Requires: MongoDB running on 127.0.0.1:27017, LM Studio running.
 
The executor no longer polls for answers — it parks at WAITING_FOR_FOUNDER
and resumes via resume_after_followup().  This script mirrors that contract:
after each park it reads the question from MongoDB, takes input from stdin,
and calls resume_after_followup() directly.  That's the same call the
FastAPI /followup endpoint will make in production.
"""

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"

from motor.motor_asyncio import AsyncIOMotorClient

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from main import load_yaml, load_text, load_llm
from engine.stages import PipelineStages
from engine.async_pipeline_executor import AsyncPipelineExecutor, MAX_FOLLOWUP_TURNS
from engine.db import SessionStore
from engine.state_machine import PipelineState

def _print_tipsc(tipsc: dict):
    score_icon = lambda v: "🟢" if v == "GREEN" else ("🟡" if v == "YELLOW" else "🔴")
    s = tipsc.get("tips_rag_scores", {})
    print(f"  {score_icon(s.get('T'))} T: {s.get('T')}  {s.get('T_reason', '')}")
    print(f"  {score_icon(s.get('I'))} I: {s.get('I')}  {s.get('I_reason', '')}")
    print(f"  {score_icon(s.get('P'))} P: {s.get('P')}  {s.get('P_reason', '')}")
    print(f"  {score_icon(s.get('S'))} S: {s.get('S')}  {s.get('S_reason', '')}")
    print(f"  Readiness: {tipsc.get('overall_readiness')}  |  DFV: {tipsc.get('ready_for_dfv')}")
 

async def main():
    agents_cfg = load_yaml("config/agents.yaml")
    task_cfg = load_yaml("config/tasks.yaml")
    preeval_skill = load_text("skills/preeval/SKILL.md")
    tipsc_rubric = load_text("skills/tipsc/SKILL.md")
    ethics_rubric = load_text("skills/ethics/SKILL.md")

    llm = load_llm()

    stages = PipelineStages(
        llm=llm,
        agents_cfg=agents_cfg,
        task_cfg=task_cfg,
        preeval_skill=preeval_skill,
        tipsc_rubric=tipsc_rubric,
        ethics_rubric=ethics_rubric,
    )

    print("=" * 60)
    print("ASYNC PIPELINE with MongoDB (resumable)")
    print("=" * 60)

    preeval_input = {
        "problem_statement": input("Problem Statement: "),
        "customer_segment": input("Customer Segment: "),
        "consequence": input("Consequence: "),
        "assumptions": input("Assumptions: "),
        "proposed_solution": input("Proposed Solution: "),
        "target_geography": input("Target Geography: "),
        "industry_sector": input("Industry Sector: "),
        "team_id": "team_test_001",
        "student_id": "usr_test_001",
    }

    session_id = f"ses_{uuid.uuid4().hex[:12]}"
    mongo_client = AsyncIOMotorClient("mongodb://127.0.0.1:27017")
    db = SessionStore(mongo_client["agis"]["userSessions"])
    executor = AsyncPipelineExecutor(stages, db)

    print(f"\nSession ID: {session_id}")
    print("Pipeline running in background...\n")

    # ── Initial run ───────────────────────────────────────────────────────────
    # Runs through PreEval → Validation/Regulatory → Ethics → TIPSC.
    # If TIPSC needs follow-up it parks at WAITING_FOR_FOUNDER and returns.
    await executor.run(session_id, preeval_input)

    # ── Followup loop ─────────────────────────────────────────────────────────
    # Mirrors what the FastAPI endpoint does: read pending_question from
    # MongoDB, get founder input, call resume_after_followup().
    # Each resume() call either parks the next question or marks TIPSC_COMPLETE.
    doc = await db.get_session(session_id)
    while doc and doc.get("state") == PipelineState.WAITING_FOR_FOUNDER:
        turn     = doc.get("followup_turn", 1)
        question = doc.get("pending_question", "")
 
        print("\n" + "=" * 60)
        print(f"FOLLOW-UP QUESTION  ({turn}/{MAX_FOLLOWUP_TURNS})")
        print("=" * 60)
        print(question)
 
        answer = input("\n> ").strip()
        if not answer:
            answer = "(no answer provided)"
 
        print("\nResuming pipeline with new answer...\n")
 
        # This is exactly what POST /userSession/{id}/followup triggers.
        await executor.resume_after_followup(session_id, answer)
 
        doc = await db.get_session(session_id)
 
        # Show updated TIPSC scores after each reeval.
        if doc and doc.get("tipsc"):
            print("\nUpdated TIPSC scores:")
            _print_tipsc(doc["tipsc"])
 


    doc = await db.get_session(session_id)
    if doc:
        print("\n" + "=" * 60)
        print("FINAL MONGODB DOCUMENT")
        print("=" * 60)
        print(f"  State: {doc.get('state')}")
        print(f"  Team ID: {doc.get('team_id')}")
        print(f"  Student ID: {doc.get('student_id')}")

        stages_done = [
            ("Pre-Eval",   "preeval"),
            ("Validation", "validation"),
            ("Regulatory", "regulatory"),
            ("Ethics",     "ethics"),
        ]

        for label, key in stages_done:
            print(f"  {label}: {'✅' if doc.get(key) else '—'}")

        if doc.get("tipsc"):
            print(f"  TIPSC: ✅")
            _print_tipsc(doc["tipsc"])

        history = doc.get("followup_history", [])
        if history:
            print(f"\n  Follow-up exchanges ({len(history)}):")
            for i, ex in enumerate(history, 1):
                print(f"    Q{i}: {ex['question']}")
                print(f"    A{i}: {ex['answer']}")
 
         
        
        if doc.get("state") == PipelineState.FAILED:
            print(f"\n  ❌ Rejection: {doc.get('rejection_reason') or doc.get('error')}")

        print(f"\n  Full document written to MongoDB collection 'agis.userSessions'")
    else:
        print("\n  No document found in MongoDB.")

    mongo_client.close()


if __name__ == "__main__":
    asyncio.run(main())
