from elasticsearch import AsyncElasticsearch

import settings
from storage.mysql import QuestionService
from routes.question.models import QuestionOnlineJudge


DEFAULT_ES_CONFIG = settings.ELASTICSEARCH_CONF["default"]


client = AsyncElasticsearch(
    hosts=DEFAULT_ES_CONFIG["URL"],
    basic_auth=(DEFAULT_ES_CONFIG["USER"], DEFAULT_ES_CONFIG["PASSWORD"])
)


async def create_index():
    """
    创建索引

    需要先在 ES 中安装 IK 分词器
    """
    mappings = {
        "properties": {
            "id": {"type": "integer"},
            "title": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart"
            },
            "description": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart"
            },
            "difficulty": {"type": "keyword"},
            "submission_quantity": {"type": "integer"},
            "pass_quantity": {"type": "integer"},
            "tags": {"type": "keyword"}
        }
    }
    if not await client.indices.exists(index="question"):
        await client.indices.create(index="question", mappings=mappings)
        print("创建 question 索引成功！")


async def migrate_data_from_mysql():
    """
    从 MySQL 中将 question、tag、question_tag 表的数据导入到 ElasticSearch 中
    """
    # 创建索引
    await create_index()

    async with QuestionService() as service:
        page, size = 1, 10

        questions, _ = await service.query_by_page(page, size)
        questions = questions.fetchall()

        while questions:
            for question in questions:
                question_id = question.id

                if await client.exists(index="question", id=str(question_id)):
                    continue

                question = QuestionOnlineJudge.model_validate(question)
                
                question_dict = question.model_dump(exclude=("tests", "solving_frameworks"))
                original_tags = question_dict.pop("tags")
                question_dict["tags"] = [tag["tag"]["name"] for tag in original_tags]
                
                response = await client.index(index="question", id=str(question_id), document=question_dict)
                print(response)

            page += 1
            questions, _ = await service.query_by_page(page, size)
            questions = questions.fetchall()  
