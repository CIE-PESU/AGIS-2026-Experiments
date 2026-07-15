# User Journey

```
Login
  │
  ▼
Dashboard
  │
  ▼
Start New Idea / Resume Existing Session
  │
  ▼
Pre-Evaluation Form
(Problem, Customer, Solution, Geography, etc.)
  │
  ▼
Validation Agent
(Check missing fields, contradictions, invalid responses)
  │
  ├────────────────────────────────┐
  ▼                                ▼
Regulatory Mapping Agent      Ethics Gate
(Applicable regulations)      (Legal, ethical, privacy,
                                safety, environmental checks)
  │                                │
  └──────────────┬─────────────────┘
                  ▼
       Build Compliance Context
                  │
           Compliance Flag?
        ┌─────────┴─────────┐
        No                  Yes
        │                    │
        ▼                    ▼
Show Compliance Issues   TIPSC Agent
+ Recommendations             │
       Stop                   ▼
              Need Follow-up Questions?
               ┌──────────┴──────────┐
               No                   Yes
                │                    │
                ▼                    ▼
        Generate Result       Follow-up Agent
                                     │
                                     ▼
                          Ask Follow-up Question
                                     │
                                     ▼
                           Store in MongoDB
                                     │
                                     ▼
                       More Follow-up Turns?
                       (Max 3 Turns Total)
                        ┌──────┴──────┐
                        Yes            No
                        │               │
                        ▼               ▼
              Next Follow-up Turn   TIPSC Agent
                                        │
                                        ▼
                            Generate TIPSC Result
                        • TIPSC Score
                        • Reasoning
                        • Ready for DFV?
                        • Compliance Issues
                                        │
                              Ready for DFV?
                           ┌────────────┴────────────┐
                           No                        Yes
                            │                          │
                            ▼                          ▼
              Show Improvement                   Submit DFV
              Recommendations                          │
                                                        ▼
                                       Parallel DFV Evaluation
                          ┌────────────┬────────────┬────────────┐
                          ▼            ▼             ▼
                    Desirability   Feasibility    Viability
                       Agent          Agent          Agent
                          └────────────┼─────────────┘
                                       ▼
                                Evaluation Agent
                                       │
                          Analyze All Three Reports
                                       │
                             GO / NO-GO Decision
                                       │
                          ┌────────────┴────────────┐
                          GO                       NO-GO
                          │                          │
                          ▼                          ▼
             Proceed to Customer            Show Recommendations
                Discovery Phase             End Current Evaluation
```

## Stage Summary

1. **Entry** — Login → Dashboard → Start New Idea / Resume Existing Session
2. **Intake** — Pre-Evaluation Form (Problem, Customer, Solution, Geography, etc.)
3. **Validation** — Validation Agent checks for missing fields, contradictions, invalid responses
4. **Compliance Check** (runs in parallel)
   - Regulatory Mapping Agent — identifies applicable regulations
   - Ethics Gate — legal, ethical, privacy, safety, environmental checks
   - Both feed into a Build Compliance Context step
5. **Compliance Flag Decision**
   - **No** → Show Compliance Issues + Recommendations → Stop
   - **Yes** → Proceed to TIPSC Agent
6. **TIPSC Follow-up Loop**
   - Check if follow-up questions are needed
   - If yes: Follow-up Agent asks a question → stores response in MongoDB → checks if more turns remain (max 3 total) → Frontend will fetch and user will enter the follow up answer it will be stored in DB and sent to TIPSC reval agent
   - If no: Generate Result directly
7. **TIPSC Result Generation** — outputs TIPSC Score, Reasoning, Ready for DFV flag, and Compliance Issues
8. **Ready for DFV Decision**
   - **No** → Show Improvement Recommendations
   - **Yes** → Submit DFV
9. **Parallel DFV Evaluation** — Desirability Agent, Feasibility Agent, and Viability Agent run concurrently
10. **Final Evaluation** — Evaluation Agent analyzes all three DFV reports and issues a GO / NO-GO Decision
    - **GO** → Proceed to Customer Discovery Phase
    - **NO-GO** → Show Recommendations, End Current Evaluation