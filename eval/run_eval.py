"""
eval/run_eval.py
----------------
Evaluation harness for the Mercedes RAG rebuild.

Usage:
    python eval/run_eval.py \\
        --dataset data/arxiv_5k.jsonl \\
        --retriever direct \\
        --k 5

    python eval/run_eval.py \\
        --dataset data/arxiv_5k.jsonl \\
        --retriever hyde \\
        --k 10 \\
        --out eval/results/run_001.json

Retriever modes:
    direct  — embed query directly, retrieve from Azure AI Search
    hyde    — generate hypothetical document via LLM, embed that, retrieve

Output (JSON):
    {
        "run_id": "run_001",
        "date": "2026-05-09",
        "retriever": "direct",
        "k": 5,
        "recall_at_k": 0.0,
        "mean_latency_ms": 0.0,
        "p95_latency_ms": 0.0,
        "num_queries": 200
    }
"""

import argparse
import json
import os
import uuid
from datetime import date
from typing import Literal


# ---------------------------------------------------------------------------
# Metric stubs
# ---------------------------------------------------------------------------

def compute_recall_at_k(
    queries: list[str],
    ground_truth_doc_ids: list[str],
    retriever_fn,
    k: int,
) -> float:
    """
    Compute Recall@K across a set of queries.

    For each query, the retriever_fn is called and the top-K doc_ids are
    compared against the single ground-truth doc_id.  A hit is counted when
    the ground-truth doc_id appears anywhere in the top-K results.

    Args:
        queries:              List of query strings (len N).
        ground_truth_doc_ids: Parallel list of expected doc_id per query (len N).
        retriever_fn:         Callable(query: str, k: int) -> list[dict]
                              where each dict has at least {"doc_id": str}.
        k:                    Number of results to retrieve per query.

    Returns:
        Recall@K as a float in [0, 1].

    Raises:
        NotImplementedError: until Day 7 implementation.
    """
    raise NotImplementedError(
        "compute_recall_at_k is not yet implemented. "
        "Implement on Day 7 of the sprint (May 9)."
    )


def compute_faithfulness(
    queries: list[str],
    retrieved_chunks: list[list[str]],
    generated_answers: list[str],
) -> float:
    """
    Compute faithfulness score: fraction of answer claims grounded in retrieved chunks.

    Uses an LLM-as-judge approach — for each (answer, chunks) pair, prompt the
    LLM to identify claims in the answer and check each claim against the chunks.
    Returns the macro-average grounding rate across all queries.

    Args:
        queries:           List of query strings (len N).
        retrieved_chunks:  List of chunk-text lists per query (len N, each M chunks).
        generated_answers: List of generated answer strings (len N).

    Returns:
        Faithfulness score as a float in [0, 1].

    Raises:
        NotImplementedError: until Day 7 implementation.
    """
    raise NotImplementedError(
        "compute_faithfulness is not yet implemented. "
        "Implement on Day 7 of the sprint (May 9)."
    )


def measure_latency(
    queries: list[str],
    retriever_fn,
    k: int,
) -> dict[str, float]:
    """
    Measure retrieval latency statistics across a set of queries.

    Calls retriever_fn for each query, records wall-clock time per call, and
    returns a summary dict with mean, p50, p95, and p99 latencies in milliseconds.

    Args:
        queries:      List of query strings to benchmark.
        retriever_fn: Callable(query: str, k: int) -> list[dict].
        k:            Number of results to retrieve per query.

    Returns:
        {
            "mean_latency_ms": float,
            "p50_latency_ms":  float,
            "p95_latency_ms":  float,
            "p99_latency_ms":  float,
        }

    Raises:
        NotImplementedError: until Day 7 implementation.
    """
    raise NotImplementedError(
        "measure_latency is not yet implemented. "
        "Implement on Day 7 of the sprint (May 9)."
    )


# ---------------------------------------------------------------------------
# Retriever stubs (wired up on Day 4 / Day 6)
# ---------------------------------------------------------------------------

def build_retriever(mode: Literal["direct", "hyde"], k: int):
    """
    Return a retriever callable for the given mode.

    direct: embed query → Azure AI Search vector query → top-K chunks
    hyde:   LLM generates hypothetical doc → embed → Azure AI Search → top-K chunks

    Args:
        mode: "direct" or "hyde"
        k:    number of results to return

    Returns:
        Callable(query: str, k: int) -> list[dict]

    Raises:
        NotImplementedError: until Day 4 (direct) / Day 6 (hyde).
    """
    raise NotImplementedError(
        f"build_retriever(mode='{mode}') is not yet implemented. "
        "Wire up the Azure AI Search client on Day 4 (May 6)."
    )


# ---------------------------------------------------------------------------
# Dataset loader stub
# ---------------------------------------------------------------------------

def load_eval_queries(dataset_path: str, n: int = 200) -> tuple[list[str], list[str]]:
    """
    Load evaluation queries and ground-truth doc_ids from the ingest JSONL.

    Uses the held-out eval slice: for each paper, the query is the abstract
    (trimmed to 512 chars) and the ground-truth doc_id is the paper's own id,
    under the assumption that the article body should be the top-retrieved chunk.

    Args:
        dataset_path: Path to arxiv_5k.jsonl produced by ingest/ingest.py.
        n:            Number of eval queries to load (default 200).

    Returns:
        (queries, ground_truth_doc_ids) — parallel lists of length n.

    Raises:
        NotImplementedError: until Day 7 implementation.
    """
    raise NotImplementedError(
        "load_eval_queries is not yet implemented. "
        "Implement on Day 7 of the sprint (May 9)."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mercedes RAG evaluation harness",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="data/arxiv_5k.jsonl",
        help="Path to the ingest JSONL file (produced by ingest/ingest.py).",
    )
    parser.add_argument(
        "--retriever",
        type=str,
        choices=["direct", "hyde"],
        default="direct",
        help="Retrieval mode: 'direct' (embed query) or 'hyde' (hypothetical doc).",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Number of chunks to retrieve per query.",
    )
    parser.add_argument(
        "--n-queries",
        type=int,
        default=200,
        help="Number of eval queries to run.",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Path to write JSON results. Defaults to eval/results/run_<uuid4[:8]>.json.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    run_id = f"run_{uuid.uuid4().hex[:8]}"
    out_path = args.out or os.path.join("eval", "results", f"{run_id}.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    print(f"[eval] run_id      : {run_id}")
    print(f"[eval] dataset     : {args.dataset}")
    print(f"[eval] retriever   : {args.retriever}")
    print(f"[eval] k           : {args.k}")
    print(f"[eval] n_queries   : {args.n_queries}")
    print(f"[eval] output      : {out_path}")
    print()

    # --- Load eval set ---
    queries, ground_truth_ids = load_eval_queries(args.dataset, n=args.n_queries)

    # --- Build retriever ---
    retriever = build_retriever(mode=args.retriever, k=args.k)

    # --- Compute metrics ---
    recall = compute_recall_at_k(
        queries=queries,
        ground_truth_doc_ids=ground_truth_ids,
        retriever_fn=retriever,
        k=args.k,
    )

    latency_stats = measure_latency(
        queries=queries,
        retriever_fn=retriever,
        k=args.k,
    )

    # --- Assemble result ---
    result = {
        "run_id": run_id,
        "date": str(date.today()),
        "retriever": args.retriever,
        "k": args.k,
        "recall_at_k": recall,
        "mean_latency_ms": latency_stats["mean_latency_ms"],
        "p95_latency_ms": latency_stats["p95_latency_ms"],
        "num_queries": args.n_queries,
    }

    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"[eval] recall@{args.k}    : {recall:.4f}")
    print(f"[eval] mean latency : {latency_stats['mean_latency_ms']:.1f} ms")
    print(f"[eval] p95 latency  : {latency_stats['p95_latency_ms']:.1f} ms")
    print(f"[eval] results → {out_path}")


if __name__ == "__main__":
    main()
