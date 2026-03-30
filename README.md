# 🔐 Privacy-Preserving Natural Language Querying via Schema-Driven Agent Pipelines

## 📌 Overview
This project enables **non-technical users** to explore data using natural language without ever exposing sensitive data to external systems.

Traditional natural language querying systems often rely on direct access to datasets, which introduces privacy risks. This project takes a fundamentally different approach:  

👉 **All query generation is performed using schema metadata only** (table names, column descriptions, relationships, and business context).  
👉 **No raw data is ever shared with Large Language Models (LLMs).**

By treating **privacy as a first-class constraint**, the system ensures safe and controlled query generation while maintaining usability and flexibility.

## 🧠 Key Idea: Schema-Only Reasoning
Instead of sending actual data to the model, the system uses:
- Table schemas  
- Column descriptions  
- Relationships between tables  
- Business context metadata  

This allows the LLM to:
- Understand user intent  
- Generate accurate structured queries  
- Maintain strict data privacy  

## ⚙️ Architecture

The system is built as an **LLM-powered, agent-driven pipeline** that decomposes the problem into modular stages:

### 🔄 Pipeline Stages
1. **Intent Interpretation**  
   - Understands the user's natural language query  

2. **Schema-Aware Table Selection**  
   - Identifies relevant tables using metadata  

3. **Column Selection & Filtering**  
   - Narrows down to required fields  

4. **Contextual Grounding**  
   - Uses validated examples and business logic  

5. **Structured Query Generation**  
   - Produces SQL (or equivalent structured query)

## 🏗️ Design Principles

### 🔐 Privacy First
- No raw data exposure at any stage  
- Schema-only interaction with LLMs  
- Safe for sensitive enterprise environments  

### 🔌 Execution-Agnostic
- Query generation is **decoupled from execution**

### 🧩 Modular Agent Design
- Each stage is handled by a dedicated agent  
- Improves interpretability and debugging  
- Enables independent optimization of components  

## ⏱️ Performance
- Handles **moderately complex analytical queries**
- End-to-end pipeline latency: **~30–50 seconds**

## 🧪 Data Usage
- Uses **synthetic or publicly available datasets only**
- No real or sensitive data is included in this project

## 🚀 Future Scope
- Add an interactive **chat-based interface** for user-friendly querying  
- Introduce **caching mechanisms** to optimize repeated query performance  
- Implement **conversational memory** to retain context across interactions  
- Enable **back-and-forth conversational querying**, allowing users to refine and iterate on previous queries naturally  
