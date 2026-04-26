"""
ChromaDB retrieval using the same embedding model as the indexed corpus.

Requires ``chromadb`` and ``sentence-transformers``. Set ``CHROMA_PERSIST_DIR`` and
``CHROMA_COLLECTION_NAME`` to match your persisted vector store.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from housing_policy_advisor import config
from housing_policy_advisor.models.locality_input import FullLocalityInput

logger = logging.getLogger(__name__)

UNIVERSAL_POLICY_QUERIES = [
    "affordable housing policy local government",
    "housing needs assessment recommendations",
    "zoning reform housing supply",
]

PROFILE_POLICY_QUERIES: Dict[str, List[str]] = {
    "RURAL_LOW_INCOME": [
        "manufactured housing mobile home rural affordable",
        "home repair rehabilitation assistance rural low income",
        "USDA rural housing assistance program",
        "down payment assistance low income rural homeownership",
        "accessory dwelling unit rural housing",
        "housing trust fund small locality",
        "eviction prevention rental assistance rural",
    ],
    "RURAL_MODERATE": [
        "accessory dwelling unit rural",
        "homeowner rehabilitation assistance",
        "community land trust rural",
        "housing trust fund small county",
        "employer assisted housing programs",
        "manufactured housing preservation",
    ],
    "URBAN_HIGH_COST": [
        "inclusionary zoning mandatory affordable units",
        "community land trust permanently affordable",
        "tax increment financing affordable housing",
        "density bonus affordable housing development",
        "anti displacement tenant protection",
        "opportunity to purchase policy",
        "housing trust fund dedicated revenue",
    ],
    "URBAN_MODERATE": [
        "mixed income housing development",
        "land bank vacant property redevelopment",
        "missing middle housing zoning reform",
        "housing choice voucher landlord recruitment",
        "workforce housing programs",
        "down payment assistance moderate income",
        "code enforcement rental registry",
    ],
    "COLLEGE_TOWN": [
        "missing middle housing zoning density",
        "rental regulation tenant protection",
        "inclusionary zoning university college town",
        "affordable rental housing young adults",
        "short term rental regulation",
        "density bonus multifamily housing",
        "landlord recruitment retention voucher",
    ],
    "SUBURBAN_GROWING": [
        "mixed income housing development",
        "land bank vacant property redevelopment",
        "missing middle housing zoning reform",
        "housing choice voucher landlord recruitment",
        "workforce housing programs",
        "down payment assistance moderate income",
        "code enforcement rental registry",
    ],
}


def _is_between(value: Optional[float], low: float, high: float) -> bool:
    return value is not None and low <= value <= high


def _assign_locality_profile(locality: FullLocalityInput) -> str:
    pop = locality.population_estimate
    income = locality.median_household_income
    burden = locality.cost_burden_rate
    homeownership = locality.homeownership_rate
    governance_form = (locality.governance_form or "").lower()

    # COLLEGE_TOWN: moderate population, low homeownership
    if pop is not None and pop > 20_000 and homeownership is not None and homeownership < 0.45:
        return "COLLEGE_TOWN"

    # URBAN_HIGH_COST: large population AND high income
    if (
        pop is not None
        and pop > 50_000
        and governance_form == "city"
        and income is not None
        and income > 65_000
        and burden is not None
        and burden > 0.35
    ):
            return "URBAN_HIGH_COST"

    # URBAN_MODERATE: large population, moderate income
    if (
        pop is not None
        and pop > 50_000
        and governance_form == "city"
        and income is not None
        and income >= 45_000
    ):
        return "URBAN_MODERATE"

    # RURAL_LOW_INCOME: small population OR low income
    if (income is not None and income < 45_000) or (pop is not None and pop < 50_000):
        return "RURAL_LOW_INCOME"

    # Default
    return "RURAL_MODERATE"


def _profile_query_suffix(locality: FullLocalityInput) -> str:
    parts: List[str] = []
    if locality.median_household_income is not None:
        rounded_income = int(round(locality.median_household_income / 1000.0) * 1000)
        parts.append(f"median income {rounded_income}")
    if locality.cost_burden_rate is not None:
        burden_pct = int(round(locality.cost_burden_rate * 100))
        parts.append(f"cost burden {burden_pct}")
    if locality.homeownership_rate is not None:
        homeownership_pct = int(round(locality.homeownership_rate * 100))
        parts.append(f"homeownership rate {homeownership_pct}")
    return " ".join(parts)


def _queries_for_profile(profile: str, locality: Optional[FullLocalityInput]) -> List[str]:
    profile_queries = PROFILE_POLICY_QUERIES.get(profile, PROFILE_POLICY_QUERIES["RURAL_MODERATE"])
    suffix = _profile_query_suffix(locality) if locality is not None else ""
    if not suffix:
        return UNIVERSAL_POLICY_QUERIES + profile_queries
    profiled = [f"{query} {suffix}" for query in profile_queries]
    return UNIVERSAL_POLICY_QUERIES + profiled


def _embedding_function():
    try:
        from chromadb.utils import embedding_functions
    except ImportError as e:
        raise RuntimeError(
            "chromadb is required for RAG. Install dependencies: pip install chromadb sentence-transformers"
        ) from e

    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=config.EMBEDDING_MODEL)


def _persistent_client():
    try:
        import chromadb
    except ImportError as e:
        raise RuntimeError(
            "chromadb is required for RAG. Install dependencies: pip install chromadb sentence-transformers"
        ) from e

    path = str(config.chroma_persist_path())
    return chromadb.PersistentClient(path=path)


def _get_collection():
    client = _persistent_client()
    name = config.CHROMA_COLLECTION_NAME
    names = {c.name for c in client.list_collections()}
    if name not in names:
        raise RuntimeError(
            f"Chroma collection {name!r} not found under {config.chroma_persist_path()}. "
            f"Available collections: {sorted(names) or '(none)'}. "
            "Build or copy the vector DB, or set CHROMA_COLLECTION_NAME."
        )
    # Do not pass a new embedding function when opening an existing collection.
    # Newer Chroma versions enforce embedding-function consistency and will raise
    # if the persisted collection already has an embedding function configured.
    return client.get_collection(name=name)


def _format_query_results(
    res: Dict[str, Any],
    *,
    retrieval_pass: str,
    query: str,
    profile: Optional[str] = None,
) -> List[Dict[str, Any]]:
    ids = (res.get("ids") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0] if res.get("distances") is not None else [None] * len(ids)
    out: List[Dict[str, Any]] = []
    for i, cid in enumerate(ids):
        text = docs[i] if i < len(docs) else ""
        meta = metas[i] if i < len(metas) else {}
        dist = dists[i] if i < len(dists) else None
        out.append(
            {
                "id": cid,
                "text": text or "",
                "metadata": meta or {},
                "distance": dist,
                "retrieval_pass": retrieval_pass,
                "retrieval_query": query,
                "retrieval_profile": profile,
            }
        )
    return out


def _dedupe_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    for chunk in chunks:
        cid = str(chunk.get("id", "")).strip()
        if not cid:
            continue
        prev = by_id.get(cid)
        if prev is None:
            by_id[cid] = chunk
            continue

        prev_dist = prev.get("distance")
        cur_dist = chunk.get("distance")
        if prev_dist is None and cur_dist is not None:
            by_id[cid] = chunk
            continue
        if cur_dist is None:
            continue
        if prev_dist is None or float(cur_dist) < float(prev_dist):
            by_id[cid] = chunk
            continue
    return list(by_id.values())


def retrieve_chunks(
    query: str,
    k: int = 8,
    locality: Optional[FullLocalityInput] = None,
) -> List[Dict[str, Any]]:
    """
    Return top-k chunks as dicts: ``id``, ``text``, ``metadata``, ``distance`` (if present).

    ``locality`` is reserved for future query expansion; currently unused.
    """
    _ = locality
    if not query.strip():
        return []
    collection = _get_collection()
    # Two-pass retrieval for locality runs:
    # pass_1: locality/context query (k=10)
    # pass_2: profile-targeted policy queries + universal baseline (k=2 each)
    if locality is not None:
        out: List[Dict[str, Any]] = []
        profile = _assign_locality_profile(locality)
        pass_2_queries = _queries_for_profile(profile, locality)
        pass_2_k = max(2, k // 4)

        pass_1_res = collection.query(
            query_texts=[query],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        out.extend(_format_query_results(pass_1_res, retrieval_pass="locality", query=query, profile=profile))

        for policy_query in pass_2_queries:
            pass_2_res = collection.query(
                query_texts=[policy_query],
                n_results=pass_2_k,
                include=["documents", "metadatas", "distances"],
            )
            out.extend(
                _format_query_results(
                    pass_2_res,
                    retrieval_pass="policy",
                    query=policy_query,
                    profile=profile,
                )
            )

        merged = _dedupe_chunks(out)
        merged.sort(key=lambda c: float("inf") if c.get("distance") is None else float(c["distance"]))
        return merged

    res = collection.query(
        query_texts=[query],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    return _format_query_results(res, retrieval_pass="single", query=query)


def retrieve(query: str, k: int = 8, locality: Optional[FullLocalityInput] = None) -> List[str]:
    """Return top-k chunk texts for the query."""
    return [c["text"] for c in retrieve_chunks(query, k=k, locality=locality) if c.get("text")]


def retrieve_chunks_with_metadata(query: str, k: int = 8) -> List[dict]:
    """Alias for :func:`retrieve_chunks` (includes metadata)."""
    return retrieve_chunks(query, k=k)
