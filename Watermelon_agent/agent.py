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
memory.create_tables()
class PlanStep(BaseModel):
    action:str
    owner:str
    repo:str
    issue_number:Optional[int] = None

class Plan(BaseModel):
    steps:List[PlanStep]

class SynthesisRequest(BaseModel):
    needs_synthesis: bool
    capability_name: Optional[str] =None
    description: Optional[str] =None
    filter_field: Optional[str] =None
    filter_type: Optional[str] =None
    filter_value: Optional[str] =None
    action_to_apply: Optional[str] =None
    owner: Optional[str]=None
    repo: Optional[str] =None


llm=ChatGroq(model="llama-3.1-8b-instant",
             api_key=os.getenv("GROQ_API_KEY"),)

github_token =os.getenv("GITHUB_TOKEN")
github_auth =Auth.Token(github_token)
gh =Github(auth=github_auth)

def list_open_issues(owner: str, repo_name: str, state: str= "open", limit: int = 20) -> list:
    repo = gh.get_repo(f"{owner}/{repo_name}")
    issues = repo.get_issues(state=state)

    results =[]
    for issue in issues:
        if len(results) >= limit:
            break
        results.append({
            "number": issue.number,
            "title": issue.title,
            "body": issue.body
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

def reopen(owner: str, repo_name: str, issue_number: int) -> dict:
    repo=gh.get_repo(f"{owner}/{repo_name}")
    issue=repo.get_issue(number=issue_number)
    issue.edit(state="open")
    return{
        "number": issue.number,
        "new_state": issue.state,
        "title": issue.title
    }

def plan_steps_structured(instruction:str) -> Plan:
    prompt=f"""You are a planning assistant for an AI agent that acts on Github
using the Github API through python. You only have these actions available:
-list_open_issues(owner,repo): lists open issues in a repo
-get_issue_details(owner, repo,issue_number): gets details of one specific issue
-close_issue(owner, repo, issue_number): closes one specific issue
-reopen(owner, repo, issue_number): reopens one specific issue

Break the instruction into a sequence of these exact actions only. Respond with
ONLY valid JSON in this exact format, nothing else, no explanation, no markdown:

{{
  "steps":[
    {{"action": "list_open_issues", "owner": "...", "repo": "..."}},
    {{"action": "close_issue", "owner": "...", "repo": "...", "issue_number":5}},
    {{"action":"reopen","owner":"...","repo":"...","issue_number":5}}
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

def check_needs_synthesis(instruction: str) -> SynthesisRequest:
    prompt = f"""You are analyzing an instruction for an AI agent that only has these
    fixed actions available:
    - list_open_issues(owner, repo)
    - get_issue_details(owner, repo, issue_number)
    - close_issue(owner, repo, issue_number)
    - reopen(owner, repo, issue_number)

    These 4 actions already handle owner and repo as normal arguments — needing an owner
    or repo does NOT mean synthesis is needed. Synthesis is ONLY needed when the
    instruction requires finding issues that match a CONTENT condition (like a keyword
    inside the title), and then applying a DIFFERENT action to only the matches.

    Example 1 — does NOT need synthesis:
    Instruction: "List open issues in owner/repo"
    Answer: {{"needs_synthesis": false}}

    Example 2 — does NOT need synthesis:
    Instruction: "Get the details of issue number 3 in owner/repo"
    Answer: {{"needs_synthesis": false}}

    Example 3 — DOES need synthesis:
    Instruction: "Close all open issues in owner/repo whose title contains the word 'bug'"
    Answer: {{
      "needs_synthesis": true,
      "capability_name": "filter_and_close_by_title",
      "description": "Finds open issues whose title contains a keyword, then closes each one",
      "filter_field": "title",
      "filter_type": "contains",
      "filter_value": "bug",
      "action_to_apply": "close_issue",
      "owner": "owner",
      "repo": "repo"
    }}
    
    Example 4 — DOES need synthesis:
    Instruction: "Reopen all issues whose title contains 'bug'."
    Answer:{{
     "needs_synthesis": true,
     "capability_name": "reopen_matching_issues",
     "description": "Reopen all issues whose title contains the word 'bug'.",
     "filter_field": "title",
     "filter_type": "contains",
     "filter_value": "bug",
     "action_to_apply": "reopen",
     "owner": "owner",
      "repo": "repo"
    }}

    Respond with ONLY valid JSON, nothing else, no explanation, no markdown.
    Use the EXACT owner and repo given in the instruction, spelled exactly as written.

    Instruction: {instruction}"""

    response = llm.invoke(prompt).content

    cleaned =response.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    data = json.loads(cleaned)
    return SynthesisRequest(**data)

def execute_synthesized_capability(request: SynthesisRequest) -> dict:
    existing =memory.get_synthesized_capability(request.capability_name)

    was_reused =existing is not None

    if not was_reused:
        memory.save_synthesized_capability(
            capability_name=request.capability_name,
            description=request.description,
            filter_field=request.filter_field,
            filter_type=request.filter_type,
            action_to_apply=request.action_to_apply
        )
    fetch_state = "closed" if request.action_to_apply == "reopen" else "open"

    try:
        all_issues = list_open_issues(request.owner, request.repo, state=fetch_state, limit=50)
        memory.record_capability_use(action_name="list_open_issues", success=True)
    except Exception as e:
        memory.record_capability_use(action_name="list_open_issues", success=False, error=str(e))
        raise

    matched=[]
    for issue in all_issues:
        field_value = issue.get(request.filter_field,"")
        if request.filter_type == "contains" and request.filter_value.lower() in str(field_value).lower():
            matched.append(issue)

    applied_results=[]
    for issue in matched:
        if request.action_to_apply == "close_issue":
           try:
               result =close_issue(request.owner, request.repo, issue["number"])
               memory.record_capability_use(action_name="close_issue", success=True)
               applied_results.append(result)
           except Exception as e:
               memory.record_capability_use(action_name="close_issue",success=False, error=str(e))

        elif request.action_to_apply == "reopen":
            try:
                result = reopen(request.owner,request.repo,issue["number"])
                memory.record_capability_use(action_name="reopen",success=True)
                applied_results.append(result)

            except Exception as e:
                memory.record_capability_use(action_name="reopen",success=False,error=str(e))



    return{
        "capability_name": request.capability_name,
        "was_reused": was_reused,
        "total_issues_checked": len(all_issues),
        "matched_count": len(matched),
        "matched_issues": matched,
        "applied_results": applied_results
    }

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

            elif step.action == "reopen":
                result = reopen(step.owner, step.repo, step.issue_number)

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

   synthesis_check =check_needs_synthesis(instruction)

   if synthesis_check.needs_synthesis:
       synthesis_result = execute_synthesized_capability(synthesis_check)
       duration =time.time() - start_time

       memory.save_execution(
           instruction=instruction,
           plan_json=synthesis_check.model_dump_json(),
           status="success",
           api_call_count=synthesis_result["matched_count"] + synthesis_result["total_issues_checked"],
           duration_seconds=duration,
           error=None
       )

       return {
           "instruction": instruction,
           "used_synthesis": True,
           **synthesis_result
       }

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
    print("Watermelon Agent — type an instruction, or 'quit' to exit.\n")
    while True:
        instruction = input("Instruction: ").strip()
        if instruction.lower() in ("quit", "exit"):
            break
        if not instruction:
            continue

        start = time.time()
        result = run_instruction(instruction)
        elapsed = time.time() - start

        print(json.dumps(result, indent=2))
        print(f"Time taken: {elapsed:.2f} seconds\n")

