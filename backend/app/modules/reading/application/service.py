from app.modules.catalog.application.ports import BookCatalogPort
from app.modules.reading.application.ports import ReadingRepository, RecommendationPort


class MockRecommendationPort:
    def __init__(self, catalog: BookCatalogPort):
        self.catalog = catalog

    def recommend(self, intent, limit):
        result = self.catalog.verified_samples(intent["topics"], limit)
        for rank, item in enumerate(result, 1):
            item["rank"] = rank
            angle = {
                "瓦尔登湖": "从独处与生活方式，继续思考自由和自我选择",
                "简·爱": "从成长与爱情故事，继续思考关系中的选择",
                "理想国": "从正义的讨论，继续思考原则与公平",
            }.get(item["title"], "继续探索你选择的主题")
            item["recommendation_reason"] = f"固定样例：{angle}。补充文字尚未进行 AI 语义分析。"
        return result


class ReadingService:
    def __init__(self, repository: ReadingRepository, recommendations: RecommendationPort):
        self.repo, self.recommendations = repository, recommendations

    def create_daily(self, intent):
        return self.repo.create_daily(intent)

    def create_recommendation(self, actor_id, intent_id, key, limit):
        intent = self.repo.intent(actor_id, intent_id)
        job = self.repo.create_job(actor_id, intent_id, key, limit)
        if job["status"] == "pending":
            return self.repo.finish_job(
                job["job_id"], self.recommendations.recommend(intent, limit), limit
            )
        return job

    def job(self, actor_id, job_id):
        return self.repo.job(actor_id, job_id)
