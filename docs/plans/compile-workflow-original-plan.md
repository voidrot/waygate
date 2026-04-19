# Original Compile Workflow Plan

This document preserves the original compile workflow plan as historical context.

It describes a broader target architecture than the current repository implements today. For the current implemented baseline, see:

- [docs/design/ingestion-and-workflows.md](../design/ingestion-and-workflows.md)
- [docs/design/data-models-and-storage.md](../design/data-models-and-storage.md)
- [docs/design/roadmap.md](../design/roadmap.md)

## Original Text

WayGate LangGraph Compiler Workflow Specification

Objective: Transform a batch of raw ingested documents into a single, cohesive, human-readable Markdown wiki page while extracting structured metadata, evaluating for hallucinations, and syncing to the PostgreSQL/pgvector storage layers.

1. The Graph State (Shared Memory)
To enable the Map-Reduce pattern and solve the "context blindness" of parallel processing, the LangGraph State must utilize Reducers (operator.add) for the short-term memory scratchpad.

raw_documents: Array of URIs/paths to the newly ingested files.

scratchpad: (Reduced via operator.add) A shared dictionary where sub-agents log defined terms, acronyms, and core claims to prevent downstream redundancy.

extracted_metadata: (Reduced via operator.add) A combined list of all Pydantic objects containing tags, topics, organizations, people, and projects.

document_summaries: (Reduced via operator.add) The array of individual file summaries.

current_draft: The synthesized Markdown string.

review_feedback: Critique from the Hermes node.

revision_count: Integer tracking the number of failed review loops.

1. Phase 1: The Compile Step (Map-Reduce)
This phase fans out the workload to process massive raw data without blowing out the LLM's context window.

Step 2A: The Fan-Out (Map)

The orchestrator node reads the raw_documents array and uses LangGraph's Send API to spawn parallel worker nodes for each individual file.

Step 2B: Sub-Agent Execution (Per File)
Each parallel worker executes a sequence of two sub-agents:

Metadata Agent: Reads the raw file and uses .with_structured_output() to force the LLM to return a strict Pydantic schema containing: tags, topics, organizations, people, and projects.

Summarize Agent: * Reads the scratchpad to see what previous workers have already defined or summarized.

Summarizes its assigned raw file.

Writes new acronyms or core concepts back to the scratchpad.

Appends its summary and metadata to the graph's global reduced state.

Step 2C: The Fan-In Synthesis (Reduce)

Once all parallel workers complete, the Synthesis Worker wakes up.

It ingests the document_summaries, the extracted_metadata, and the unified scratchpad.

It drafts a single, cohesive, high-level Markdown document that resolves redundancies and formats the final output.

1. Phase 2: The Review Step (Hermes Quality Gate)
This node acts as a ruthless, independent evaluator to prevent the system from degrading into hallucinations.

Input: The current_draft and the original raw_documents.

Execution: A distinct LLM instance (potentially a faster model) is prompted strictly to evaluate factual grounding, Markdown formatting, and tone.

Output: Returns a structured Pydantic ReviewOutcome containing a boolean approved flag and a list of specific feedback strings.

Routing Logic:

If approved == True: Route to Publish.

If approved == False AND revision_count < 3: Append feedback to state, increment revision_count, and route back to the Synthesis Worker for edits.

If approved == False AND revision_count >= 3: Route to Human Review (DLQ) to prevent infinite billing loops.

1. Phase 3: The Publish Step
This node transitions the stochastic LLM outputs into strictly deterministic, immutable storage utilizing the "Stable Identity" pattern.

File System (Live Wiki): * Generates a stable UUIDv7 for the document ID to prevent OS-level directory slowdowns.

Wraps the current_draft in strict YAML frontmatter (embedding the metadata extracted in Phase 1).

Writes the file to the flat live/ directory.

Vector Database (pgvector): * Chunks the original raw files (using semantic boundaries) to roughly 75% of the target context size.

Generates embeddings and upserts them into PostgreSQL using pgvector-python.

Attaches the extracted metadata (tags, orgs, people) as JSON payloads to the vector chunks for highly precise hybrid search later.

Library Index (Graph/PostgreSQL): * Updates the bipartite bridging tables (e.g., File_Entities) in PostgreSQL using SQLAlchemy to associate the new UUIDv7 file ID with its respective tags, topics, people, and organizations.

1. Phase 4: Human Review (The Dead-Letter Queue)
This is a terminal state in the LangGraph orchestration designed to handle catastrophic synthesis failures.

Execution: The graph halts execution.

State: The failed current_draft, the associated raw_documents, and the final review_feedback from Hermes are preserved in the graph's Postgres Checkpointer.

Post-Hook Alert: A LangGraph post-hook triggers an event (e.g., a Slack webhook or a notification to the Django-Ninja admin UI) alerting human developers that a document is deadlocked.

Resolution: A human reviews the draft, manually unblocks it, or adjusts the raw source data, allowing the graph to resume or be dismissed.
