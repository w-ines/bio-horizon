"""Test script for relation extraction using wesin/pubmedbert-relation-extraction model."""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from ner.router import extract_from_text


def test_relation_extraction():
    """Test relation extraction with sample biomedical text."""
    
    # Test text with clear biomedical relations
    test_cases = [
        {
            "text": "Aspirin inhibits COX-2 enzyme activity in inflammatory cells.",
            "entity_types": ["CHEMICAL", "GENE"],
            "description": "Chemical-Gene inhibition"
        },
        {
            "text": "Metformin activates AMPK signaling pathway in diabetic patients.",
            "entity_types": ["CHEMICAL", "GENE"],
            "description": "Chemical-Gene activation"
        },
        {
            "text": "Ibuprofen treats inflammation and reduces pain in arthritis.",
            "entity_types": ["CHEMICAL", "DISEASE"],
            "description": "Chemical-Disease treatment"
        },
    ]
    
    print("=" * 80)
    print("Testing Relation Extraction with wesin/pubmedbert-relation-extraction")
    print("=" * 80)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[Test {i}] {test_case['description']}")
        print(f"Text: {test_case['text']}")
        print("-" * 80)
        
        try:
            # Extract entities and relations
            result = extract_from_text(
                test_case["text"],
                entity_types=test_case["entity_types"],
                enable_relations=True,
                provider="openmed"
            )
            
            # Display results
            result_dict = result.to_dict()
            
            print(f"Provider: {result_dict['provider']}")
            
            # Show entities
            print("\nEntities found:")
            for entity_type, entities in result_dict['entities'].items():
                if entities:
                    print(f"  {entity_type}:")
                    for ent in entities:
                        print(f"    - {ent['text']} (confidence: {ent.get('confidence', 'N/A')})")
            
            # Show relations
            if result_dict.get('relations'):
                print("\nRelations found:")
                for subj, rel_type, obj in result_dict['relations']:
                    print(f"  {subj} --[{rel_type}]--> {obj}")
            else:
                print("\nNo relations found.")
                
            if result_dict.get('error'):
                print(f"\nError: {result_dict['error']}")
                
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("Test completed!")
    print("=" * 80)


if __name__ == "__main__":
    test_relation_extraction()
