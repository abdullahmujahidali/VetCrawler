import scrapy


class TopicItem(scrapy.Item):
    section = scrapy.Field()
    topic_name = scrapy.Field()
    topic_url = scrapy.Field()
