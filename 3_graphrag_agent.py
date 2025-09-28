from neo4j import GraphDatabase
from neo4j_graphrag.retrievers import Text2CypherRetriever
from neo4j_graphrag.llm import OpenAILLM
from dotenv import load_dotenv
import openai
import os
import re
load_dotenv()

## OpenAI 클라이언트 선언
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

## Neo4j 드라이버와 리트리버 선언
URI = "neo4j://127.0.0.1:7687"
AUTH = ("neo4j", "12345678")
driver = GraphDatabase.driver(URI, auth=AUTH)
llm = OpenAILLM(model_name="gpt-4.1")

examples = [
    "USER INPUT: '토미오카 기유는 시즌 1에서 어떤 역할을 했는지 에피소드별로 알려줘.' QUERY: MATCH (n {name: '토미오카 기유'})-[r]-(m) RETURN n, r, m, properties(r) AS rel_props ORDER BY r.episode_number"
]


retriever = Text2CypherRetriever(
    driver=driver,
    llm=llm,  
    examples=examples,
)

def llm_cal(prompt: str, model: str = "gpt-4.1") -> str:
    response = client.responses.create(
        model=model,
        input=[
            {"role": "user", "content": prompt},
        ],
    )
    return response.output_text

def graphrag_pipeline(user_question):

    # 1 질문 -> cypher query -> 결과 리스트 반환
    result =retriever.search(query_text=user_question)

    # 2 Cypher Query 확인
    cypher_used = result.metadata.get("cypher")
    print("생성된 Cypher Query:")
    print(cypher_used)


    # 3 결과 확인
    result_items = result.items
    print("지식그래프에 찾은 결과")
    print(result_items)

    # 4 결과 기반으로 프롬프트 완성
    context_list = []
    for item in result_items:
        raw = str(item.content)
        # element_id=... 부분만 제거
        cleaned = re.sub(r"element_id='[^']*'\s*", "", raw)
        context_list.append(cleaned)

    full_context = "\n".join(context_list)

    full_prompt = f"""
    아래의 데이터베이스 결과만을 참고하여 사용자의 질문에 답변해주세요.  
    데이터베이스 결과를 그대로 노출하지 말고, 자연스러운 서술로 정리해 주세요.  
    사용자의 질문: {user_question}  
    데이터베이스 결과: {full_context}  

    ### 조건
    - 그래프DB의 관계명(예: DEFENDS, SIBLING_OF, REUNITES_WITH 등)은 그대로 쓰지 말고,
    맥락에 맞는 자연스러운 한국어 문장으로 풀어 설명하세요.
    - 에피소드별로 일어난 사건은 간결하고 이해하기 쉽게 정리하세요.
    - 응답은 마치 스토리를 설명하듯 자연스럽게 작성하세요.
    """
    print("완성 프롬프트")
    print(full_prompt)
    # 3 완성된 프롬프트로 최종 답변 생성
    final_result = llm_cal(full_prompt)
    return final_result

if __name__=="__main__":
    queries = [

    "카마도 탄지로는 시즌 1에서 에피소드별로 어떤 활약을 했어?",
    # "토미오카 기유는 시즌 1에서 어떤 역할을 했는지 에피소드별로 알려줘.",
    # "카마도 탄지로와 카마도 네즈코 사이에 어떤 사건들이 있었어? 에피소드별로 정리해줘.",
        ]
    
    for query in queries:
        print(query)
        print("-"*100)
        print(graphrag_pipeline(query))
        print("-"*100)


