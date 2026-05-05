"""
ChromaDB retrieval using the same embedding model as the indexed corpus.

Requires ``chromadb`` and ``sentence-transformers``. Set ``CHROMA_PERSIST_DIR`` and
``CHROMA_COLLECTION_NAME`` to match your persisted vector store.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

from housing_policy_advisor import config
from housing_policy_advisor.models.locality_input import FullLocalityInput
from housing_policy_advisor.models.policy_class import SUPPORTED_POLICY_CLASSES, validate_policy_class

logger = logging.getLogger(__name__)

UNIVERSAL_POLICY_QUERIES = [
    "affordable housing policy local government",
    "housing needs assessment recommendations",
    "zoning reform housing supply",
]

TaggedQuery = Tuple[str, FrozenSet[str]]

CLASS_QUERY_EXPANSIONS: Dict[str, str] = {
    "adu": (
        "accessory dwelling unit secondary unit garage conversion "
        "backyard cottage detached accessory apartment by-right "
        "owner occupancy"
    ),
    "affordable_dwelling_unit": (
        "affordable dwelling unit ordinance inclusionary mandate "
        "AMI set-aside percentage developer requirement Fairfax "
        "below market affordable units income restricted"
    ),
    "density_bonus": (
        "density bonus additional floor area height bonus zoning bonus "
        "affordable housing set aside increased density incentive"
    ),
}


PROFILE_POLICY_QUERIES: Dict[str, List[TaggedQuery]] = {
    "RURAL_LOW_INCOME": [
        ("eviction prevention rental assistance rural low income", frozenset({"high_burden", "low_income"})),
        ("home repair rehabilitation assistance aging rural low income", frozenset({"aging_housing", "low_income"})),
        ("manufactured housing preservation rural low income", frozenset({"low_supply", "low_income"})),
        ("rural housing trust fund low income small locality", frozenset({"high_burden", "low_supply"})),
        ("USDA rural housing assistance program low income", frozenset({"low_income"})),
        ("down payment assistance low income rural homeownership", frozenset({"low_income"})),
        ("rural rental assistance housing vouchers landlord recruitment", frozenset({"high_burden"})),
        ("homeowner rehabilitation assistance rural", frozenset({"aging_housing"})),
        ("accessory dwelling unit rural housing", frozenset({"low_supply"})),
        ("vacant property rehabilitation rural housing", frozenset({"high_vacancy"})),
        ("small locality affordable housing development subsidy", frozenset({"low_supply"})),
        ("manufactured home community infrastructure preservation", frozenset()),
        ("housing counseling rural homeownership", frozenset()),
    ],
    "RURAL_MODERATE": [
        ("homeowner rehabilitation assistance aging housing rural", frozenset({"aging_housing", "high_income"})),
        ("accessory dwelling unit rural low supply housing", frozenset({"low_supply", "high_income"})),
        ("community land trust rural affordability high burden", frozenset({"high_burden"})),
        ("housing trust fund small county", frozenset({"high_burden"})),
        ("employer assisted housing programs rural workforce", frozenset({"high_income"})),
        ("manufactured housing preservation rural", frozenset({"low_supply"})),
        ("rural infill housing vacant property reuse", frozenset({"high_vacancy"})),
        ("down payment assistance moderate income rural", frozenset({"low_homeownership"})),
        ("small county zoning reform accessory dwelling units", frozenset({"low_supply"})),
        ("home repair tax abatement aging housing stock", frozenset({"aging_housing"})),
        ("regional housing trust fund rural county", frozenset()),
        ("housing counseling rural moderate income", frozenset()),
        ("land bank rural vacant property redevelopment", frozenset()),
    ],
    "URBAN_HIGH_COST": [
        ("inclusionary zoning mandatory affordable units high cost", frozenset({"high_burden", "high_income"})),
        ("community land trust permanently affordable high cost city", frozenset({"high_burden", "high_income"})),
        ("tenant protection anti displacement high burden city", frozenset({"high_burden", "low_homeownership"})),
        ("opportunity to purchase policy tenant displacement", frozenset({"high_burden", "low_homeownership"})),
        ("tax increment financing affordable housing high income city", frozenset({"high_income"})),
        ("housing trust fund dedicated revenue high cost", frozenset({"high_burden"})),
        ("density bonus affordable housing development", frozenset({"low_supply"})),
        ("transit oriented affordable housing zoning reform", frozenset({"rapid_growth"})),
        ("single room occupancy preservation rental affordability", frozenset({"low_homeownership"})),
        ("vacant property acquisition affordable housing city", frozenset({"high_vacancy"})),
        ("adaptive reuse aging housing commercial conversion", frozenset({"aging_housing"})),
        ("fee waiver affordable housing development high cost", frozenset()),
        ("public land disposition affordable housing city", frozenset()),
    ],
    "URBAN_MODERATE": [
        ("land bank vacant property redevelopment moderate income city", frozenset({"high_vacancy", "low_income"})),
        ("housing choice voucher landlord recruitment high burden city", frozenset({"high_burden", "low_homeownership"})),
        ("code enforcement rental registry aging housing city", frozenset({"aging_housing", "low_homeownership"})),
        ("mixed income housing development moderate income city", frozenset({"high_burden"})),
        ("missing middle housing zoning reform urban moderate", frozenset({"low_supply"})),
        ("workforce housing programs moderate income", frozenset({"rapid_growth"})),
        ("down payment assistance moderate income urban", frozenset({"low_homeownership"})),
        ("rental assistance eviction prevention city", frozenset({"high_burden"})),
        ("infill redevelopment affordable housing urban", frozenset({"high_vacancy"})),
        ("housing rehabilitation tax abatement older neighborhoods", frozenset({"aging_housing"})),
        ("accessory dwelling units urban zoning reform", frozenset({"low_supply"})),
        ("community land trust urban moderate income", frozenset()),
        ("public land affordable housing urban", frozenset()),
    ],
    "COLLEGE_TOWN": [
        ("student housing partnership affordable rental rapid growth", frozenset({"rapid_growth", "high_income"})),
        ("vacant property reuse near campus housing aging neighborhoods", frozenset({"high_vacancy", "aging_housing"})),
        ("rental assistance tenant protection college town high burden", frozenset({"high_burden", "low_homeownership"})),
        ("missing middle housing zoning density college town low supply", frozenset({"low_supply", "low_homeownership"})),
        ("affordable rental housing young adults university high burden", frozenset({"high_burden", "low_homeownership"})),
        ("inclusionary zoning university college town", frozenset({"high_income", "high_burden"})),
        ("short term rental regulation college town rental market", frozenset({"low_homeownership"})),
        ("density bonus multifamily housing college town", frozenset({"low_supply"})),
        ("landlord recruitment retention voucher college town", frozenset({"high_burden"})),
        ("accessory dwelling units college town neighborhoods", frozenset({"low_supply"})),
        ("rental registry code enforcement college town", frozenset({"aging_housing"})),
        ("community land trust college town affordability", frozenset()),
        ("housing trust fund college town", frozenset()),
    ],
    "SUBURBAN_GROWING": [
        ("workforce housing fast growing county suburb high income", frozenset({"rapid_growth", "high_income"})),
        ("infrastructure capacity housing development impact fees suburban growth", frozenset({"rapid_growth", "high_income"})),
        ("accessory dwelling unit single family suburban zone low supply", frozenset({"low_supply", "high_income"})),
        ("large lot zoning reform missing middle suburban low supply", frozenset({"low_supply", "high_income"})),
        ("transit oriented development housing suburb", frozenset({"rapid_growth"})),
        ("adequate public facilities ordinance growth management", frozenset({"rapid_growth"})),
        ("suburban infill redevelopment affordable housing", frozenset({"high_income"})),
        ("housing trust fund dedicated revenue suburban county", frozenset({"high_burden"})),
        ("down payment assistance suburban workforce", frozenset({"low_homeownership"})),
        ("commercial corridor adaptive reuse suburban housing", frozenset({"high_vacancy"})),
        ("home repair preservation aging suburban housing", frozenset({"aging_housing"})),
        ("inclusionary zoning suburban mixed income", frozenset()),
        ("public land affordable housing suburban county", frozenset()),
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

    # URBAN_HIGH_COST: large city, high income, high burden
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

    # URBAN_MODERATE: large city, moderate income
    if (
        pop is not None
        and pop > 50_000
        and governance_form == "city"
        and income is not None
        and income >= 45_000
    ):
        return "URBAN_MODERATE"

    # COLLEGE_TOWN: moderate population (bounded), below-average homeownership.
    # Checked after urban city profiles — county-level ACS threshold raised to 0.58
    # because surrounding rural areas dilute the university homeownership signal.
    if (
        pop is not None
        and 15_000 < pop < 120_000
        and homeownership is not None
        and homeownership < 0.58
    ):
        return "COLLEGE_TOWN"

    # SUBURBAN_GROWING: large non-city jurisdiction, moderate+ income
    if (
        pop is not None
        and pop > 50_000
        and governance_form != "city"
        and income is not None
        and income >= 55_000
    ):
        return "SUBURBAN_GROWING"

    # RURAL_LOW_INCOME: small population OR low income
    if (income is not None and income < 45_000) or (pop is not None and pop < 50_000):
        return "RURAL_LOW_INCOME"

    # Default
    return "RURAL_MODERATE"


def _compute_locality_tags(locality: FullLocalityInput, profile: str) -> FrozenSet[str]:
    _ = profile
    tags: set[str] = set()

    if locality.cost_burden_rate is not None and locality.cost_burden_rate > 0.42:
        tags.add("high_burden")

    permits = locality.building_permits_annual
    if permits is None or permits < 100:
        tags.add("low_supply")
    elif permits > 500:
        tags.add("rapid_growth")

    if locality.vacancy_rate is not None and locality.vacancy_rate > 0.08:
        tags.add("high_vacancy")
    if locality.homeownership_rate is not None and locality.homeownership_rate < 0.45:
        tags.add("low_homeownership")
    if locality.median_household_income is not None and locality.median_household_income < 45_000:
        tags.add("low_income")
    if locality.median_household_income is not None and locality.median_household_income > 80_000:
        tags.add("high_income")
    if locality.pct_built_pre_1980 is not None and locality.pct_built_pre_1980 > 0.55:
        tags.add("aging_housing")

    return frozenset(tags)


def _select_queries(profile: str, locality: Optional[FullLocalityInput], n: int = 7) -> List[str]:
    profile_queries = PROFILE_POLICY_QUERIES.get(profile, PROFILE_POLICY_QUERIES["RURAL_MODERATE"])
    tags = _compute_locality_tags(locality, profile) if locality is not None else frozenset()
    ranked = sorted(
        enumerate(profile_queries),
        key=lambda item: (-sum(1 for tag in item[1][1] if tag in tags), item[0]),
    )
    return [query for _, (query, _) in ranked[:n]]


def _queries_for_profile(profile: str, locality: Optional[FullLocalityInput]) -> List[str]:
    return UNIVERSAL_POLICY_QUERIES + _select_queries(profile, locality)


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

    ``locality`` enables profile-specific query selection when provided.
    """
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


def retrieve_classifier_chunks(
    query: str,
    policy_class: Optional[str] = None,
    k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Retrieve evidence chunks for policy classification.

    Metadata filtering is primary when ``policy_class`` is provided. When no
    class is provided, retrieval runs once per supported class and returns
    de-duplicated evidence grouped by each chunk's metadata.
    """
    if not query.strip():
        return []
    if k <= 0:
        raise ValueError("k must be positive")

    collection = _get_collection()
    classes = [validate_policy_class(policy_class)] if policy_class else list(SUPPORTED_POLICY_CLASSES)

    out: List[Dict[str, Any]] = []
    for klass in classes:
        expanded_query = f"{query.strip()} {CLASS_QUERY_EXPANSIONS[klass]}"
        res = collection.query(
            query_texts=[expanded_query],
            n_results=k,
            where={"policy_class": klass},
            include=["documents", "metadatas", "distances"],
        )
        out.extend(
            _format_query_results(
                res,
                retrieval_pass="classifier",
                query=expanded_query,
                profile=klass,
            )
        )

    merged = _dedupe_chunks(out)
    merged.sort(key=lambda c: float("inf") if c.get("distance") is None else float(c["distance"]))
    return merged


def retrieve(query: str, k: int = 8, locality: Optional[FullLocalityInput] = None) -> List[str]:
    """Return top-k chunk texts for the query."""
    return [c["text"] for c in retrieve_chunks(query, k=k, locality=locality) if c.get("text")]


def retrieve_chunks_with_metadata(query: str, k: int = 8) -> List[dict]:
    """Alias for :func:`retrieve_chunks` (includes metadata)."""
    return retrieve_chunks(query, k=k)
