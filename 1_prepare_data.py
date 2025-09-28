#!/usr/bin/env python3
"""
Standalone Knowledge Graph Generator
====================================

This script combines data collection and processing into a single executable file.
It collects episode data from Wikipedia and processes it into a knowledge graph.

Usage:
    uv run python standalone_knowledge_graph.py
    
    or simply:
    
    uv run standalone_knowledge_graph.py

Requirements:
    - OpenAI API key in .env file or OPENAI_API_KEY environment variable
    - Internet connection for Wikipedia scraping and OpenAI API calls
"""

import json
import re
import os
from typing import List, Dict, Any, Optional, Union
import requests
from bs4 import BeautifulSoup
import openai
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Type definitions
PropertyValue = Union[str, int, float, bool, None]

class Node(BaseModel):
    id: str
    label: str
    properties: Optional[Dict[str, PropertyValue]] = None

class Relationship(BaseModel):
    type: str
    start_node_id: str
    end_node_id: str
    properties: Optional[Dict[str, PropertyValue]] = None

class GraphResponse(BaseModel):
    nodes: List[Node]
    relationships: List[Relationship]

# Templates for LLM processing
UPDATED_TEMPLATE = """
You are a top-tier algorithm designed for extracting information in structured formats to build a knowledge graph. Extract the entities (nodes) and specify their type from the following text, but **you MUST select nodes ONLY from the following predefined set** (see the provided NODES list below). Do not create any new nodes or use names that do not exactly match one in the NODES list.

Also extract the relationships between these nodes. Return the result as JSON using the following format:

{
  "nodes": [
    {"id": "N0", "label": "인간", "properties": {"name": "Tanjiro Kamado"}}
  ],
  "relationships": [
    {"type": "FIGHTS", "start_node_id": "N0", "end_node_id": "N13", "properties": {"outcome": "victory"}}
  ]
}

Additional rules:
- Use only nodes from the NODES list. Do not invent or substitute nodes.
- Skip any relationship if one of its entities is not in NODES.
- Only output valid relationships where both endpoints exist in NODES and the direction matches their types.

NODES =
[
  {"id":"N0",  "label":"인간", "properties":{"name":"Tanjiro Kamado"}},
  {"id":"N1",  "label":"인간", "properties":{"name":"Nezuko Kamado"}},
  {"id":"N2",  "label":"인간", "properties":{"name":"Giyu Tomioka"}},
  {"id":"N3",  "label":"인간", "properties":{"name":"Sakonji Urokodaki"}},
  {"id":"N4",  "label":"인간", "properties":{"name":"Sabito"}},
  {"id":"N5",  "label":"인간", "properties":{"name":"Makomo"}},
  {"id":"N6",  "label":"인간", "properties":{"name":"Zenitsu Agatsuma"}},
  {"id":"N7",  "label":"인간", "properties":{"name":"Inosuke Hashibira"}},
  {"id":"N8",  "label":"인간", "properties":{"name":"Kanao Tsuyuri"}},
  {"id":"N9",  "label":"인간", "properties":{"name":"Kyojuro Rengoku"}},
  {"id":"N10", "label":"인간", "properties":{"name":"Kagaya Ubuyashiki"}},
  {"id":"N11", "label":"인간", "properties":{"name":"Shinobu Kocho"}},
  {"id":"N12", "label":"인간", "properties":{"name":"Sanemi Shinazugawa"}},
  {"id":"N13", "label":"도깨비", "properties":{"name":"Muzan Kibutsuji"}},
  {"id":"N14", "label":"도깨비", "properties":{"name":"Susamaru"}},
  {"id":"N15", "label":"도깨비", "properties":{"name":"Yahaba"}},
  {"id":"N16", "label":"도깨비", "properties":{"name":"Kyogai"}},
  {"id":"N17", "label":"도깨비", "properties":{"name":"Rui"}},
  {"id":"N18", "label":"도깨비", "properties":{"name":"Enmu"}}
]
"""

# Korean node name mapping
KOREAN_NODE_MAP = {
    # 귀살대 (Demon Slayer Corps)
    "Tanjiro Kamado": "카마도 탄지로",
    "Nezuko Kamado": "카마도 네즈코",
    "Giyu Tomioka": "토미오카 기유",
    "Sakonji Urokodaki": "우로코다키 사콘지",
    "Sabito": "사비토",
    "Makomo": "마코모",
    "Zenitsu Agatsuma": "아가츠마 젠이츠",
    "Inosuke Hashibira": "하시비라 이노스케",
    "Kanao Tsuyuri": "츠유리 카나오",
    "Kyojuro Rengoku": "렌고쿠 쿄쥬로",
    "Kagaya Ubuyashiki": "우부야시키 카가야",
    "Shinobu Kocho": "코쵸우 시노부",
    "Sanemi Shinazugawa": "시나즈가와 사네미",

    # 도깨비 (Demons)
    "Muzan Kibutsuji": "키부츠지 무잔",
    "Susamaru": "스사마루",
    "Yahaba": "야하바",
    "Kyogai": "쿄우가이",
    "Rui": "루이",
    "Enmu": "엔무",
}

def llm_call_structured(prompt: str, model: str = "gpt-4o-mini") -> GraphResponse:
    """Call OpenAI API with structured output"""
    resp = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "user", "content": prompt},
        ],
        response_format=GraphResponse,
    )
    return resp.choices[0].message.parsed

def combine_chunk_graphs(chunk_graphs: List[GraphResponse]) -> GraphResponse:
    """
    Combine multiple GraphResponse objects into one.
    - Collects all nodes and relationships
    - Removes duplicate nodes, keeping the first occurrence
    """
    # 1. Collect all nodes from all chunk graphs
    all_nodes = []
    for chunk_graph in chunk_graphs:
        for node in chunk_graph.nodes:
            all_nodes.append(node)
    
    # 2. Collect all relationships from all chunk graphs
    all_relationships = []
    for chunk_graph in chunk_graphs:
        for relationship in chunk_graph.relationships:
            all_relationships.append(relationship)
    
    # 3. Remove duplicate nodes
    unique_nodes = []
    seen = set()  # Set to remember already added nodes

    for node in all_nodes:
        # Create a key from node's id, label, and properties
        node_key = (node.id, node.label, str(node.properties))
        # Add to unique_nodes if not already seen
        if node_key not in seen:
            unique_nodes.append(node)
            seen.add(node_key)

    # 4. Return combined GraphResponse
    return GraphResponse(nodes=unique_nodes, relationships=all_relationships)

def fetch_episode(link: str) -> List[dict]:
    """Fetch episode data from Wikipedia"""
    season = int(re.search(r"season_(\d+)", link).group(1))
    print(f"Fetching Season {season} from: {link}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(link, headers=headers)
    
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.select_one("table.wikitable.plainrowheaders.wikiepisodetable")

    episodes = []
    rows = table.select("tr.vevent.module-episode-list-row")

    for i, row in enumerate(rows, start=1):
        synopsis = None
        synopsis_row = row.find_next_sibling("tr", class_="expand-child")
        if synopsis_row:
            synopsis_cell = synopsis_row.select_one("td.description div.shortSummaryText")
            synopsis = synopsis_cell.get_text(strip=True) if synopsis_cell else None

        episodes.append({
            "season": season,
            "episode_in_season": i,
            "synopsis": synopsis,
        })
    
    return episodes

def collect_data() -> List[dict]:
    """Collect episode data from multiple seasons"""
    print("=== 데이터 수집 시작 ===")
    
    episode_links = [
        "https://en.wikipedia.org/wiki/Demon_Slayer:_Kimetsu_no_Yaiba_season_1",  # 귀멸의 칼날 시즌 1
        # Add more seasons as needed:
        # "https://en.wikipedia.org/wiki/Demon_Slayer:_Kimetsu_no_Yaiba_season_2",  # 귀멸의 칼날 시즌 2
    ]
    
    all_episodes = []
    for link in episode_links:
        try:
            episodes = fetch_episode(link)
            all_episodes.extend(episodes)
        except Exception as e:
            print(f"Error fetching data from {link}: {e}")
            continue
    
    print(f"총 {len(all_episodes)}개 에피소드 수집 완료")
    return all_episodes

def process_data(episodes: List[dict]) -> GraphResponse:
    """Process episode data into knowledge graph"""
    print("=== 데이터 처리 시작 ===")
    
    chunk_graphs: List[GraphResponse] = []
    
    for episode in episodes:
        if not episode.get("synopsis"):
            print(f"에피소드 S{episode['season']}E{episode['episode_in_season']:02d}: 시놉시스가 없어 건너뜀")
            continue
            
        print(f"에피소드 처리 중: 시즌 {episode['season']}, 에피소드 {episode['episode_in_season']}")
        
        try:
            # (1) Generate prompt with updated template for node standardization
            prompt = UPDATED_TEMPLATE + f"\n 입력값\n {episode['synopsis']}"
            graph_response = llm_call_structured(prompt)

            # (2) Add episode number to relationships (e.g., S1E01)
            episode_number = f"S{episode['season']}E{episode['episode_in_season']:02d}"

            for relationship in graph_response.relationships:
                if relationship.properties is None:
                    relationship.properties = {}
                relationship.properties["episode_number"] = episode_number
                
            # (3) Convert node names to Korean
            for node in graph_response.nodes:
                english_name = node.properties.get("name", "")
                if english_name in KOREAN_NODE_MAP:
                    node.properties["name"] = KOREAN_NODE_MAP[english_name]
            
            chunk_graphs.append(graph_response)
            
        except Exception as e:
            print(f"  - 에피소드 처리 중 오류 발생: {e}")
            continue
    
    if not chunk_graphs:
        raise Exception("그래프를 성공적으로 추출하지 못했습니다.")
    
    print(f"총 {len(chunk_graphs)}개 에피소드 처리 완료")
    return combine_chunk_graphs(chunk_graphs)

def save_output(episodes: List[dict], final_graph: GraphResponse):
    """Save outputs to JSON files"""
    print("=== 결과 저장 ===")
    
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)
    
    # Save original data
    with open("output/1_원본데이터.json", "w", encoding="utf-8") as f:
        json.dump(episodes, f, indent=2, ensure_ascii=False)
    print("원본 데이터 저장: output/1_원본데이터.json")
    
    # Save final knowledge graph
    with open("output/지식그래프_최종.json", "w", encoding="utf-8") as f:
        json.dump(final_graph.model_dump(), f, ensure_ascii=False, indent=2)
    print("최종 지식그래프 저장: output/지식그래프_최종.json")

def main():
    """Main function that orchestrates the entire process"""
    try:
        # Check for OpenAI API key
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ OPENAI_API_KEY가 설정되지 않았습니다.")
            print("\n설정 방법:")
            print("1. .env 파일에 OPENAI_API_KEY=your_api_key_here 추가")
            print("2. 또는 환경변수로 설정: export OPENAI_API_KEY=your_api_key_here")
            return 1
        
        print("🚀 지식그래프 생성기 시작")
        print("=" * 50)
        
        # Step 1: Collect data
        episodes = collect_data()
        
        if not episodes:
            raise Exception("수집된 에피소드 데이터가 없습니다.")
        
        # Step 2: Process data
        final_graph = process_data(episodes)
        
        # Step 3: Save outputs
        save_output(episodes, final_graph)
        
        print("=" * 50)
        print("✅ 지식그래프 생성 완료!")
        print(f"📊 총 노드 수: {len(final_graph.nodes)}")
        print(f"🔗 총 관계 수: {len(final_graph.relationships)}")
        print("\n생성된 파일:")
        print("- output/1_원본데이터.json")
        print("- output/지식그래프_최종.json")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
