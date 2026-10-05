# ReMind — Google Photos Memory Reconstruction MVP

> **Full project context** derived from [`problemStatement.txt`](file:///c:/Users/Mukta Kulkarni/OneDrive/Desktop/Google MVP/problemStatement.txt)

---

## 1. Problem Statement

Users often cannot formulate the right search query for a photo they want to find. They remember the photo only vaguely (e.g., *"that small cafe we went to during our Goa trip"*) and cannot describe it precisely.

- **Keyword search** (e.g., "Goa cafe") and **AI natural-language search** (e.g., "Find the cafe we went to during our Goa trip") both depend on the user supplying a precise enough description.
- When the memory is incomplete, the user has no clear way to narrow down the results and reach the photo they have in mind.

### Core Question

> *"When users cannot formulate the right search query, does an AI-guided memory reconstruction loop help them retrieve the intended photo more successfully than conventional search?"*

---

## 2. Objective

### Primary Objective

Prove that **ReMind** can help a user retrieve a photo they cannot precisely describe, using **progressive memory reconstruction**.

ReMind achieves this by:

1. Converting the user's vague memory into machine-readable retrieval clues.
2. Retrieving a first candidate set of photos.
3. Identifying the additional clue that would **reduce uncertainty the most**, and asking the user for it.
4. Re-ranking the candidates after each answer until the user recognizes the intended photo.

### What the MVP Should Demonstrate

The value comes from **interactive reconstruction of incomplete memories**, rather than from AI understanding alone.

### Metrics

| Type | Metric |
|------|--------|
| **Primary** | Successful Vaguely-Remembered Photo Retrieval Rate |
| Secondary | Time to retrieval |
| Secondary | Refinement turns |
| Secondary | Photos viewed |
| Secondary | Abandonment |
| Secondary | User satisfaction |

### Out of Scope (Later Phases)

- Google's production-scale infrastructure
- Perfect AI search
- A complete personal memory graph
- Proactive memories
- Full Google Photos integration

---

## 3. MVP Scope

| Component | Details |
|-----------|---------|
| **Dataset** | 500–1,000 photos organized into realistic memory clusters (e.g., Goa trip, Bangalore weekend, College event, Medical/document photos) with distractor photos |
| **AI** | Multimodal LLM for image description, memory parsing, and refinement-question generation |
| **Retrieval** | Embeddings + metadata |
| **Ranking** | Semantic relevance + contextual match |
| **Core Innovation** | Uncertainty-driven refinement |
| **Frontend** | 5-screen lightweight mobile app |

---

## 4. System Workflow

The workflow has two parts:

1. **Offline Indexing Pipeline** — built once on the test library.
2. **Online Memory Reconstruction Loop** — run for every user search.

### 4.1 Offline: Library Indexing Pipeline

```
Photos → Multimodal analysis → Metadata + descriptions → Embeddings → Vector index
```

| Step | Description |
|------|-------------|
| **1 — Photo Library** | Controlled "Google Photos-like" test library of 500–1,000 photos. Sources: own photos, public-domain/sample images, or a synthetic dataset. Organized into memory clusters with distractor photos. |
| **2 — Multimodal Analysis** | The multimodal model generates descriptions/tags for each image (no manual creation). |
| **3 — Metadata + Descriptions** | A structured record per photo: `photo_id`, `date`, `location`, `people`, `event`, `scene`, `objects`, `visual_description`, `ocr_text`. Example: `photo_id: "goa_023"`, `date: "2025-12-18"`, `location: "Goa"`, `people: ["friend_1", "friend_2"]`, `event: "Goa Trip"`, `scene: ["cafe", "indoor"]`, `objects: ["coffee", "table"]`, `visual_description: "small cafe with blue wall and wooden tables"`. |
| **4 — Embeddings** | One combined representation per photo: visual description + objects + people + location + event + OCR. An embedding is generated for each combined representation. |
| **5 — Vector Index** | Embeddings stored in a vector index (FAISS, Chroma, Qdrant, or Pinecone). Metadata kept alongside for both vector (semantic) and metadata search. |

### 4.2 Online: Memory Reconstruction Loop

```
Vague memory → Memory Understanding → Candidate Retrieval → Uncertainty Analysis → Memory Prompt → Re-rank → Recognition
```

| Step | What Happens | Screen | User-Facing Text | CTA / Options |
|------|-------------|--------|------------------|---------------|
| **1 — User Vague Memory** | User types a vague memory (e.g., *"That small cafe we went to during our Goa trip…"*) | Screen 1: Memory Search | "What do you remember?" | "Find my memory" |
| **2 — Memory Understanding** | LLM extracts structured retrieval clues with confidence scores (location, event, scene, people, time, visual_details). Example: `location: "Goa" (0.95)`, `scene: "cafe" (0.85)`, `people: null`, `time: null (0.0)`. | Screen 2: Understanding | "Here's what I understood" (e.g., Goa, Cafe, Trip, Friends - maybe) | "Find photos" |
| **3 — Candidate Retrieval** | Extracted clues drive vector/semantic search + metadata search → top 20 candidates. | Screen 3: Candidates | "I found 20 possibilities" (photo grid) | "Help me narrow it down" |
| **4 — Uncertainty Analysis** | Memory Refinement Engine examines candidates and asks: *"What additional clue would reduce uncertainty the most?"* Example: 8 daytime cafes, 7 evening cafes, 5 beach cafes → system picks the most useful dimension. | *(internal)* | — | — |
| **5 — Memory Prompt** | LLM generates the refinement question (e.g., *"Do you remember if it was during the day or evening?"*). | Screen 4: Memory Refinement | "What else do you remember?" | Day / Evening / Not sure |
| **6 — Re-rank** | User's answer applied as a constraint. Example: "Evening" → 20 → 6 candidates. Steps 4–6 repeat until recognition. | Screen 3 (updated) | "These 6 look closer." | — |
| **7 — Recognition** | Best match shown as large photo. | Screen 5: Success | "I think we found it!" / "Is this the photo you remember?" | "Yes, that's it" / "No, keep looking" |

> **Note:** "No, keep looking" continues the refinement loop (Steps 4–6).

### 4.3 End-to-End Flow Summary

1. User has a vague memory: *"That cafe in Goa…"*
2. **Memory Understanding:** extract contextual clues.
3. **Candidate Retrieval:** find top 20 photos.
4. **Uncertainty Analysis:** identify what information would help most.
5. **Memory Prompt:** *"Day or evening?"*
6. **Re-rank:** 20 → 6 candidates.
7. **Recognition:** *"That's the one!"*

### 4.4 Frontend Screen Map (5-Screen Lightweight Mobile App)

| Screen | Title | Prompt | Action |
|--------|-------|--------|--------|
| 1 | Memory Search | "What do you remember?" | Find my memory |
| 2 | Understanding | "Here's what I understood" | Find photos |
| 3 | Candidates | "I found 20 possibilities" | Help me narrow it down |
| 4 | Memory Refinement | "What else do you remember?" | Select a clue / I don't remember |
| 5 | Success | "I think we found it!" | Yes, that's it / No, keep looking |

---

## 5. How the Workflow Will Be Tested

### Participants

10–20 users × 5 vague-memory tasks.

**Example task:** *"Find the photo from your Goa trip where you were sitting at a cafe with friends."*

### Three Versions Compared

| Version | Approach | Example |
|---------|----------|---------|
| **A — Traditional keyword search (control)** | Keyword query | "Goa cafe" |
| **B — AI natural-language search** | Free-form NL query | "Find the cafe we went to during our Goa trip." |
| **C — ReMind (Memory Reconstruction)** | Vague input → candidates → refinement loop → recognition | "That cafe from Goa." → candidates → "Was it near the beach?" → candidates → "Was it in the evening?" → recognition |

### Measured

- **Successful retrieval** (primary: Successful Vaguely-Remembered Photo Retrieval Rate)
- Time to retrieval
- Refinement turns / number of attempts
- Photos viewed
- Abandonment
- User confidence / satisfaction
