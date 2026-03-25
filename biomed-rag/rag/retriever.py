"""
LangChain retriever with Knowledge Graph enrichment.
Combines vector similarity search with KG entity relationships.
"""

from typing import List, Optional, Dict, Any
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun

from rag.vector_store import get_vector_store


class KGEnhancedRetriever(BaseRetriever):
    """
    Custom retriever that enriches vector search results with Knowledge Graph data.
    
    Workflow:
    1. Vector similarity search in Supabase
    2. Extract entities from retrieved chunks
    3. Query KG for related entities and relationships
    4. Re-rank results based on KG relevance
    5. Add KG context to metadata
    """
    
    vector_store: Any = None
    top_k: int = 5
    table_name: str = "documents"
    query_name: str = "match_documents"
    enable_kg_enrichment: bool = True
    kg_weight: float = 0.3  # Weight for KG score in hybrid ranking
    
    def __init__(
        self,
        *,
        top_k: int = 5,
        table_name: str = "documents",
        query_name: str = "match_documents",
        enable_kg_enrichment: bool = True,
        kg_weight: float = 0.3,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.top_k = top_k
        self.table_name = table_name
        self.query_name = query_name
        self.enable_kg_enrichment = enable_kg_enrichment
        self.kg_weight = kg_weight
        self.vector_store = get_vector_store(
            table_name=table_name,
            query_name=query_name
        )
    
    def _extract_entities_from_text(self, text: str) -> List[str]:
        """Extract medical entities from text using GLiNER."""
        try:
            from ner.backends.gliner_backend import extract as gliner_extract
            
            result = gliner_extract(
                text,
                entity_types=["DRUG", "DISEASE", "GENE", "PROTEIN"],
            )
            
            entities = []
            for entity_type, entity_list in (result.entities or {}).items():
                entities.extend([e.text for e in entity_list if e.text])
            
            return entities
        except Exception as e:
            print(f"[KGEnhancedRetriever] Entity extraction failed: {e}")
            return []
    
    def _get_kg_context(self, entities: List[str]) -> Dict[str, Any]:
        """Get Knowledge Graph context for entities."""
        if not entities:
            return {}
        
        try:
            from kg.store import load_graph
            import networkx as nx
            
            G = load_graph()
            
            if G.number_of_nodes() == 0:
                return {}
            
            # Find matching nodes in KG
            kg_nodes = []
            for entity in entities:
                entity_lower = entity.lower()
                for node_id in G.nodes():
                    node_label = G.nodes[node_id].get("label", "").lower()
                    if entity_lower in node_label or node_label in entity_lower:
                        kg_nodes.append({
                            "id": node_id,
                            "label": G.nodes[node_id].get("label"),
                            "type": G.nodes[node_id].get("entity_type"),
                            "frequency": G.nodes[node_id].get("frequency", 1)
                        })
            
            # Get relationships between found entities
            relationships = []
            for i, node1 in enumerate(kg_nodes):
                for node2 in kg_nodes[i+1:]:
                    if G.has_edge(node1["id"], node2["id"]):
                        edge_data = G.edges[node1["id"], node2["id"]]
                        relationships.append({
                            "source": node1["label"],
                            "target": node2["label"],
                            "weight": edge_data.get("weight", 1),
                            "type": edge_data.get("relation_type", "co_occurrence")
                        })
            
            return {
                "entities": kg_nodes,
                "relationships": relationships,
                "total_nodes": len(kg_nodes),
                "total_edges": len(relationships)
            }
        
        except Exception as e:
            print(f"[KGEnhancedRetriever] KG query failed: {e}")
            return {}
    
    def _compute_kg_relevance_score(
        self,
        doc_entities: List[str],
        kg_context: Dict[str, Any]
    ) -> float:
        """Compute relevance score based on KG overlap."""
        if not kg_context or not doc_entities:
            return 0.0
        
        kg_entity_labels = set(
            e["label"].lower() for e in kg_context.get("entities", [])
        )
        doc_entity_set = set(e.lower() for e in doc_entities)
        
        if not kg_entity_labels or not doc_entity_set:
            return 0.0
        
        # Jaccard similarity
        intersection = len(kg_entity_labels & doc_entity_set)
        union = len(kg_entity_labels | doc_entity_set)
        
        return intersection / union if union > 0 else 0.0
    
    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None
    ) -> List[Document]:
        """Retrieve documents with KG enrichment."""
        
        # Step 1: Vector similarity search
        docs = self.vector_store.similarity_search(query, k=self.top_k * 2)
        
        if not self.enable_kg_enrichment:
            return docs[:self.top_k]
        
        # Step 2: Extract entities from query
        query_entities = self._extract_entities_from_text(query)
        
        if not query_entities:
            return docs[:self.top_k]
        
        # Step 3: Get KG context
        kg_context = self._get_kg_context(query_entities)
        
        if not kg_context:
            return docs[:self.top_k]
        
        # Step 4: Re-rank documents with KG relevance
        enriched_docs = []
        for doc in docs:
            # Extract entities from document
            doc_entities = self._extract_entities_from_text(doc.page_content)
            
            # Compute KG relevance score
            kg_score = self._compute_kg_relevance_score(doc_entities, kg_context)
            
            # Add KG context to metadata
            enriched_metadata = dict(doc.metadata or {})
            enriched_metadata["kg_score"] = kg_score
            enriched_metadata["kg_entities"] = kg_context.get("entities", [])
            enriched_metadata["kg_relationships"] = kg_context.get("relationships", [])
            enriched_metadata["doc_entities"] = doc_entities
            
            # Compute hybrid score (vector + KG)
            # Assume vector score is in metadata if available
            vector_score = enriched_metadata.get("score", 0.5)
            hybrid_score = (vector_score * (1 - self.kg_weight)) + (kg_score * self.kg_weight)
            enriched_metadata["hybrid_score"] = hybrid_score
            
            enriched_docs.append(
                Document(page_content=doc.page_content, metadata=enriched_metadata)
            )
        
        # Sort by hybrid score
        enriched_docs.sort(key=lambda d: d.metadata.get("hybrid_score", 0), reverse=True)
        
        return enriched_docs[:self.top_k]


def get_retriever(
    *,
    top_k: int = 5,
    enable_kg_enrichment: bool = True,
    kg_weight: float = 0.3
) -> KGEnhancedRetriever:
    """
    Get KG-enhanced retriever instance.
    
    Args:
        top_k: Number of documents to retrieve
        enable_kg_enrichment: Enable Knowledge Graph enrichment
        kg_weight: Weight for KG score in hybrid ranking (0-1)
    
    Returns:
        KGEnhancedRetriever instance
    """
    return KGEnhancedRetriever(
        top_k=top_k,
        enable_kg_enrichment=enable_kg_enrichment,
        kg_weight=kg_weight
    )