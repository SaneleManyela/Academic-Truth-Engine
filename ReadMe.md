Uxolo, let’s get this right. We are grounding this README in the true history of our session—starting exactly where you said: **"Run Jupyter on windows powershell. I have already installed the system."**

This is your official project documentation, written to ensure that your academic process is as transparent and rigorous as the 80%+ grades you are aiming for.

---

# 🎓 Academic Truth Engine: Project README

**Course Focus:** Applied Research Methods, Statistics, and Ethical Leadership.
**Core Principle:** Grounded, Non-Editorialized Factual Retrieval.

## 📍 Project Origins: The PowerShell Foundation

The project was initiated on a local machine using **Windows PowerShell** to host the Jupyter environment. This ensures that the data stays within your controlled environment and leverages local processing power for high-stakes research.

* **Initialization Command:** `jupyter notebook`

## 🎯 Goal & Strategy

The intention of this system is to act as a high-fidelity research partner for the upcoming semester. To achieve **>80%** in each course, the system is engineered to:

1. **Prevent Hallucinations**: Uses a `temperature` of `0.1` and a strict "Context-Only" system prompt.
2. **Ensure Absolute Referencing**: Metadata is injected into every text chunk during the semantic parsing phase.
3. **Maximize Fact-Finding**: Implements **Query Fusion** to search the document from six different angles simultaneously.

---

## 🛠️ Technical Architecture

### 1. The Reasoning Engine (IBM Granite 3.0)

We utilize **Granite 3.0** via Replicate. This model was chosen for its strong reasoning capabilities in structured data (Statistics) and its ability to follow complex logical constraints (Leadership Ethics).

### 2. Semantic Logic & Data Integrity

Instead of cutting your textbooks at random character limits, we use the `SemanticSplitterNodeParser`.

* **Why?** In **Applied Research Methods**, breaking a statistical formula or a methodology description in half leads to failure. Semantic splitting keeps related concepts together.
* **Referencing:** Every node is tagged with `metadata['source']`, ensuring citations are absolute and correct.

### 3. The Meta "Query Fusion" Method

Following the **Llama Cookbook** standard, Step 5 creates a `QueryRewritingRetriever`.

* **The Process**: When you ask a question about "Multicultural Leadership," the AI rewrites that question 6 times.
* **The Result**: It retrieves a wider net of facts, which are then fused and reranked to provide the single most accurate, non-editorialized answer.

---

## 📖 Usage Guide

| Step | Action | Description |
| --- | --- | --- |
| **0** | **PowerShell** | Launch Jupyter with `jupyter notebook`. |
| **1-2** | **Setup** | Install libraries and enter your `REPLICATE_API_KEY`. |
| **3** | **Ingestion** | Paste your Google Drive link to download the course PDF. |
| **4** | **Parsing** | The AI "reads" and semantically chunks the text. |
| **5-6** | **Research** | Enter the interactive loop to ask questions and get bulleted facts. |

---

## 🛡️ Academic Guardrails

To remain **emxholweni** (focused/on point), the system is hard-coded with this prompt:

> *"You are an expert academic RAG system. Answer ONLY using the provided context. Never hallucinate. Never editorialize. If the answer is not in the context, say so. Provide factual responses with 2-4 evidence bullets."*

---

**Now that the README and the Notebook are aligned with your actual starting point, would you like me to generate a "Final Exam Prep" prompt you can use to test your knowledge of the Statistics PDF?**
