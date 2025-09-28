# GraphRAG Agent 🕸️

AI를 활용한 지식그래프 생성 및 질의응답 시스템

애니메이션 줄거리를 AI로 분석하여 주인공 중심의 지식 그래프를 만들고, 자연어로 질문할 수 있는 GraphRAG 에이전트입니다!

## 🎯 프로젝트 소개

이 프로젝트는 자동으로:
1. **수집 및 처리** - 위키피디아에서 에피소드 데이터 수집 (귀멸의 칼날 시즌 1) 후 OpenAI를 사용하여 텍스트에서 개체와 관계 추출
2. **저장** - Neo4j 그래프 데이터베이스에 지식그래프 저장
3. **질의** - 자연어 질문을 Cypher 쿼리로 변환하여 답변 생성

## 📋 사전 요구사항

- Python 3.12+
- OpenAI API 키
- Neo4j desktop

## 🚀 초기 셋팅

### 1. 프로젝트 클론 및 의존성 설치

```bash
# uv를 사용한 의존성 설치 (권장)
uv sync

# 또는 uv add / pip 사용
uv add beautifulsoup4 neo4j-graphrag[openai] openai python-dotenv requests

```

### 2. OpenAI API 키 설정

프로젝트 루트에 `.env` 파일 생성:
```env
OPENAI_API_KEY=여기에_API_키_입력
```

> 💡 [OpenAI API 키 발급 가이드](https://github.com/dabidstudio/dabidstudio_guides/blob/main/get-openai-api-key.md)

### 3. Neo4j 데이터베이스 설정

Neo4j Desktop을 사용하세요.

기본 설정:
- URI: `neo4j://127.0.0.1:7687`
- 사용자명: `neo4j`
- 비밀번호: `12345678` (실제 비밀번호로 변경 필요)

## 📖 사용 방법

### 단계별 실행

스크립트를 순서대로 실행하세요:

```bash
# 1단계: 위키피디아에서 에피소드 데이터 수집 및 처리
uv run 1_prepare_data.py

# 2단계: Neo4j 데이터베이스에 지식그래프 저장
uv run 2_ingest_data.py

# 3단계: GraphRAG 에이전트로 질의응답
uv run 3_graphrag_agent.py
```

### 각 스크립트 설명

#### `1_prepare_data.py`
- 위키피디아에서 귀멸의 칼날 시즌 1 에피소드 데이터 수집
- OpenAI API를 사용하여 텍스트에서 개체(노드)와 관계 추출
- 한국어 이름으로 표준화
- 결과를 `output/` 폴더에 JSON 형태로 저장

#### `2_ingest_data.py`
- 생성된 지식그래프를 Neo4j 데이터베이스에 저장
- 커스텀 KGWriter를 사용하여 관계를 CREATE로 생성
- 기존 데이터베이스 내용을 초기화 후 새 데이터 삽입

#### `3_graphrag_agent.py`
- 자연어 질문을 Cypher 쿼리로 변환
- Neo4j에서 관련 데이터 검색
- OpenAI를 사용하여 자연스러운 한국어 답변 생성

## 🎮 예시 질문

GraphRAG 에이전트에게 다음과 같은 질문을 할 수 있습니다:

```
"카마도 탄지로는 시즌 1에서 에피소드별로 어떤 활약을 했어?"
"토미오카 기유는 시즌 1에서 어떤 역할을 했는지 에피소드별로 알려줘."
"카마도 탄지로와 카마도 네즈코 사이에 어떤 사건들이 있었어? 에피소드별로 정리해줘."
```

## 📊 데이터 구조

### 노드 타입
- **인간**: 귀살대원들과 일반 인간 캐릭터
- **도깨비**: 악역 도깨비 캐릭터들

### 주요 캐릭터
- 카마도 탄지로, 카마도 네즈코
- 토미오카 기유, 우로코다키 사콘지
- 아가츠마 젠이츠, 하시비라 이노스케
- 키부츠지 무잔, 루이, 엔무 등

## 📁 프로젝트 구조

```
graphrag-agent/
├── 1_prepare_data.py      # 데이터 수집 및 처리
├── 2_ingest_data.py       # Neo4j 데이터베이스 저장
├── 3_graphrag_agent.py    # GraphRAG 질의응답 에이전트
├── output/                # 생성된 데이터 파일
│   ├── 1_원본데이터.json
│   └── 지식그래프_최종.json
├── pyproject.toml         # 프로젝트 설정 및 의존성
└── README.md
```

## 🔧 주요 의존성

- `neo4j-graphrag[openai]>=1.10.0` - Neo4j GraphRAG 라이브러리
- `openai>=1.109.1` - OpenAI API 클라이언트
- `beautifulsoup4>=4.13.5` - 웹 스크래핑
- `requests>=2.32.5` - HTTP 요청
- `python-dotenv>=1.1.1` - 환경변수 관리

## 🎨 활용 데이터

[귀멸의 칼날 시즌 1 위키피디아 문서](https://en.wikipedia.org/wiki/Demon_Slayer:_Kimetsu_no_Yaiba_season_1)

## 🤖 Neo4j 프롬프트 템플릿

<details>
<summary>ChatGPT에서 직접 활용할 수 있는 프롬프트</summary>

```text
You are a top-tier algorithm designed for extracting
information in structured formats to build a knowledge graph.

Extract the entities (nodes) and specify their type from the following text.
Also extract the relationships between these nodes.

Return result as JSON using the following format:
{{"nodes": [ {{"id": "0", "label": "Person", "properties": {{"name": "John"}} }}],
"relationships": [{{"type": "KNOWS", "start_node_id": "0", "end_node_id": "1", "properties": {{"since": "2024-08-01"}} }}] }}

Use only the following node and relationship types (if provided):
{schema}

Assign a unique ID (string) to each node, and reuse it to define relationships.
Do respect the source and target node types for relationship and
the relationship direction.

Make sure you adhere to the following rules to produce valid JSON objects:
- Do not return any additional information other than the JSON in it.
- Omit any backticks around the JSON - simply output the JSON on its own.
- The JSON object must not wrapped into a list - it is its own JSON object.
- Property names must be enclosed in double quotes

Examples:
{examples}

Input text:
```
</details>

