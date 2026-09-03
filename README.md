# 🤖 Autonomous GitHub Agent

An autonomous AI agent that understands natural language GitHub requests, creates structured execution plans, executes GitHub actions, and continuously improves using persistent memory and capability synthesis — built to demonstrate autonomous reasoning under real technical constraints, not just prompt-response automation.

---

## ✨ Features
- 🧠 LLM-powered task planning using Groq (Llama 3.1)
- 📋 Structured planning with Pydantic models
- 🔗 GitHub API integration
- 💾 Persistent SQLite execution memory
- ⚡ Reuses previously successful execution plans
- 🔄 Runtime capability synthesis through tool composition
- 📊 Tracks execution statistics and tool reliability

---

## 🏗️ Tech Stack
- Python
- LangChain
- Groq (Llama 3.1)
- GitHub API
- SQLite
- Pydantic

---

## 🚀 Current Capabilities
- List GitHub Issues
- Retrieve Issue Details
- Close GitHub Issues
- Reopen GitHub Issues
- Plan multi-step workflows
- Learn from previous executions
- Synthesize reusable capabilities at runtime — generalized to any action and filter combination, not just close

---

## 📂 Project Structure

Watermelon_agent/
├── agent.py
├── memory.py
├── tests.py
├── ARCHITECTURE.md
└── DEMO.md

---

## 📖 Documentation
- **ARCHITECTURE.md** – System design and implementation decisions.
- **DEMO.md** – Walkthrough of the agent and capabilities.

---

Built with a focus on autonomous reasoning, persistent memory, and reusable AI capabilities rather than simple prompt-response automation.
