import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import BaseModel
from typing import List, Optional
import json
from github import Github,Auth
import time
import memory

load_dotenv()
class PlanStep(BaseModel):
    action:str
    owner:str
    repo:str
    issue_number:Optional[int] = None

class Plan(BaseModel):
    steps:List[PlanStep]



llm=ChatGroq(model="llama-3.1-8b-instant",
             api_key=os.getenv("GROQ_API_KEY"),)

github_token =os.getenv("GITHUB_TOKEN")
github_auth =Auth.Token(github_token)
gh =Github(auth=github_auth)

def list_open_issues(owner: str, repo_name: str, limit: int = 5) -> list:
    repo = gh.get_repo(f"{owner}/{repo_name}")
    issues = repo.get_issues(state="open")

    results =[]
    for issue in issues:
        if len(results) >= limit:
            break
        results.append({
            "number": issue.number,
            "title": issue.title
        })
    return results

def get_issue_details(owner: str, repo_name:str, issue_number:int) -> dict:
    repo =gh.get_repo(f"{owner}/{repo_name}")
    issue=repo.get_issue(number=issue_number)
    return{
        "number": issue.number,
        "title": issue.title,
        "state": issue.state,
        "body": issue.body
    }

def close_issue(owner: str, repo_name: str, issue_number: int) -> dict:
    repo=gh.get_repo(f"{owner}/{repo_name}")
    issue=repo.get_issue(number=issue_number)
    issue.edit(state="closed")
    return{
        "number": issue.number,
        "new_state": issue.state
    }

def plan_steps_structured(instruction:str) -> Plan:
    prompt=f"""You are a planning assistant for an AI agent that acts on Github
using the Github API through python. You only have these actions available:
-list_open_issues(owner,repo): lists open issues in a repo
-get_issue_details(owner, repo,issue_number): gets details of one specific issue
-close_issue(owner, repo, issue_number): closes one specific issue

Break the instruction into a sequence of these exact actions only. Respond with
ONLY valid JSON in this exact format, nothing else, no explanation, no markdown:

{{
  "steps":[
    {{"action": "list_open_issues", "owner": "...", "repo": "..."}},
    {{"action": "close_issue", "owner": "...", "repo": "...", "issue_number":5}}
    ]
}}

Instruction:{instruction}"""

    response =llm.invoke(prompt).content

    cleaned = response.strip()
    if cleaned.startswith("```"):
        cleaned =cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned =cleaned[4:]
        cleaned =cleaned.strip()

    data =json.loads(cleaned)
    return Plan(**data)

def execute_plan(plan: Plan) -> dict:
    executed_steps=[]

    for step in plan.steps:
        try:
            if step.action == "list_open_issues":
                result= list_open_issues(step.owner, step.repo)

            elif step.action == "get_issue_details":
                result= get_issue_details(step.owner, step.repo, step.issue_number)

            elif step.action == "close_issue":
                result =close_issue(step.owner, step.repo, step.issue_number)

            else:
                raise ValueError(f"Unknown action: {step.action}")

            executed_steps.append({
                "action":step.action,
                "status": "success",
                "result": result
            })

        except Exception as e:
            executed_steps.append({
                "action": step.action,
                "status": "failed",
                "error": str(e)
            })
            break

    return{
        "total_steps": len(plan.steps),
        "completed_steps":len(executed_steps),
        "steps": executed_steps
    }

def run_instruction(instruction:str) -> dict:
   start_time =time.time()

   past_matches = memory.get_similar_execution(instruction, limit=1)

   reused_plan =False
   if past_matches:
       try:
           plan= Plan(**json.loads(past_matches[0]["plan_json"]))
           reused_plan = True
       except Exception:
           plan =plan_steps_structured(instruction)
   else:
       plan= plan_steps_structured(instruction)

   report = execute_plan(plan)
   report["instruction"] =instruction
   report["reused_past_plan"] = reused_plan
   report["planning_llm_call_made"] = not reused_plan

   duration =time.time() - start_time

   for step_result in report["steps"]:
       memory.record_capability_use(
           action_name=step_result["action"],
           success=(step_result["status"] == "success"),
           error =step_result.get("error")
       )
   memory.save_execution(
       instruction = instruction,
       plan_json =plan.model_dump_json(),
       status="success" if report["completed_steps"] == report["total_steps"] else "failed",
       api_call_count=report["completed_steps"],
       duration_seconds=duration,
       error=report["steps"][-1].get("error") if report["steps"] and report["steps"][-1]["status"] == "failed" else None
   )

   return report

if __name__ == "__main__":
    test_instruction = "Get the details of issue number 1 in Shiva-keerth/OmniMind-AI-Enterprise"

    for i in range(1,5):
        t=time.time()
        report = run_instruction(test_instruction)
        elapsed =time.time() -t
        print(f"Run {i}: {elapsed:.2f}s, reused_past_plan: {report['reused_past_plan']}")

    print("\n=== Capability memory check ===")
    stats = memory.get_capability_stats("get_issue_details")
    print(json.dumps(stats, indent=2))